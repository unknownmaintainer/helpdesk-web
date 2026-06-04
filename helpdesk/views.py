import logging
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied
import threading
from django.core.mail import send_mail

def send_mail_async(subject, message, recipient_list, from_email=None, html_message=None, fail_silently=True):
    def _send():
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=fail_silently,
            )
        except Exception as e:
            logger.error(f"Async email sending failed: {str(e)}")

    threading.Thread(target=_send).start()

from django.db.models import Q
from django_ratelimit.decorators import ratelimit

from .models import CustomUser, Ticket, TicketUpdate, LoginAttempt, TicketLog, IncidentAuditLog
from .forms import TicketSubmissionForm
from .validators import validate_file_size, validate_file_type
from .utils import get_client_ip

audit_logger = logging.getLogger('ticket_audit')

# Setup standard python logging
logger = logging.getLogger('helpdesk')
logger.setLevel(logging.INFO)
if not logger.handlers:
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
    
    # File handler inside logs/ directory
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    fh = logging.FileHandler(os.path.join(log_dir, 'helpdesk.log'))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        department = request.POST.get('department', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        profile_picture = request.FILES.get('profile_picture')
        
        if not full_name or not email or not password or not confirm_password:
            messages.error(request, "Please enter all required fields.")
            return render(request, 'helpdesk/register.html')
            
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'helpdesk/register.html')
            
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return render(request, 'helpdesk/register.html')
            
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
            
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='employee',
            full_name=full_name,
            department=department,
            profile_picture=profile_picture
        )
        logger.info(f"User registered: {user.email}")
        messages.success(request, "Account created successfully! Please sign in.")
        return redirect('login')
        
    return render(request, 'helpdesk/register.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        # Get client IP address
        ip_address = get_client_ip(request)
            
        try:
            user_obj = CustomUser.objects.get(email=email)
            username = user_obj.username
        except CustomUser.DoesNotExist:
            username = None
            
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                LoginAttempt.objects.create(email_attempted=email, success=False, ip_address=ip_address)
                messages.error(request, "Your account has been deactivated.")
                return render(request, 'helpdesk/login.html')
                
            LoginAttempt.objects.create(email_attempted=email, success=True, ip_address=ip_address)
            login(request, user)
            logger.info(f"User login: {user.email}")
            
            # Check user security notification preferences
            if user.notify_security:
                logger.info(f"Security Alert: Secure login detected for account {user.email}")
                send_mail_async(
                    subject="Security Alert: New Login Detected",
                    message=f"Hi {user.full_name or user.username},\n\nA login was detected for your account at {user.email}.\n\nIf this wasn't you, please change your password immediately in Settings.",
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
                
            return redirect('dashboard')
        else:
            LoginAttempt.objects.create(email_attempted=email, success=False, ip_address=ip_address)
            messages.error(request, "Invalid email or password.")
            
    return render(request, 'helpdesk/login.html')

def logout_view(request):
    if request.user.is_authenticated:
        logger.info(f"User logout: {request.user.email}")
    logout(request)
    return redirect('login')

@login_required
def dashboard_view(request):
    user = request.user
    role = 'manager' if user.is_superuser else user.role
    if role == 'manager':
        # Manager metrics
        tickets = Ticket.objects.all()
        total_tickets = tickets.count()
        open_tickets = tickets.filter(status='Open').count()
        investigating_tickets = tickets.filter(status='Investigating').count()
        resolved_tickets = tickets.filter(status='Resolved').count()
        closed_tickets = tickets.filter(status='Closed').count()
        
        recent_tickets = tickets.order_by('-created_at')[:5]
        
        context = {
            'role': user.role,
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'investigating_tickets': investigating_tickets,
            'resolved_tickets': resolved_tickets,
            'closed_tickets': closed_tickets,
            'recent_tickets': recent_tickets,
            'active_tab': 'dashboard',
        }
    else:
        # Employee metrics: Remove statistics cards, only show recent tickets and options
        my_tickets = Ticket.objects.filter(created_by=user)
        recent_tickets = my_tickets.order_by('-created_at')[:3] # last 3 tickets only
        
        context = {
            'role': user.role,
            'recent_tickets': recent_tickets,
            'active_tab': 'dashboard',
        }
        
    return render(request, 'helpdesk/dashboard.html', context)

@login_required
def ticket_list_view(request):
    role = 'manager' if request.user.is_superuser else request.user.role
    
    if request.method == 'POST' and role == 'manager':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_tickets')
        
        if action == 'close' and selected_ids:
            tickets_to_close = Ticket.objects.filter(id__in=selected_ids, status='Resolved')
            count = tickets_to_close.count()
            if count:
                for t in tickets_to_close:
                    t.status = 'Closed'
                    t.save()
                    TicketLog.objects.create(
                        ticket=t,
                        changed_by=request.user,
                        change_description=f"Ticket closed via bulk close."
                    )
                    logger.info(f"Ticket closed: Ticket #{t.id} closed by {request.user.email} (Bulk Close)")
                messages.success(request, f"Successfully closed {count} resolved tickets.")
            else:
                messages.warning(request, "Only tickets with status 'Resolved' can be bulk closed.")
            return redirect('tickets')

    # Get base tickets based on role
    if role == 'employee':
        tickets = Ticket.objects.filter(created_by=request.user)
    else:
        tickets = Ticket.objects.all()

    # Search & status filters only
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    if status_filter:
        tickets = tickets.filter(status=status_filter)

    from django.core.paginator import Paginator
    page = request.GET.get('page', 1)
    paginator = Paginator(tickets.order_by('-created_at'), 6)
    tickets_page = paginator.get_page(page)

    context = {
        'role': role,
        'tickets': tickets_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'active_tab': 'tickets',
    }
    return render(request, 'helpdesk/tickets.html', context)

@login_required
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def ticket_create_view(request):
    if getattr(request, 'limited', False):
        return HttpResponse("Rate Limit Exceeded. Maximum 5 ticket submissions per minute.", status=429)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', '').strip()
        priority = request.POST.get('priority', '').strip()
        description = request.POST.get('description', '').strip()
        attachment = request.FILES.get('attachment')

        if not title or not category or not priority or not description:
            messages.error(request, "Please enter all required fields.")
            return render(request, 'helpdesk/create_ticket.html', {
                'active_tab': 'create_ticket',
                'title': title,
                'category': category,
                'priority': priority,
                'description': description,
            })

        if attachment:
            try:
                validate_file_type(attachment)
                validate_file_size(attachment)
            except Exception as exc:
                messages.error(request, str(exc))
                return render(request, 'helpdesk/create_ticket.html', {
                    'active_tab': 'create_ticket',
                    'title': title,
                    'category': category,
                    'priority': priority,
                    'description': description,
                })

        # Check for unique title per user constraint
        if Ticket.objects.filter(created_by=request.user, title=title).exists():
            messages.error(request, "You have already created a ticket with this title.")
            return render(request, 'helpdesk/create_ticket.html', {
                'active_tab': 'create_ticket',
                'title': title,
                'category': category,
                'priority': priority,
                'description': description,
            })

        ticket = Ticket.objects.create(
            created_by=request.user,
            title=title,
            category=category,
            priority=priority,
            description=description,
            attachment=attachment
        )
        TicketLog.objects.create(
            ticket=ticket,
            changed_by=request.user,
            change_description=f"Ticket created: {title}"
        )
        logger.info(f"Ticket created: Ticket #{ticket.id} by {request.user.email}")
        messages.success(request, f"Ticket #{ticket.id} submitted successfully!")
        return redirect('tickets')

    return render(request, 'helpdesk/create_ticket.html', {'active_tab': 'create_ticket'})

@login_required
def ticket_detail_view(request, ticket_id):
    role = 'manager' if request.user.is_superuser else request.user.role
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # SR-02 Anti-IDOR: Employees attempting to access tickets they don't own get 403 Forbidden
    if role == 'employee' and ticket.created_by != request.user:
        raise PermissionDenied("403 Forbidden")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_note':
            # Manager only notes
            if role != 'manager':
                raise PermissionDenied("Only IT Managers can add updates/notes.")
            comment = request.POST.get('comment', '').strip()
            if comment:
                TicketUpdate.objects.create(
                    ticket=ticket,
                    comment=comment,
                    updated_by=request.user
                )
                messages.success(request, "Ticket update note added.")
                
                # Check user notification preferences
                ticket_owner = ticket.created_by
                if ticket_owner.notify_tickets:
                    logger.info(f"Notification sent: Notify {ticket_owner.email} of note added to Ticket #{ticket.id}")
                    send_mail_async(
                        subject=f"New Note Added to Ticket #{ticket.id}",
                        message=f"Hi {ticket_owner.full_name or ticket_owner.username},\n\nIT Manager {request.user.full_name or request.user.username} added a note to your ticket:\n\n\"{comment}\"\n\nView details: http://127.0.0.1:8000/tickets/{ticket.id}/",
                        from_email=None,
                        recipient_list=[ticket_owner.email],
                        fail_silently=True,
                    )
            return redirect('ticket_detail', ticket_id=ticket.id)

        elif action == 'update_status':
            if role != 'manager':
                raise PermissionDenied("Only IT Managers can modify status.")
            status = request.POST.get('status')
            if status in dict(Ticket.STATUS_CHOICES):
                old_status = ticket.status
                ticket.status = status
                ticket.save()
                TicketLog.objects.create(
                    ticket=ticket,
                    changed_by=request.user,
                    change_description=f"Ticket status updated from '{old_status}' to '{status}'"
                )
                logger.info(f"Status changed: Ticket #{ticket.id} status changed from {old_status} to {status} by {request.user.email}")
                if status == 'Closed':
                    logger.info(f"Ticket closed: Ticket #{ticket.id} closed by {request.user.email}")
                messages.success(request, f"Status updated to {status}.")
                
                # Check user notification preferences
                ticket_owner = ticket.created_by
                if ticket_owner.notify_tickets:
                    logger.info(f"Notification sent: Notify {ticket_owner.email} of status update ({status}) on Ticket #{ticket.id}")
                    send_mail_async(
                        subject=f"Status Updated: Ticket #{ticket.id}",
                        message=f"Hi {ticket_owner.full_name or ticket_owner.username},\n\nIT Manager {request.user.full_name or request.user.username} updated the status of your ticket \"{ticket.title}\" from {old_status} to {status}.\n\nView details: http://127.0.0.1:8000/tickets/{ticket.id}/",
                        from_email=None,
                        recipient_list=[ticket_owner.email],
                        fail_silently=True,
                    )
            return redirect('ticket_detail', ticket_id=ticket.id)

        elif action == 'edit_ticket':
            # Employee can only edit their own Open tickets
            if role == 'employee' and ticket.created_by == request.user and ticket.status == 'Open':
                title = request.POST.get('title', '').strip()
                category = request.POST.get('category', '').strip()
                priority = request.POST.get('priority', '').strip()
                description = request.POST.get('description', '').strip()
                attachment = request.FILES.get('attachment')

                if title and category and priority and description:
                    if attachment:
                        try:
                            validate_file_type(attachment)
                            validate_file_size(attachment)
                        except Exception as exc:
                            messages.error(request, str(exc))
                            return redirect('ticket_detail', ticket_id=ticket.id)

                    ticket.title = title
                    ticket.category = category
                    ticket.priority = priority
                    ticket.description = description
                    if attachment:
                        ticket.attachment = attachment
                    ticket.save()
                    TicketLog.objects.create(
                        ticket=ticket,
                        changed_by=request.user,
                        change_description=f"Ticket details edited by user."
                    )
                    logger.info(f"Ticket edited: Ticket #{ticket.id} edited by {request.user.email}")
                    messages.success(request, f"Ticket #{ticket.id} updated successfully.")
                else:
                    messages.error(request, "All fields are required.")
            else:
                messages.error(request, "You can only edit your own tickets while they are still Open.")
            return redirect('ticket_detail', ticket_id=ticket.id)

        elif action == 'delete_ticket':
            # Employee can delete own Open tickets; Manager can delete any ticket
            if (role == 'employee' and ticket.created_by == request.user and ticket.status == 'Open') or role == 'manager':
                ticket_num = ticket.id
                ticket_title = ticket.title
                ticket.delete()
                TicketLog.objects.create(
                    ticket_id=None,
                    changed_by=request.user,
                    change_description=f"Ticket deleted: #{ticket_num} - {ticket_title}"
                )
                logger.info(f"Ticket deleted: Ticket #{ticket_num} deleted by {request.user.email}")
                messages.success(request, f"Ticket #{ticket_num} has been deleted.")
                return redirect('tickets')
            else:
                messages.error(request, "You can only delete your own tickets while they are still Open.")
                return redirect('ticket_detail', ticket_id=ticket.id)

    updates = ticket.updates.order_by('created_at')

    # NIST Equivalent Timeline Steps
    timeline_steps = [
        {'label': 'Open', 'nist': 'Detection', 'status': 'done' if ticket.status != 'Open' else 'active'},
        {'label': 'Investigating', 'nist': 'Analysis / Containment', 'status': 'done' if ticket.status in ['Resolved', 'Closed'] else ('active' if ticket.status == 'Investigating' else 'pending')},
        {'label': 'Resolved', 'nist': 'Recovery', 'status': 'done' if ticket.status == 'Closed' else ('active' if ticket.status == 'Resolved' else 'pending')},
        {'label': 'Closed', 'nist': 'Post-Incident Review', 'status': 'done' if ticket.status == 'Closed' else 'pending'}
    ]

    # Determine if employee can edit/delete (only own Open tickets)
    can_edit = (role == 'employee' and ticket.created_by == request.user and ticket.status == 'Open')
    can_delete = can_edit or role == 'manager'

    context = {
        'role': role,
        'ticket': ticket,
        'updates': updates,
        'timeline_steps': timeline_steps,
        'can_edit': can_edit,
        'can_delete': can_delete,
        'active_tab': 'tickets',
    }
    return render(request, 'helpdesk/ticket_details.html', context)

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            department = request.POST.get('department', '').strip()

            if not full_name or not email:
                messages.error(request, "Name and Email are required.")
                return redirect('profile')

            # Verify email uniqueness
            if CustomUser.objects.exclude(id=user.id).filter(email=email).exists():
                messages.error(request, "Email already in use.")
                return redirect('profile')

            # Track changes for audit log
            changes = []
            if user.full_name != full_name:
                changes.append(f"Full name changed from '{user.full_name}' to '{full_name}'")
            if user.email != email:
                changes.append(f"Email changed from '{user.email}' to '{email}'")
            if user.department != department:
                changes.append(f"Department changed from '{user.department}' to '{department}'")

            user.full_name = full_name
            user.email = email
            user.department = department
            
            new_username = email.split('@')[0]
            if user.username != new_username:
                base_username = new_username
                username = new_username
                counter = 1
                while CustomUser.objects.exclude(id=user.id).filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                user.username = username
                changes.append(f"Username updated to '{username}'")
            
            user.save()
            
            # Log the audit entry
            if changes:
                audit_desc = "Profile updated: " + " | ".join(changes)
                TicketLog.objects.create(
                    ticket_id=None,
                    changed_by=user,
                    change_description=audit_desc
                )
                logger.info(f"Profile updated for {user.email}: {audit_desc}")
            
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')

        elif action == 'update_avatar':
            profile_picture = request.FILES.get('profile_picture')
            if profile_picture:
                ext = os.path.splitext(profile_picture.name)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    try:
                        validate_file_size(profile_picture)
                    except Exception as exc:
                        messages.error(request, str(exc))
                        return redirect('profile')

                    old_picture_name = user.profile_picture.name if user.profile_picture else "None"
                    user.profile_picture = profile_picture
                    user.save()
                    
                    # Log the audit entry
                    audit_desc = f"Profile picture updated (from: {old_picture_name[:50]} to: {profile_picture.name[:50]})"
                    TicketLog.objects.create(
                        ticket_id=None,
                        changed_by=user,
                        change_description=audit_desc
                    )
                    logger.info(f"Avatar updated for {user.email}")
                    
                    messages.success(request, "Profile picture updated successfully.")
                else:
                    messages.error(request, "Invalid file type. Please upload an image.")
            return redirect('profile')

        elif action == 'remove_avatar':
            if user.profile_picture:
                old_picture_name = user.profile_picture.name
                user.profile_picture.delete()
                user.profile_picture = None
                user.save()
                
                # Log the audit entry
                audit_desc = f"Profile picture removed (was: {old_picture_name[:50]})"
                TicketLog.objects.create(
                    ticket_id=None,
                    changed_by=user,
                    change_description=audit_desc
                )
                logger.info(f"Avatar removed for {user.email}")
                
                messages.success(request, "Profile picture removed successfully.")
            return redirect('profile')

    # Fetch and paginate user activities
    all_tickets = Ticket.objects.filter(created_by=user).order_by('-created_at')
    all_updates = TicketUpdate.objects.filter(updated_by=user).order_by('-created_at')
    all_ticket_logs = TicketLog.objects.filter(changed_by=user).order_by('-timestamp')
    all_login_attempts = LoginAttempt.objects.filter(email_attempted=user.email).order_by('-timestamp')
    
    activity_list = []
    for t in all_tickets:
        activity_list.append({
            'icon': 'fa-ticket text-primary',
            'desc': f"Submitted support ticket: \"{t.title}\"",
            'date': t.created_at
        })
    for u in all_updates:
        activity_list.append({
            'icon': 'fa-comment-dots text-success',
            'desc': f"Added note/update to Ticket #{u.ticket.id} - \"{u.ticket.title}\"",
            'date': u.created_at
        })
    for log in all_ticket_logs:
        desc = log.change_description or ""
        # Clean up raw admin log details to present formal descriptions in profile activity feed
        icon_class = 'fa-clipboard-list text-warning'
        
        if desc.startswith("Profile picture updated"):
            desc = "Updated profile picture"
            icon_class = 'fa-image text-info'
        elif desc.startswith("Profile picture removed"):
            desc = "Removed profile picture"
            icon_class = 'fa-trash-can text-danger'
        elif desc.startswith("Profile updated:"):
            desc = "Updated profile details"
            icon_class = 'fa-user-pen text-primary'
        elif desc.startswith("Security settings updated:"):
            desc = desc.replace("Security settings updated: ", "")
            icon_class = 'fa-shield-halved text-success'
        elif desc.startswith("Ticket submitted") or desc.startswith("Ticket created:"):
            # Already handled by all_tickets loop above, skip to avoid duplicates
            continue
        elif desc.startswith("Created new user"):
            icon_class = 'fa-user-plus text-primary'
        elif desc.startswith("Permanently deleted"):
            icon_class = 'fa-user-minus text-danger'
        elif desc.startswith("User ") and ("activated" in desc or "deactivated" in desc):
            icon_class = 'fa-user-gear text-secondary'
        elif desc.startswith("Ticket status updated"):
            icon_class = 'fa-circle-check text-success'
        elif desc.startswith("Ticket closed"):
            icon_class = 'fa-folder-closed text-secondary'
        
        if desc:
            activity_list.append({
                'icon': icon_class,
                'desc': desc,
                'date': log.timestamp
            })
    for login in all_login_attempts:
        activity_list.append({
            'icon': 'fa-right-to-bracket text-info' if login.success else 'fa-exclamation-triangle text-danger',
            'desc': 'Successfully logged into the system' if login.success else 'Unsuccessful login attempt detected',
            'date': login.timestamp
        })

    # Sort activity by date descending
    activity_list = sorted(activity_list, key=lambda x: x['date'], reverse=True)

    from django.core.paginator import Paginator
    paginator = Paginator(activity_list, 5)  # 5 activities per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'role': user.role,
        'page_obj': page_obj,
        'active_tab': 'profile'
    }
    return render(request, 'helpdesk/profile.html', context)

@login_required
def settings_view(request):
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_password':
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                
                TicketLog.objects.create(
                    ticket_id=None,
                    changed_by=user,
                    change_description="Security settings updated: Password changed."
                )

                # Check user security notification preferences
                if user.notify_security:
                    logger.info(f"Security Alert: Password changed successfully for user {user.email}")
                    send_mail_async(
                        subject="Security Alert: Password Changed Successfully",
                        message=f"Hi {user.full_name or user.username},\n\nYour account password has been successfully updated.\n\nIf you did not perform this change, please contact IT immediately.",
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
            else:
                messages.error(request, "Password change failed. Please review guidelines.")
            return redirect('settings')
        elif action == 'update_notifications':
            notify_tickets = request.POST.get('notify_tickets') == 'true'
            notify_security = request.POST.get('notify_security') == 'true'
            
            changes = []
            if user.notify_tickets != notify_tickets:
                changes.append(f"Ticket notifications {'enabled' if notify_tickets else 'disabled'}")
            if user.notify_security != notify_security:
                changes.append(f"Security notifications {'enabled' if notify_security else 'disabled'}")
                
            user.notify_tickets = notify_tickets
            user.notify_security = notify_security
            user.save()
            
            if changes:
                TicketLog.objects.create(
                    ticket_id=None,
                    changed_by=user,
                    change_description="Notification preferences updated: " + " | ".join(changes)
                )
            return JsonResponse({'status': 'success'})

    form = PasswordChangeForm(user)
    context = {
        'role': user.role,
        'form': form,
        'active_tab': 'settings'
    }
    return render(request, 'helpdesk/settings.html', context)

@login_required
def integrations_view(request):
    """Manager-only page: integration status, connected services, and demo simulator."""
    if request.user.role != 'manager' and not request.user.is_superuser:
        raise PermissionDenied("Access Denied")

    # Last ticket submitted via API (source != employee)
    last_api_ticket = Ticket.objects.exclude(source='employee').order_by('-created_at').first()
    api_ticket_count = Ticket.objects.exclude(source='employee').count()

    context = {
        'role': request.user.role,
        'active_tab': 'integrations',
        'last_api_ticket': last_api_ticket,
        'api_ticket_count': api_ticket_count,
        'services': [
            {'name': 'Firewall Service',          'description': 'Monitors inbound/outbound traffic for anomalies', 'icon': 'fa-solid fa-fire-flame-curved', 'color': '#dc2626', 'color_bg': '#fee2e2'},
            {'name': 'Antivirus Service',          'description': 'Scans endpoints for malware signatures',          'icon': 'fa-solid fa-shield-virus',       'color': '#16a34a', 'color_bg': '#dcfce7'},
            {'name': 'Network Monitoring Service', 'description': 'Tracks bandwidth, latency and connection events',  'icon': 'fa-solid fa-network-wired',      'color': '#2563eb', 'color_bg': '#dbeafe'},
            {'name': 'External Monitoring API',    'description': 'Third-party SIEM integration endpoint',            'icon': 'fa-solid fa-satellite-dish',     'color': '#7c3aed', 'color_bg': '#ede9fe'},
        ],
    }
    return render(request, 'helpdesk/integrations.html', context)


@login_required
def simulate_alert_view(request):
    """AJAX POST endpoint: creates a simulated security incident for demo purposes."""
    if request.user.role != 'manager' and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required.'}, status=405)

    import json
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST

    alert_type = data.get('alert_type', 'firewall')

    ALERT_CONFIG = {
        'firewall': {
            'title':       'Suspicious Inbound Traffic Detected',
            'description': 'The Firewall Service detected an unusual spike in inbound TCP connections from an unrecognised external IP range. Potential port scanning or reconnaissance activity identified.',
            'source':      'firewall',
            'priority':    'High',
            'actor_label': 'Firewall Service',
        },
        'malware': {
            'title':       'Malware Signature Detected on Endpoint',
            'description': 'The Antivirus Service identified a known malware signature (Trojan.GenericKD) in a file downloaded on a corporate endpoint. Quarantine action has been triggered automatically.',
            'source':      'antivirus',
            'priority':    'Critical',
            'actor_label': 'Antivirus Service',
        },
        'brute_force': {
            'title':       'Brute Force Attack Detected',
            'description': 'The Network Monitoring Service detected over 500 failed SSH login attempts from a single external IP within a 2-minute window. This matches a known brute-force attack pattern.',
            'source':      'network',
            'priority':    'Critical',
            'actor_label': 'Network Monitoring Service',
        },
    }

    if alert_type not in ALERT_CONFIG:
        return JsonResponse({'error': 'Invalid alert_type.'}, status=400)

    cfg = ALERT_CONFIG[alert_type]

    ticket = Ticket.objects.create(
        title=cfg['title'],
        description=cfg['description'],
        ticket_type='Security Incident',
        category='Security',
        priority=cfg['priority'],
        source=cfg['source'],
        nist_stage='detection',
        created_by=request.user,
    )

    IncidentAuditLog.objects.create(
        ticket=ticket,
        actor=None,
        actor_label=cfg['actor_label'],
        action=f"Incident automatically generated by {cfg['actor_label']}.",
    )

    TicketLog.objects.create(
        ticket=ticket,
        changed_by=request.user,
        change_description=f"Security incident automatically generated by {cfg['actor_label']}.",
    )

    audit_logger.info("", extra={
        'user': request.user.email,
        'action': 'SIMULATE_ALERT',
        'id': ticket.id,
        'detail': f"Simulated {alert_type} alert. Ticket #{ticket.id} created.",
    })

    return JsonResponse({
        'status': 'success',
        'ticket_id': ticket.id,
        'title': ticket.title,
        'source': ticket.get_source_display(),
        'priority': ticket.priority,
    })


@login_required
def users_view(request):
    if request.user.role != 'manager' and not request.user.is_superuser:
        raise PermissionDenied("Access Denied")

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_user':
            full_name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            role = request.POST.get('role', 'employee')
            department = request.POST.get('department', 'IT & Systems').strip()
            password = request.POST.get('password', '')

            if not full_name or not email or not password:
                messages.error(request, "Name, email, and password are required.")
                return redirect('users')

            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, "A user with this email already exists.")
                return redirect('users')

            username = email.split('@')[0]
            base_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            new_user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                full_name=full_name,
                department=department
            )
            TicketLog.objects.create(
                ticket=None,
                changed_by=request.user,
                change_description=f"Created new user account: {new_user.email} (Role: {role.capitalize()})"
            )
            messages.success(request, f"User {new_user.full_name} created.")

        elif action == 'toggle_status':
            target_id = request.POST.get('user_id')
            target_user = get_object_or_404(CustomUser, id=target_id)
            if target_user == request.user:
                messages.error(request, "You cannot modify your own status.")
            else:
                target_user.is_active = not target_user.is_active
                target_user.save()
                state = "activated" if target_user.is_active else "deactivated"
                TicketLog.objects.create(
                    ticket=None,
                    changed_by=request.user,
                    change_description=f"User {target_user.email} has been {state}."
                )
                messages.success(request, f"User {target_user.full_name} has been {state}.")

        return redirect('users')

    managers = CustomUser.objects.filter(role='manager')
    employees = CustomUser.objects.filter(role='employee')
    context = {
        'role': request.user.role,
        'managers': managers,
        'employees': employees,
        'active_tab': 'users',
    }
    return render(request, 'helpdesk/users.html', context)


