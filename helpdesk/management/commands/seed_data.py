from django.core.management.base import BaseCommand
from helpdesk.models import CustomUser, Ticket, TicketUpdate

class Command(BaseCommand):
    help = 'Seeds database with default users, tickets, and updates.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database...")
        
        # 1. Clear existing database
        TicketUpdate.objects.all().delete()
        Ticket.objects.all().delete()
        CustomUser.objects.all().delete()

        # 2. Create default users
        # Employee
        bob = CustomUser.objects.create_user(
            username='employee',
            email='employee@gmail.com',
            password='password123',
            role='employee',
            full_name='Bob Smith',
            department='Human Resources'
        )
        
        # Manager / Admin
        alice = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@gmail.com',
            password='admin123',
            role='manager',
            full_name='Alice Johnson',
            department='IT & Systems'
        )
        
        # Developer
        charlie = CustomUser.objects.create_user(
            username='dev',
            email='dev@gmail.com',
            password='password123',
            role='employee',
            full_name='Charlie Brown',
            department='Engineering'
        )

        self.stdout.write(self.style.SUCCESS("Users created successfully."))

        # 3. Create default support tickets
        t1 = Ticket.objects.create(
            title="Slow PC Performance",
            description="My corporate desktop is extremely slow to boot and freezes when opening Chrome. I have closed background apps but it persists.",
            category="Hardware",
            priority="Medium",
            status="Open",
            created_by=bob
        )
        
        t2 = Ticket.objects.create(
            title="Outlook Email Sync Issue",
            description="My Outlook client is stuck on 'Working Offline' and does not pull new messages. I can send emails, but not receive.",
            category="Software",
            priority="Low",
            status="Investigating",
            created_by=bob
        )

        t3 = Ticket.objects.create(
            title="Corporate VPN Disconnection",
            description="The Cisco AnyConnect VPN client disconnects every 10 minutes when working remotely, disrupting access to local servers.",
            category="Network",
            priority="High",
            status="Resolved",
            created_by=charlie
        )

        t4 = Ticket.objects.create(
            title="AD Password Reset Request",
            description="I forgot my AD password and my account is currently locked after multiple attempts. I need a reset.",
            category="Account",
            priority="Medium",
            status="Closed",
            created_by=charlie
        )

        self.stdout.write(self.style.SUCCESS("Support tickets seeded."))

        # 4. Seed ticket updates
        TicketUpdate.objects.create(
            ticket=t2,
            comment="Checking your mailbox quota and connectivity settings.",
            updated_by=alice
        )
        TicketUpdate.objects.create(
            ticket=t3,
            comment="Identified a router route mismatch on remote servers. VPN tunnel settings have been refreshed.",
            updated_by=alice
        )
        TicketUpdate.objects.create(
            ticket=t3,
            comment="Issue has been successfully resolved. Checked connection stability and VPN client is stable.",
            updated_by=alice
        )
        TicketUpdate.objects.create(
            ticket=t4,
            comment="Temporary password sent via secure SMS. User confirmed login and reset password. Closing ticket.",
            updated_by=alice
        )

        self.stdout.write(self.style.SUCCESS("Seeding activity completed successfully!"))
