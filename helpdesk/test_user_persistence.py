from django.test import TestCase
from django.urls import reverse
from helpdesk.models import CustomUser

class UserPersistenceTests(TestCase):
    def test_register_login_logout_login(self):
        # 1. Register user
        register_url = reverse('register')
        response = self.client.post(register_url, {
            'full_name': 'Test Persistence',
            'email': 'persistence@gmail.com',
            'department': 'Testing',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302) # Redirect to login

        # Verify user was created
        user = CustomUser.objects.get(email='persistence@gmail.com')
        self.assertTrue(user.check_password('Password123!'))

        # 2. First login
        login_url = reverse('login')
        response_login1 = self.client.post(login_url, {
            'email': 'persistence@gmail.com',
            'password': 'Password123!'
        })
        self.assertEqual(response_login1.status_code, 302) # Redirect to dashboard

        # 3. Logout
        logout_url = reverse('logout')
        response_logout = self.client.get(logout_url)
        self.assertEqual(response_logout.status_code, 302) # Redirect to login

        # Verify user still has correct password
        user.refresh_from_db()
        self.assertTrue(user.check_password('Password123!'))

        # 4. Second login
        response_login2 = self.client.post(login_url, {
            'email': 'persistence@gmail.com',
            'password': 'Password123!'
        })
        self.assertEqual(response_login2.status_code, 302) # Should succeed!
