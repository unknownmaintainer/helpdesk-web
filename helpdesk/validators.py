import re
from django.core.exceptions import ValidationError
import os

def sanitize_input(text):
    if not text:
        return text
    # Strip HTML tags
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def validate_file_type(file):
    allowed_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.txt']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file extension: {ext}. Allowed types: {', '.join(allowed_extensions)}")

def validate_file_size(file):
    max_size = 5 * 1024 * 1024 # 5MB
    if file.size > max_size:
        raise ValidationError("File size cannot exceed 5MB.")
