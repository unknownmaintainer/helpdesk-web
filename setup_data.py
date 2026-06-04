import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'helpdesk_project.settings')
django.setup()

from helpdesk.models import CustomUser, Ticket, TicketUpdate

def seed_data():
    # We keep users if they exist, or create them
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@gmail.com',
            'full_name': 'Rostom Balboa',
            'role': 'manager',
            'department': 'IT Specialist',
            'password': 'admin123'
        },
        {
            'username': 'employee',
            'email': 'employee@gmail.com',
            'full_name': 'Mardion Fuerte',
            'role': 'employee',
            'department': 'Engineering',
            'password': 'password123'
        },
        {
            'username': 'employee2',
            'email': 'employee2@gmail.com',
            'full_name': 'Ella Abainza',
            'role': 'employee',
            'department': 'Human Resources',
            'password': 'password123'
        }
    ]
    
    users = {}
    for ud in users_data:
        # Check by email first
        user = CustomUser.objects.filter(email=ud['email']).first()
        if not user:
            # Check by username
            user = CustomUser.objects.filter(username=ud['username']).first()
            
        if user:
            # Update fields to match current seed configuration (e.g. gmail transition)
            user.email = ud['email']
            user.username = ud['username']
            user.full_name = ud['full_name']
            user.role = ud['role']
            user.department = ud['department']
            if ud['role'] == 'manager':
                user.is_staff = True
                user.is_superuser = True
            user.save()
            print(f"Updated existing user: {user.username} ({user.email})")
        else:
            # Create new user
            user = CustomUser.objects.create_user(
                username=ud['username'],
                email=ud['email'],
                password=ud['password'],
                role=ud['role'],
                full_name=ud['full_name'],
                department=ud['department']
            )
            if ud['role'] == 'manager':
                user.is_staff = True
                user.is_superuser = True
            user.is_active = True
            user.save()
            print(f"Created new user: {user.username} ({user.email})")
            
        users[ud['username']] = user
    
    print("Users seeded successfully.")

    # 2. Seed Tickets (only if database has no tickets to avoid wiping/duplicating live data)
    if not Ticket.objects.exists():
        tickets_data = [
            {
                'created_by': users['employee'],
                'title': 'Slow PC Performance',
                'category': 'Hardware',
                'priority': 'Medium',
                'description': 'My corporate desktop is extremely slow to boot and freezes when opening Chrome. I have closed background apps but it persists.',
                'status': 'Open'
            },
            {
                'created_by': users['employee'],
                'title': 'Outlook Email Sync Issue',
                'category': 'Software',
                'priority': 'Low',
                'description': 'My Outlook client is stuck on "Working Offline" and does not pull new messages. I can send emails, but not receive.',
                'status': 'Investigating'
            },
            {
                'created_by': users['dev'],
                'title': 'Corporate VPN Disconnection',
                'category': 'Network',
                'priority': 'High',
                'description': 'The Cisco AnyConnect VPN client disconnects every 10 minutes when working remotely, disrupting access to local servers.',
                'status': 'Resolved'
            },
            {
                'created_by': users['dev'],
                'title': 'AD Password Reset Request',
                'category': 'Account',
                'priority': 'Medium',
                'description': 'I forgot my AD password and my account is currently locked after multiple attempts. I need a reset.',
                'status': 'Closed'
            }
        ]

        tickets = []
        for td in tickets_data:
            t = Ticket.objects.create(**td)
            tickets.append(t)
        
        print("Tickets seeded successfully.")

        # 3. Seed Ticket Updates
        updates_data = [
            {
                'ticket': tickets[1],  # Outlook Email Sync Issue
                'comment': 'I am looking into this issue. Checking your mailbox quota and connectivity settings.',
                'updated_by': users['admin']
            },
            {
                'ticket': tickets[2],  # Corporate VPN Disconnection
                'comment': 'Identified a router route mismatch on remote servers. VPN tunnel settings have been refreshed.',
                'updated_by': users['admin']
            },
            {
                'ticket': tickets[2],  # Corporate VPN Disconnection
                'comment': 'Issue has been successfully resolved. Checked connection stability and VPN client is stable.',
                'updated_by': users['admin']
            },
            {
                'ticket': tickets[3],  # AD Password Reset
                'comment': 'Temporary password sent via secure SMS. User confirmed login and reset password. Closing ticket.',
                'updated_by': users['admin']
            }
        ]

        for ud in updates_data:
            TicketUpdate.objects.create(**ud)

        print("Ticket updates seeded successfully.")
    else:
        print("Tickets already exist. Skipping ticket/update seeding to preserve live database tickets.")

if __name__ == '__main__':
    seed_data()