@login_required
def security_logs_view(request):
    if request.user.role != 'manager' and not request.user.is_superuser:
        raise PermissionDenied("Access Denied")

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')

    # Query 1: Security events (like Password resets/changes, profile updates)
    security_events = TicketLog.objects.filter(ticket=None).order_by('-timestamp')
    if query:
        security_events = security_events.filter(
            Q(changed_by__email__icontains=query) | 
            Q(changed_by__full_name__icontains=query) | 
            Q(change_description__icontains=query)
        )

    # Query 2: Login attempts
    login_attempts = LoginAttempt.objects.all()
    if query:
        login_attempts = login_attempts.filter(Q(email_attempted__icontains=query) | Q(ip_address__icontains=query))

    if status_filter == 'success':
        login_attempts = login_attempts.filter(success=True)
    elif status_filter == 'failed':
        login_attempts = login_attempts.filter(success=False)

    from django.core.paginator import Paginator
    
    # Paginate Login History
    login_paginator = Paginator(login_attempts, 10)
    login_page = request.GET.get('login_page', 1)
    login_page_obj = login_paginator.get_page(login_page)

    # Paginate Security Events
    event_paginator = Paginator(security_events, 10)
    event_page = request.GET.get('event_page', 1)
    event_page_obj = event_paginator.get_page(event_page)

    context = {
        'role': request.user.role,
        'login_page_obj': login_page_obj,
        'event_page_obj': event_page_obj,
        'query': query,
        'status_filter': status_filter,
        'active_tab': 'security_logs',
    }
    return render(request, 'helpdesk/security_logs.html', context)

