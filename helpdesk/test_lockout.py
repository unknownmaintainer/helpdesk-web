from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from helpdesk.models import CustomUser

class AxesLockoutTests(TestCase):
    def setUp(self):
        cache.clear()
        # Reset axes attempts
        from axes.models import AccessAttempt
        AccessAttempt.objects.all().delete()
        
        # Create test users
        self.user1 = CustomUser.objects.create_user(
            username='user1',
            email='user1@gmail.com',
            password='password123',
            role='employee',
            full_name='User One'
        )
        self.user2 = CustomUser.objects.create_user(
            username='user2',
            email='user2@gmail.com',
            password='password123',
            role='employee',
            full_name='User Two'
        )

    @override_settings(AXES_ENABLED=True)
    def test_lockout_only_affects_matching_combination(self):
        # We try to log in 5 times unsuccessfully for user1 from IP 1.1.1.1
        login_url = reverse('login')
        
        # Unsuccessful login attempts for user1 from IP 1.1.1.1
        for _ in range(5):
            self.client.post(login_url, {
                'email': 'user1@gmail.com',
                'password': 'wrongpassword'
            }, REMOTE_ADDR='1.1.1.1')
            
        # The 6th attempt should be blocked and show access denied
        response = self.client.post(login_url, {
            'email': 'user1@gmail.com',
            'password': 'password123'
        }, REMOTE_ADDR='1.1.1.1')
        
        # It should render helpdesk/access_denied.html
        self.assertEqual(response.status_code, 429)
        self.assertTemplateUsed(response, 'helpdesk/access_denied.html')

        # Since it is AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True,
        # user2 should still be able to log in from the SAME IP (1.1.1.1)!
        response_user2 = self.client.post(login_url, {
            'email': 'user2@gmail.com',
            'password': 'password123'
        }, REMOTE_ADDR='1.1.1.1')
        self.assertEqual(response_user2.status_code, 302) # Redirect to dashboard

    @override_settings(AXES_ENABLED=True)
    def test_lockout_is_ip_specific(self):
        login_url = reverse('login')
        
        # Unsuccessful login attempts for user1 from IP 1.1.1.1
        for _ in range(5):
            self.client.post(login_url, {
                'email': 'user1@gmail.com',
                'password': 'wrongpassword'
            }, REMOTE_ADDR='1.1.1.1')
            
        # user1 trying to log in from a DIFFERENT IP (2.2.2.2) should succeed!
        response_user1_diff_ip = self.client.post(login_url, {
            'email': 'user1@gmail.com',
            'password': 'password123'
        }, REMOTE_ADDR='2.2.2.2')
        self.assertEqual(response_user1_diff_ip.status_code, 302) # Redirect to dashboard
