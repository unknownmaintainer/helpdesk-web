from django.apps import AppConfig
from django.db.models.signals import post_migrate

def update_superusers(sender, **kwargs):
    try:
        from .models import CustomUser
        CustomUser.objects.filter(is_superuser=True).exclude(role='manager').update(role='manager')
    except Exception:
        pass

class HelpdeskConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'helpdesk'

    def ready(self):
        post_migrate.connect(update_superusers, sender=self)