@login_required
def solutions_detail_view(request, slug):
    guides = {
        'forgot-password': {
            'title': 'Forgot Password',
            'icon': 'fa-key text-warning',
            'desc': 'Follow these steps to recover or reset your account password.',
            'steps': [
                'Ensure Caps Lock is turned off on your keyboard.',
                'If you are still logged out, navigate to your Profile page and enter a new password in the password change form.',
                'If you cannot log in at all, contact an IT Support Analyst at extension 4500 to request an AD credentials reset.',
                'A temporary password will be sent to your verified mobile number or manager.'
            ]
        },
        'internet-not-working': {
            'title': 'Internet Not Working',
            'icon': 'fa-wifi text-info',
            'desc': 'Troubleshoot your local network or corporate VPN client.',
            'steps': [
                'Check if your device Wi-Fi card is enabled and connected to the corporate network.',
                'Unplug and replug your ethernet LAN cable if connected via cable.',
                'Disconnect and reconnect your Cisco AnyConnect VPN client if working remotely.',
                'Try restarting your router or network adaptor to clear local caching issues.'
            ]
        },
        'printer-not-working': {
            'title': 'Printer Not Working',
            'icon': 'fa-print text-primary',
            'desc': 'Check printer status and clear print queues.',
            'steps': [
                'Verify the printer power indicator is green and the screen displays no error codes.',
                'Open paper trays to inspect for physical paper jams or out-of-paper conditions.',
                'Open Windows Settings -> Devices -> Printers & Scanners, and verify the correct corporate network printer is selected.',
                'Restart the Windows Print Spooler service to clear stuck print queues.'
            ]
        },
        'email-access-issue': {
            'title': 'Email Access Issue',
            'icon': 'fa-envelope-open-text text-success',
            'desc': 'Resolve mail delivery delay or sync disconnects.',
            'steps': [
                'Check your junk email folder to verify if messages were misclassified by spam filters.',
                'In Outlook, verify that the bottom-right status bar displays "Connected" and not "Working Offline".',
                'Verify that your corporate mailbox quota limit has not been exceeded.',
                'Run a manual Send/Receive action using the Outlook ribbon button.'
            ]
        }
    }
    
    guide = guides.get(slug)
    if not guide:
        return redirect('dashboard')
        
    return render(request, 'helpdesk/solutions_detail.html', {'guide': guide, 'active_tab': 'dashboard'})


