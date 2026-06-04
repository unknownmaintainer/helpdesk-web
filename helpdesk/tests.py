from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from helpdesk.models import CustomUser, Ticket, TicketUpdate, MileageReport
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient
import logging

# Disable logging printouts during tests to keep output clean
logging.disable(logging.CRITICAL)

@override_settings(AXES_ENABLED=False)
class ModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='test_user',
            email='test@gmail.com',
            password='password123',
            role='employee',
            full_name='Test Employee'
        )

    def test_ticket_creation(self):
        ticket = Ticket.objects.create(
            title="Slow PC",
            description="Testing PC speed",
            category="Hardware",
            priority="Low",
            created_by=self.user
        )
        self.assertEqual(ticket.status, "Open")
        self.assertEqual(ticket.nist_equivalent, "Detection")
        
        # Test update creation
        update = TicketUpdate.objects.create(
            ticket=ticket,
            comment="Doing diagnostics scan.",
            updated_by=self.user
        )
        self.assertEqual(ticket.updates.count(), 1)
        self.assertEqual(ticket.updates.first().comment, "Doing diagnostics scan.")

@override_settings(AXES_ENABLED=False)
class AccessControlTests(TestCase):
    def setUp(self):
        self.employee = CustomUser.objects.create_user(
            username='employee_user',
            email='emp@gmail.com',
            password='password123',
            role='employee',
            full_name='Bob Employee'
        )
        self.other_employee = CustomUser.objects.create_user(
            username='other_user',
            email='other@gmail.com',
            password='password123',
            role='employee',
            full_name='Charlie Employee'
        )
        self.manager = CustomUser.objects.create_user(
            username='manager_user',
            email='mgr@gmail.com',
            password='password123',
            role='manager',
            full_name='Alice Manager'
        )
        self.ticket = Ticket.objects.create(
            title="Employee ticket",
            description="Secret stuff",
            category="Hardware",
            priority="Medium",
            created_by=self.employee
        )

    def test_employee_cannot_view_admin_pages(self):
        self.client.login(username='employee_user', password='password123')
        
        # Accessing users management view should trigger PermissionDenied (403 status)
        response = self.client.get(reverse('users'))
        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_view_other_users_tickets(self):
        self.client.login(username='employee_user', password='password123')
        
        # Can view own ticket details
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee ticket")
        
        # Logged in as other employee, blocked from accessing ticket
        self.client.login(username='other_user', password='password123')
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_view_all_tickets(self):
        self.client.login(username='manager_user', password='password123')
        
        # Can view own ticket details
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Employee ticket")

    def test_manager_can_add_user(self):
        self.client.login(username='manager_user', password='password123')
        response = self.client.post(reverse('users'), {
            'action': 'add_user',
            'full_name': 'New Employee',
            'email': 'new_emp@gmail.com',
            'department': 'Operations',
            'role': 'employee',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='new_emp@gmail.com').exists())
        new_user = CustomUser.objects.get(email='new_emp@gmail.com')
        self.assertEqual(new_user.role, 'employee')
        self.assertEqual(new_user.department, 'Operations')

    def test_manager_can_add_user_with_colliding_email_prefix(self):
        self.client.login(username='manager_user', password='password123')
        # employee_user username already exists. Let's create one with email employee_user@other.com
        response = self.client.post(reverse('users'), {
            'action': 'add_user',
            'full_name': 'Colliding Employee',
            'email': 'employee_user@other.com',
            'department': 'Security',
            'role': 'employee',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='employee_user@other.com').exists())
        new_user = CustomUser.objects.get(email='employee_user@other.com')
        self.assertEqual(new_user.username, 'employee_user1')

@override_settings(AXES_ENABLED=False)
class SecurityRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username='emp_user',
            email='emp_user@gmail.com',
            password='password123',
            role='employee',
            full_name='Rate Limited User'
        )

    def test_rate_limiting_triggers_on_submissions(self):
        self.client.login(username='emp_user', password='password123')
        url = reverse('create_ticket')
        
        # Submit 5 ticket requests (Allowed)
        for i in range(5):
            response = self.client.post(url, {
                'title': f'Ticket {i}',
                'description': 'Description text',
                'category': 'Hardware',
                'priority': 'Medium'
            })
            self.assertEqual(response.status_code, 302) # Redirect to tickets on success

        # 6th submission should exceed rate limits and return 429
        response = self.client.post(url, {
            'title': 'Ticket 6',
            'description': 'Description text',
            'category': 'Hardware',
            'priority': 'Medium'
        })
        self.assertEqual(response.status_code, 429)

class RESTAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee = CustomUser.objects.create_user(
            username='api_emp',
            email='api_emp@gmail.com',
            password='password123',
            role='employee',
            full_name='API Employee'
        )
        self.manager = CustomUser.objects.create_user(
            username='api_mgr',
            email='api_mgr@gmail.com',
            password='password123',
            role='manager',
            full_name='API Manager'
        )
        self.ticket = Ticket.objects.create(
            title="API ticket",
            description="Testing API",
            category="Hardware",
            priority="Medium",
            created_by=self.employee
        )

    def test_jwt_token_and_tickets_access(self):
        # 1. Obtain token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_emp@gmail.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        access_token = response.data['access']

        # 2. Access tickets via JWT
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get('/api/tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], "API ticket")

    def test_patch_restricted_to_managers(self):
        # Obtain employee token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_emp@gmail.com',
            'password': 'password123'
        })
        access_token_emp = response.data['access']

        # Attempt to patch as employee (should be blocked)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token_emp}')
        response = self.client.patch(f'/api/tickets/{self.ticket.id}/', {'status': 'Investigating'})
        self.assertEqual(response.status_code, 403)

        # Obtain manager token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_mgr@gmail.com',
            'password': 'password123'
        })
        access_token_mgr = response.data['access']

        # Attempt to patch as manager (should succeed)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token_mgr}')
        response = self.client.patch(f'/api/tickets/{self.ticket.id}/', {'status': 'Investigating'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Ticket.objects.get(id=self.ticket.id).status, "Investigating")

@override_settings(AXES_ENABLED=False)
class RegistrationAndUiTests(TestCase):
    def setUp(self):
        self.manager = CustomUser.objects.create_user(
            username='mgr_user',
            email='mgr@gmail.com',
            password='password123',
            role='manager',
            full_name='Manager User'
        )
        self.employee = CustomUser.objects.create_user(
            username='emp_user',
            email='emp@gmail.com',
            password='password123',
            role='employee',
            full_name='Employee User'
        )
        self.open_ticket = Ticket.objects.create(
            title="Open ticket title",
            description="Open ticket description",
            category="Hardware",
            priority="Low",
            created_by=self.employee,
            status="Open"
        )
        self.resolved_ticket = Ticket.objects.create(
            title="Resolved ticket title",
            description="Resolved ticket description",
            category="Software",
            priority="Medium",
            created_by=self.employee,
            status="Resolved"
        )

    def test_registration_flow_success(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'New User',
            'email': 'newuser@gmail.com',
            'department': 'Operations',
            'password': 'securepassword123',
            'confirm_password': 'securepassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(email='newuser@gmail.com').exists())

    def test_registration_validation_empty_fields(self):
        response = self.client.post(reverse('register'), {
            'full_name': '',
            'email': 'newuser@gmail.com',
            'department': 'Operations',
            'password': 'securepassword123',
            'confirm_password': 'securepassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='newuser@gmail.com').exists())

    def test_registration_validation_password_mismatch(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'New User',
            'email': 'newuser@gmail.com',
            'department': 'Operations',
            'password': 'securepassword123',
            'confirm_password': 'differentpassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='newuser@gmail.com').exists())

    def test_registration_validation_duplicate_email(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'Employee User Duplicate',
            'email': 'emp@gmail.com',
            'department': 'Operations',
            'password': 'securepassword123',
            'confirm_password': 'securepassword123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CustomUser.objects.filter(email='emp@gmail.com').count(), 1)

    def test_bulk_close_elements_visibility(self):
        self.client.login(username='mgr_user', password='password123')
        
        response = self.client.get(reverse('tickets'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Close Selected')
        self.assertNotContains(response, 'id="selectAllTickets"')
        self.assertNotContains(response, 'name="selected_tickets"')

        response = self.client.get(reverse('tickets') + '?status=Resolved')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Close Selected')
        self.assertContains(response, 'id="selectAllTickets"')
        self.assertContains(response, 'name="selected_tickets"')

    def test_simplified_filtering(self):
        self.client.login(username='emp_user', password='password123')
        
        response = self.client.get(reverse('tickets') + '?status=Resolved')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resolved ticket title')
        self.assertNotContains(response, 'Open ticket title')

        response = self.client.get(reverse('tickets') + '?search=Open')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Open ticket title')
        self.assertNotContains(response, 'Resolved ticket title')


@override_settings(AXES_ENABLED=False)
class CrudPermissionTests(TestCase):
    def setUp(self):
        self.employee = CustomUser.objects.create_user(
            username='emp1',
            email='emp1@gmail.com',
            password='password123',
            role='employee',
            full_name='Employee One'
        )
        self.other_employee = CustomUser.objects.create_user(
            username='emp2',
            email='emp2@gmail.com',
            password='password123',
            role='employee',
            full_name='Employee Two'
        )
        self.manager = CustomUser.objects.create_user(
            username='mgr1',
            email='mgr1@gmail.com',
            password='password123',
            role='manager',
            full_name='Manager One'
        )
        self.open_ticket = Ticket.objects.create(
            title="Open Ticket",
            description="Open ticket desc",
            category="Hardware",
            priority="Low",
            created_by=self.employee,
            status="Open"
        )
        self.resolved_ticket = Ticket.objects.create(
            title="Resolved Ticket",
            description="Resolved ticket desc",
            category="Hardware",
            priority="Low",
            created_by=self.employee,
            status="Resolved"
        )

    def test_employee_can_edit_own_open_ticket(self):
        self.client.login(username='emp1', password='password123')
        url = reverse('ticket_detail', args=[self.open_ticket.id])
        response = self.client.post(url, {
            'action': 'edit_ticket',
            'title': 'Updated Title',
            'description': 'Updated description',
            'category': 'Software',
            'priority': 'High'
        })
        self.assertEqual(response.status_code, 302)
        self.open_ticket.refresh_from_db()
        self.assertEqual(self.open_ticket.title, 'Updated Title')
        self.assertEqual(self.open_ticket.category, 'Software')
        self.assertEqual(self.open_ticket.priority, 'High')

    def test_employee_cannot_edit_own_resolved_ticket(self):
        self.client.login(username='emp1', password='password123')
        url = reverse('ticket_detail', args=[self.resolved_ticket.id])
        response = self.client.post(url, {
            'action': 'edit_ticket',
            'title': 'New Resolved Title',
            'description': 'New Resolved description',
            'category': 'Software',
            'priority': 'High'
        })
        self.assertEqual(response.status_code, 302)
        self.resolved_ticket.refresh_from_db()
        self.assertEqual(self.resolved_ticket.title, 'Resolved Ticket') # Unchanged

    def test_employee_cannot_edit_others_ticket(self):
        self.client.login(username='emp2', password='password123')
        url = reverse('ticket_detail', args=[self.open_ticket.id])
        # Trying to POST to other employee's ticket detail view should raise PermissionDenied (403 status)
        response = self.client.post(url, {
            'action': 'edit_ticket',
            'title': 'Hacked Title',
            'description': 'Hacked description',
            'category': 'Software',
            'priority': 'High'
        })
        self.assertEqual(response.status_code, 403)
        self.open_ticket.refresh_from_db()
        self.assertEqual(self.open_ticket.title, 'Open Ticket') # Unchanged

    def test_employee_can_delete_own_open_ticket(self):
        self.client.login(username='emp1', password='password123')
        url = reverse('ticket_detail', args=[self.open_ticket.id])
        response = self.client.post(url, {
            'action': 'delete_ticket'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Ticket.objects.filter(id=self.open_ticket.id).exists())

    def test_employee_cannot_delete_own_resolved_ticket(self):
        self.client.login(username='emp1', password='password123')
        url = reverse('ticket_detail', args=[self.resolved_ticket.id])
        response = self.client.post(url, {
            'action': 'delete_ticket'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Ticket.objects.filter(id=self.resolved_ticket.id).exists())

    def test_manager_can_delete_any_ticket(self):
        self.client.login(username='mgr1', password='password123')
        url = reverse('ticket_detail', args=[self.resolved_ticket.id])
        response = self.client.post(url, {
            'action': 'delete_ticket'
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Ticket.objects.filter(id=self.resolved_ticket.id).exists())


@override_settings(AXES_ENABLED=False)
class SettingsPageTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='settings_user',
            email='settings@gmail.com',
            password='Password123!',
            role='employee',
            full_name='Settings Tester'
        )

    def test_settings_requires_login(self):
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_settings_view_accessible_logged_in(self):
        self.client.login(username='settings_user', password='Password123!')
        response = self.client.get(reverse('settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings')
        self.assertContains(response, 'Appearance Theme Mode')
        self.assertContains(response, 'PASSWORD GUIDELINES')

    def test_password_change_success(self):
        self.client.login(username='settings_user', password='Password123!')
        response = self.client.post(reverse('settings'), {
            'action': 'change_password',
            'old_password': 'Password123!',
            'new_password1': 'NewPassword99!',
            'new_password2': 'NewPassword99!',
        })
        self.assertEqual(response.status_code, 302)
        # Check that user can now log in with the new password
        self.client.logout()
        login_success = self.client.login(username='settings_user', password='NewPassword99!')
        self.assertTrue(login_success)

    def test_password_change_failure_wrong_old_password(self):
        self.client.login(username='settings_user', password='Password123!')
        response = self.client.post(reverse('settings'), {
            'action': 'change_password',
            'old_password': 'WrongPassword123',
            'new_password1': 'NewPassword99!',
            'new_password2': 'NewPassword99!',
        })
        self.assertEqual(response.status_code, 302)
        # Check that user CANNOT log in with the new password
        self.client.logout()
        login_success = self.client.login(username='settings_user', password='NewPassword99!')
        self.assertFalse(login_success)
        # Check that they can still log in with the old password
        login_old_success = self.client.login(username='settings_user', password='Password123!')
        self.assertTrue(login_old_success)


from helpdesk.models import TicketLog
from helpdesk.forms import TicketSubmissionForm
from setup_data import seed_data

@override_settings(AXES_ENABLED=False)
class NISTIncidentTrackerTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username='nist_emp',
            email='nist_emp@gmail.com',
            password='password123',
            role='employee',
            full_name='NIST Employee'
        )
        self.manager = CustomUser.objects.create_user(
            username='nist_mgr',
            email='nist_mgr@gmail.com',
            password='password123',
            role='manager',
            full_name='NIST Manager'
        )
        self.ticket = Ticket.objects.create(
            title="Assigned Ticket",
            description="Testing assignment",
            ticket_type="IT Support",
            nist_stage="preparation",
            priority="Medium",
            created_by=self.user,
            assigned_to=self.user
        )

    def test_form_validation(self):
        # Security Incident with Low priority should fail validation
        form_data = {
            'title': 'Test Incident',
            'description': 'Testing Low priority security incident',
            'ticket_type': 'Security Incident',
            'priority': 'Low'
        }
        form = TicketSubmissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('priority', form.errors)

        # IT Support with Low priority should be valid
        form_data_ok = {
            'title': 'Test Incident',
            'description': 'Testing Low priority security incident',
            'ticket_type': 'IT Support',
            'priority': 'Low'
        }
        form_ok = TicketSubmissionForm(data=form_data_ok)
        self.assertTrue(form_ok.is_valid())

    def test_submit_ticket_view(self):
        self.client.login(username='nist_emp', password='password123')
        
        # Valid submit
        response = self.client.post(reverse('submit_ticket'), {
            'title': 'New Ticket',
            'description': 'New Description',
            'ticket_type': 'IT Support',
            'priority': 'High'
        })
        self.assertEqual(response.status_code, 302)
        
        # Check that it auto sets nist_stage to 'detection'
        new_ticket = Ticket.objects.get(title='New Ticket')
        self.assertEqual(new_ticket.nist_stage, 'detection')
        
        # Check TicketLog
        self.assertTrue(TicketLog.objects.filter(ticket=new_ticket).exists())
        log = TicketLog.objects.filter(ticket=new_ticket).first()
        self.assertEqual(log.changed_by, self.user)

    def test_submit_ticket_rate_limiting(self):
        self.client.login(username='nist_emp', password='password123')
        url = reverse('submit_ticket')
        
        # Submit 5 times
        for i in range(5):
            res = self.client.post(url, {
                'title': f'Rate Limit Ticket {i}',
                'description': 'Rate limiting description',
                'ticket_type': 'IT Support',
                'priority': 'High'
            })
            self.assertEqual(res.status_code, 302)

        # 6th time should be rate limited with HTTP 429
        res = self.client.post(url, {
            'title': 'Rate Limit Ticket 6',
            'description': 'Rate limiting description',
            'ticket_type': 'IT Support',
            'priority': 'High'
        })
        self.assertEqual(res.status_code, 429)
        self.assertContains(res, "Too many requests. Please wait before submitting again.", status_code=429)

    def test_update_ticket_stage_view(self):
        self.client.login(username='nist_emp', password='password123')
        
        # Update stage to containment
        response = self.client.post(reverse('update_ticket_stage', args=[self.ticket.id]), {
            'nist_stage': 'containment'
        })
        self.assertEqual(response.status_code, 302)
        
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.nist_stage, 'containment')
        
        # Check TicketLog
        log = TicketLog.objects.filter(ticket=self.ticket).order_by('-id').first()
        self.assertIn("NIST stage updated from preparation to containment.", log.change_description)

    def test_ticket_list_view_filtering(self):
        self.client.login(username='nist_emp', password='password123')
        
        # Request assigned tickets list
        response = self.client.get(reverse('ticket_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assigned Ticket")

        # Create another ticket not assigned to the user
        other_ticket = Ticket.objects.create(
            title="Unassigned Ticket",
            description="Testing assignment",
            ticket_type="IT Support",
            nist_stage="preparation",
            priority="Medium",
            created_by=self.user,
            assigned_to=None
        )
        response = self.client.get(reverse('ticket_list'))
        self.assertNotContains(response, "Unassigned Ticket")

    def test_jwt_api_endpoints(self):
        # 1. Obtain token
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post(reverse('token_obtain_pair'), {
            'username': 'nist_emp@gmail.com',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 200)
        token = response.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # 2. Get tickets
        res_get = client.get('/api/tickets/')
        self.assertEqual(res_get.status_code, 200)
        
        # 3. Create ticket via API
        res_post = client.post('/api/tickets/create/', {
            'title': 'API NIST Ticket',
            'description': 'API description',
            'ticket_type': 'Security Incident',
            'priority': 'High'
        })
        self.assertEqual(res_post.status_code, 201)
        self.assertEqual(res_post.data['title'], 'API NIST Ticket')
        self.assertEqual(res_post.data['nist_stage'], 'detection')
        
        # 4. Try creating low priority security incident (should fail)
        res_post_fail = client.post('/api/tickets/create/', {
            'title': 'API NIST Ticket Fail',
            'description': 'API description',
            'ticket_type': 'Security Incident',
            'priority': 'Low'
        })
        self.assertEqual(res_post_fail.status_code, 400)


@override_settings(AXES_ENABLED=False)
class SeedDataTests(TestCase):
    def test_seed_data_does_not_reset_existing_user_passwords(self):
        manager = CustomUser.objects.create_user(
            username='admin',
            email='admin@gmail.com',
            password='CustomPassword123!',
            role='manager',
            full_name='Alice Johnson'
        )

        seed_data()

        manager.refresh_from_db()
        self.assertTrue(manager.check_password('CustomPassword123!'))
        self.assertFalse(manager.check_password('admin123'))


@override_settings(AXES_ENABLED=False)
class TicketUniqueTitleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username='test_user',
            email='test@gmail.com',
            password='password123',
            role='employee',
            full_name='Test Employee'
        )
        self.existing_ticket = Ticket.objects.create(
            title="Duplicate Title",
            description="First ticket description",
            category="Hardware",
            priority="Medium",
            created_by=self.user
        )

    def test_ticket_create_view_duplicate_title(self):
        self.client.login(username='test_user', password='password123')
        # Try to create a ticket with the same title
        response = self.client.post(reverse('create_ticket'), {
            'title': 'Duplicate Title',
            'category': 'Software',
            'priority': 'High',
            'description': 'Second ticket description'
        })
        # It should render the template with 200 (not redirect/crash)
        self.assertEqual(response.status_code, 200)
        # Check that the error message is present in the context/messages
        messages_list = list(response.context['messages'])
        self.assertTrue(any("You have already created a ticket with this title." in m.message for m in messages_list))
        # Ensure count is still 1
        self.assertEqual(Ticket.objects.filter(created_by=self.user).count(), 1)

    def test_submit_ticket_view_duplicate_title(self):
        self.client.login(username='test_user', password='password123')
        response = self.client.post(reverse('submit_ticket'), {
            'title': 'Duplicate Title',
            'category': 'Software',
            'priority': 'High',
            'description': 'Second ticket description',
            'ticket_type': 'IT Support'
        })
        self.assertEqual(response.status_code, 200)
        # Form should contain field error on title
        form = response.context['form']
        self.assertIn('title', form.errors)
        self.assertEqual(form.errors['title'], ["You have already created a ticket with this title."])
        # Ensure count is still 1
        self.assertEqual(Ticket.objects.filter(created_by=self.user).count(), 1)

    def test_api_create_ticket_duplicate_title(self):
        client = APIClient()
        token_response = client.post(reverse('token_obtain_pair'), {
            'username': 'test@gmail.com',
            'password': 'password123'
        })
        self.assertEqual(token_response.status_code, 200)
        token = token_response.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Try to post duplicate ticket
        response = client.post('/api/tickets/create/', {
            'title': 'Duplicate Title',
            'description': 'Second ticket description',
            'ticket_type': 'Security Incident',
            'priority': 'High'
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], "You have already created a ticket with this title.")
        # Ensure count is still 1
        self.assertEqual(Ticket.objects.filter(created_by=self.user).count(), 1)


class MileageAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver = CustomUser.objects.create_user(
            username='driver_test',
            email='driver@gmail.com',
            password='password123',
            role='employee',
            full_name='Driver Test'
        )
        self.manager = CustomUser.objects.create_user(
            username='manager_test',
            email='manager@gmail.com',
            password='password123',
            role='manager',
            full_name='Manager Test'
        )
        self.report = MileageReport.objects.create(
            driver=self.driver,
            mileage=150.50,
            dashboard_alert="Engine light on",
            fleet_valuation=500000.00,
            procurement_cost=25000.00
        )

    def test_mileage_submission_success(self):
        # Obtain driver token
        token_res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'driver@gmail.com',
            'password': 'password123'
        })
        self.assertEqual(token_res.status_code, 200)
        token = token_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Post new mileage report
        response = self.client.post('/api/mileage/', {
            'mileage': 200.75,
            'dashboard_alert': 'Tire pressure low'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(MileageReport.objects.filter(driver=self.driver).count(), 2)

    def test_driver_retrieval_masks_values(self):
        # Obtain driver token
        token_res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'driver@gmail.com',
            'password': 'password123'
        })
        token = token_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(f'/api/mileage/{self.report.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['fleet_valuation'], "$*,***,***.**")
        self.assertEqual(response.data['procurement_cost'], "$**,***.**")

    def test_manager_retrieval_unmasked_values(self):
        # Obtain manager token
        token_res = self.client.post(reverse('token_obtain_pair'), {
            'username': 'manager@gmail.com',
            'password': 'password123'
        })
        token = token_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(f'/api/mileage/{self.report.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data['fleet_valuation']), 500000.00)
        self.assertEqual(float(response.data['procurement_cost']), 25000.00)

    def test_unauthenticated_api_blocked(self):
        response = self.client.get('/api/mileage/')
        self.assertEqual(response.status_code, 401)



