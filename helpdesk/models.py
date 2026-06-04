from cloudinary_storage.storage import MediaCloudinaryStorage
from django.db import models
from django.contrib.auth.models import AbstractUser

cloudinary_storage = MediaCloudinaryStorage()

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager', 'IT Manager'),
    )
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    department = models.CharField(max_length=100, default='IT & Systems')
    profile_picture = models.ImageField(upload_to='profile_pictures/', storage=cloudinary_storage, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notify_tickets = models.BooleanField(default=True)
    notify_security = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name or self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'manager'
        super().save(*args, **kwargs)

class Ticket(models.Model):
    CATEGORY_CHOICES = (
        ('Hardware', 'Hardware'),
        ('Software', 'Software'),
        ('Network', 'Network'),
        ('Account', 'Account'),
        ('Security', 'Security'),
    )
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    )
    STATUS_CHOICES = (
        ('Open', 'Open'),
        ('Investigating', 'Investigating'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    )
    TICKET_TYPE_CHOICES = (
        ('IT Support', 'IT Support'),
        ('Security Incident', 'Security Incident'),
    )
    NIST_STAGE_CHOICES = (
        ('preparation', 'Preparation'),
        ('detection', 'Detection'),
        ('containment', 'Containment'),
        ('recovery', 'Recovery'),
        ('closed', 'Closed'),
    )
    SOURCE_CHOICES = (
        ('employee', 'Employee Report'),
        ('firewall', 'Firewall Alert'),
        ('antivirus', 'Antivirus Alert'),
        ('network', 'Network Monitor'),
        ('monitoring', 'Security Monitoring Tool'),
    )

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tickets_created')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets_assigned')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Hardware')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    ticket_type = models.CharField(max_length=50, choices=TICKET_TYPE_CHOICES, default='IT Support')
    nist_stage = models.CharField(max_length=50, choices=NIST_STAGE_CHOICES, default='preparation')
    description = models.TextField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='employee')
    attachment = models.FileField(upload_to='attachments/tickets/', storage=cloudinary_storage, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['title', 'created_by']
        indexes = [
            models.Index(fields=['nist_stage']),
            models.Index(fields=['created_by']),
            models.Index(fields=['is_resolved']),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_resolved and self.nist_stage != 'closed':
            raise ValidationError("Resolved tickets must be Closed.")
        if self.ticket_type == 'Security Incident' and self.priority == 'Low':
            raise ValidationError({'priority': "Security tickets cant be Low priority."})

    @property
    def attachment_filename(self):
        import os
        return os.path.basename(self.attachment.name) if self.attachment else ""

    @property
    def nist_equivalent(self):
        mapping = {
            'Open': 'Detection',
            'Investigating': 'Analysis / Containment',
            'Resolved': 'Recovery',
            'Closed': 'Post-Incident Review'
        }
        return mapping.get(self.status, '')

    @property
    def status_badge_class(self):
        mapping = {
            'Open': 'b-open',
            'Investigating': 'b-inprogress',
            'Resolved': 'b-resolved',
            'Closed': 'b-closed'
        }
        return mapping.get(self.status, 'b-open')

    def __str__(self):
        return f"#{self.id} - {self.title}"

    def save(self, *args, **kwargs):
        if self.pk:
            orig = Ticket.objects.get(pk=self.pk)
            
            # 1. If nist_stage changed, update status and is_resolved
            if self.nist_stage != orig.nist_stage:
                if self.nist_stage in ['preparation', 'detection']:
                    self.status = 'Open'
                    self.is_resolved = False
                elif self.nist_stage == 'containment':
                    self.status = 'Investigating'
                    self.is_resolved = False
                elif self.nist_stage == 'recovery':
                    self.status = 'Resolved'
                    self.is_resolved = True
                elif self.nist_stage == 'closed':
                    self.status = 'Closed'
                    self.is_resolved = True
            
            # 2. If status changed, update nist_stage and is_resolved
            elif self.status != orig.status:
                if self.status == 'Open':
                    if self.nist_stage not in ['preparation', 'detection']:
                        self.nist_stage = 'detection'
                    self.is_resolved = False
                elif self.status == 'Investigating':
                    self.nist_stage = 'containment'
                    self.is_resolved = False
                elif self.status == 'Resolved':
                    self.nist_stage = 'recovery'
                    self.is_resolved = True
                elif self.status == 'Closed':
                    self.nist_stage = 'closed'
                    self.is_resolved = True
            
            # 3. If is_resolved changed, update status and nist_stage
            elif self.is_resolved != orig.is_resolved:
                if self.is_resolved:
                    if self.status not in ['Resolved', 'Closed']:
                        self.status = 'Resolved'
                    if self.nist_stage not in ['recovery', 'closed']:
                        self.nist_stage = 'recovery'
                else:
                    if self.status in ['Resolved', 'Closed']:
                        self.status = 'Open'
                    if self.nist_stage in ['recovery', 'closed']:
                        self.nist_stage = 'detection'
        else:
            # New ticket initial sync
            if self.status != 'Open':
                if self.status == 'Investigating':
                    self.nist_stage = 'containment'
                    self.is_resolved = False
                elif self.status == 'Resolved':
                    self.nist_stage = 'recovery'
                    self.is_resolved = True
                elif self.status == 'Closed':
                    self.nist_stage = 'closed'
                    self.is_resolved = True
            elif self.nist_stage != 'preparation':
                if self.nist_stage == 'detection':
                    self.status = 'Open'
                    self.is_resolved = False
                elif self.nist_stage == 'containment':
                    self.status = 'Investigating'
                    self.is_resolved = False
                elif self.nist_stage == 'recovery':
                    self.status = 'Resolved'
                    self.is_resolved = True
                elif self.nist_stage == 'closed':
                    self.status = 'Closed'
                    self.is_resolved = True
            elif self.is_resolved:
                self.status = 'Resolved'
                self.nist_stage = 'recovery'
            else:
                self.status = 'Open'
                self.nist_stage = 'preparation'
                self.is_resolved = False

        super().save(*args, **kwargs)


class TicketUpdate(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='updates')
    comment = models.TextField()
    updated_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Update on #{self.ticket.id} by {self.updated_by.username}"

class LoginAttempt(models.Model):
    email_attempted = models.EmailField(max_length=254)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.email_attempted} - {status} at {self.timestamp}"

class TicketLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    change_description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.ticket:
            return f"Log #{self.id} for Ticket #{self.ticket.id} by {self.changed_by.username}"
        else:
            return f"Log #{self.id} (Account) by {self.changed_by.username}"


class IncidentAuditLog(models.Model):
    """Rich per-ticket audit trail shown on ticket detail page."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='audit_logs')
    actor = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    actor_label = models.CharField(max_length=200, blank=True,
        help_text="Human-readable actor name, e.g. 'Firewall Service' or 'IT Manager Alice'")
    action = models.TextField(help_text="Human-readable description of what happened")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.actor_label}: {self.action[:60]}"


class MileageReport(models.Model):
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mileage_reports')
    mileage = models.DecimalField(max_digits=10, decimal_places=2)
    dashboard_alert = models.TextField(blank=True, default='')
    fleet_valuation = models.DecimalField(max_digits=15, decimal_places=2, default=1250000.00)
    procurement_cost = models.DecimalField(max_digits=15, decimal_places=2, default=45000.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report #{self.id} by {self.driver.username} - Mileage: {self.mileage}"