@login_required
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def submit_ticket(request):
    try:
        if getattr(request, 'limited', False):
            return HttpResponse("Too many requests. Please wait before submitting again.", status=429)

        if request.method == 'POST':
            form = TicketSubmissionForm(request.POST, request.FILES)
            if form.is_valid():
                title = form.cleaned_data.get('title')
                if Ticket.objects.filter(created_by=request.user, title=title).exists():
                    form.add_error('title', "You have already created a ticket with this title.")
                else:
                    ticket = form.save(commit=False)
                    ticket.created_by = request.user
                    ticket.nist_stage = 'detection'
                    ticket.save()

                    # Create TicketLog entry
                    TicketLog.objects.create(
                        ticket=ticket,
                        changed_by=request.user,
                        change_description="Ticket submitted and initial NIST stage set to detection."
                    )

                    # Log using Python logging module (ticket_audit)
                    audit_logger.info("", extra={
                        'user': request.user.email,
                        'action': 'CREATE',
                        'id': ticket.id,
                        'detail': ticket.title
                    })

                    messages.success(request, "Ticket submitted successfully!")
                    return redirect('ticket_list')
        else:
            form = TicketSubmissionForm()

        return render(request, 'helpdesk/ticket_form.html', {'form': form})
    except Exception as e:
        audit_logger.error(f"Error in submit_ticket: {str(e)}")
        raise e


