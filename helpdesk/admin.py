from django.contrib import admin
from .models import CustomUser, Ticket, TicketUpdate, LoginAttempt, TicketLog

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name', 'role', 'department', 'created_at')
    search_fields = ('username', 'email', 'full_name', 'department')
    list_filter = ('role', 'department')

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'ticket_type', 'nist_stage', 'priority', 'is_resolved', 'created_at')
    list_filter = ('nist_stage', 'priority', 'ticket_type')
    search_fields = ('title', 'description')
    actions = ['mark_as_resolved']

    @admin.action(description="Mark selected tickets as resolved")
    def mark_as_resolved(self, request, queryset):
        if request.user.role != 'manager' and not request.user.is_superuser:
            self.message_user(request, "Permission Denied: Only IT Managers can perform this action.", level='error')
            return
        
        updated_count = 0
        tickets_to_update = []
        logs_to_create = []
        for ticket in queryset:
            if not ticket.is_resolved:
                ticket.is_resolved = True
                tickets_to_update.append(ticket)
                
                # Write to database audit trail
                logs_to_create.append(
                    TicketLog(
                        ticket=ticket,
                        changed_by=request.user,
                        change_description="Ticket marked as resolved via admin bulk action."
                    )
                )
                
                # Log using python logging module
                import logging
                audit_logger = logging.getLogger('ticket_audit')
                audit_logger.info("", extra={
                    'user': request.user.email,
                    'action': 'ADMIN_BULK_RESOLVE',
                    'id': ticket.id,
                    'detail': "Ticket marked as resolved via admin bulk action."
                })
                updated_count += 1
                
        if tickets_to_update:
            Ticket.objects.bulk_update(tickets_to_update, ['is_resolved'])
            TicketLog.objects.bulk_create(logs_to_create)
                
        self.message_user(request, f"Successfully marked {updated_count} tickets as resolved.")

@admin.register(TicketUpdate)
class TicketUpdateAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'updated_by', 'created_at')
    search_fields = ('ticket__title', 'comment', 'updated_by__username')

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('email_attempted', 'success', 'ip_address', 'timestamp')
    search_fields = ('email_attempted', 'ip_address')
    list_filter = ('success',)

@admin.register(TicketLog)
class TicketLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'changed_by', 'change_description', 'timestamp')
    search_fields = ('ticket__title', 'changed_by__username', 'change_description')
    list_filter = ('timestamp',)
    readonly_fields = ('ticket', 'changed_by', 'change_description', 'timestamp')
