from django import forms
from .models import Ticket
from .validators import sanitize_input, validate_file_type, validate_file_size

class TicketSubmissionForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'description', 'ticket_type', 'priority', 'attachment']

    def clean_title(self):
        return sanitize_input(self.cleaned_data.get('title'))

    def clean_description(self):
        return sanitize_input(self.cleaned_data.get('description'))

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            validate_file_type(attachment)
            validate_file_size(attachment)
        return attachment

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