@login_required
def update_ticket_stage(request, ticket_id):
    try:
        if request.method == 'POST':
            ticket = get_object_or_404(Ticket, id=ticket_id)
            role = 'manager' if request.user.is_superuser else request.user.role
            if role != 'manager' and ticket.assigned_to_id != request.user.id:
                raise PermissionDenied("Only managers or assigned users can update this ticket.")

            new_stage = request.POST.get('nist_stage')
            if new_stage in ['preparation', 'detection', 'containment', 'recovery', 'closed']:
                old_stage = ticket.nist_stage
                ticket.nist_stage = new_stage
                ticket.save()

                # Create TicketLog entry
                TicketLog.objects.create(
                    ticket=ticket,
                    changed_by=request.user,
                    change_description=f"NIST stage updated from {old_stage} to {new_stage}."
                )

                # Log every update using Python logging
                audit_logger.info("", extra={
                    'user': request.user.email,
                    'action': 'UPDATE',
                    'id': ticket.id,
                    'detail': f"{old_stage} | {new_stage}"
                })

                messages.success(request, f"Ticket stage updated to {new_stage.capitalize()}.")
            else:
                messages.error(request, "Invalid NIST stage.")

        return redirect('ticket_list')
    except Exception as e:
        audit_logger.error(f"Error in update_ticket_stage: {str(e)}")
        raise e


@login_required
def ticket_list(request):
    try:
        tickets = Ticket.objects.select_related('created_by', 'assigned_to').filter(assigned_to=request.user)

        stage = request.GET.get('stage')
        resolved = request.GET.get('resolved')

        if stage:
            tickets = tickets.filter(nist_stage=stage)

        if resolved is not None and resolved != '':
            if resolved.lower() in ['true', '1', 'yes']:
                tickets = tickets.filter(is_resolved=True)
            elif resolved.lower() in ['false', '0', 'no']:
                tickets = tickets.filter(is_resolved=False)

        context = {
            'tickets': tickets,
            'nist_stage_filter': stage,
            'is_resolved_filter': resolved,
        }
        return render(request, 'helpdesk/ticket_list.html', context)
    except Exception as e:
        audit_logger.error(f"Error in ticket_list: {str(e)}")
        raise e

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email address is required.'}, status=400)
        
        # Check if user exists
        user_exists = CustomUser.objects.filter(email=email).exists()
        
        if user_exists:
            user = CustomUser.objects.get(email=email)
            # Build the login portal URL dynamically based on the request host
            login_url = request.build_absolute_uri(reverse('login'))
            
            # Log the password reset request to database for admin visibility
            TicketLog.objects.create(
                ticket=None,
                changed_by=user,
                change_description=f"Security alert: Password reset link requested. Sent to: {email} | Demo reset link: {login_url}"
            )
            
            # Send real email using SMTP
            subject = 'Password Reset Request - IT Helpdesk Pro'
            message = f"""
Hello,

We received a request to reset your password for your IT Helpdesk & Incident Tracker account.

If you made this request, you can reset your password by contacting your IT System Administrator or using this demo portal link:
{login_url}

If you did not request this, please ignore this email or contact security-incident@gmail.com.

Best regards,
IT Helpdesk Security Team
"""
            html_message = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
    <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #0A3D91; margin-bottom: 5px;">IT Helpdesk & Incident Tracker</h2>
        <span style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Security Notification</span>
    </div>
    <div style="background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <p style="font-size: 16px; color: #1e293b; line-height: 1.6;">Hello,</p>
        <p style="font-size: 15px; color: #334155; line-height: 1.6;">We received a password reset request for your IT Helpdesk account (<strong>{email}</strong>).</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{login_url}" style="background: linear-gradient(135deg, #0A3D91, #1e5bb8); color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Go to Login Portal</a>
        </div>
        <p style="font-size: 13px; color: #64748b; line-height: 1.5; margin-top: 25px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
            If you did not request this reset, you can safely ignore this email. Your password will remain secure.
        </p>
    </div>
    <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #94a3b8;">
        &copy; 2026 IT Helpdesk Incident Tracker &bull; Enterprise Operations Center
    </div>
</div>
"""
            try:
                send_mail_async(
                    subject=subject,
                    message=message,
                    from_email=None, # will use DEFAULT_FROM_EMAIL
                    recipient_list=[email],
                    html_message=html_message,
                    fail_silently=False,
                )
                logger.info(f"Password reset email sent to: {email}")
            except Exception as e:
                logger.error(f"Failed to send email to {email}: {str(e)}")
                # We still return success to the front-end to avoid leaking user list or error details
                
        # Return success regardless of user existence to prevent user enumeration
        return JsonResponse({
            'status': 'success', 
            'message': 'Reset link sent! If that account exists, check your inbox.'
        })
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

def bad_request(request, exception):
    return render(request, 'errors/400.html', status=400)

def forbidden(request, exception):
    return render(request, 'errors/403.html', status=403)

def page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)

def server_error(request):
    return render(request, 'errors/500.html', status=500)
