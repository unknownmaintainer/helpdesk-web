from pathlib import Path

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils.module_loading import import_string


class Command(BaseCommand):
    help = 'Migrate existing FileField/ImageField files to the default storage (Cloudinary). Use --dry-run to preview.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated without making changes')

    def _get_local_path(self, file_field):
        if not file_field:
            return None

        name = (file_field.name or '').lstrip('/')
        if not name:
            return None

        media_url_prefix = getattr(settings, 'MEDIA_URL', '/media/').lstrip('/')
        if media_url_prefix and name.startswith(media_url_prefix):
            name = name[len(media_url_prefix):].lstrip('/')

        candidates = [Path(settings.MEDIA_ROOT) / name]
        if name.startswith('media/'):
            candidates.append(Path(settings.MEDIA_ROOT) / name[len('media/'):])

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Attempt extension fallback for legacy records without a file suffix.
        stem = Path(name).stem
        if not Path(name).suffix:
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                candidate = Path(settings.MEDIA_ROOT) / f"{name}{ext}"
                if candidate.exists():
                    return candidate

        # Fall back to stem-based matching across media files.
        prefix = stem
        for candidate in Path(settings.MEDIA_ROOT).rglob('*'):
            if not candidate.is_file():
                continue
            candidate_stem = candidate.stem
            if candidate_stem == stem or candidate_stem.startswith(stem) or stem.startswith(candidate_stem):
                return candidate

        return None

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        migrated = 0
        skipped = 0

        try:
            storage_cls = import_string(settings.DEFAULT_FILE_STORAGE)
            storage_backend = storage_cls()
        except Exception as e:
            self.stdout.write(self.style.WARNING(
                f"Could not instantiate DEFAULT_FILE_STORAGE: {e}. Falling back to default_storage."
            ))
            storage_backend = default_storage

        for model in apps.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, (models.FileField, models.ImageField)):
                    field_name = field.name
                    qs = model.objects.exclude(**{f"{field_name}": ""}).exclude(**{f"{field_name}__isnull": True})
                    if qs.exists():
                        self.stdout.write(self.style.NOTICE(f"Processing {model.__name__}.{field_name} ({qs.count()} objects)"))
                    for obj in qs:
                        f = getattr(obj, field_name)
                        if not f:
                            skipped += 1
                            continue

                        storage_module = f.storage.__class__.__module__
                        if 'cloudinary' in storage_module.lower():
                            skipped += 1
                            continue

                        if dry_run:
                            self.stdout.write(
                                f"[dry-run] Would migrate: {model.__name__} id={getattr(obj, 'id', 'unknown')} "
                                f"field={field_name} file={f.name} storage={storage_module}"
                            )
                            continue

                        local_path = self._get_local_path(f)
                        if local_path is None:
                            self.stdout.write(self.style.ERROR(
                                f"Skipping {model.__name__} id={getattr(obj, 'id', 'unknown')}: local file not found for {f.name}"
                            ))
                            skipped += 1
                            continue

                        try:
                            with local_path.open('rb') as fh:
                                content = fh.read()

                            new_name = storage_backend.save(local_path.name, ContentFile(content))
                            setattr(obj, field_name, new_name)
                            obj.save(update_fields=[field_name])

                            migrated += 1
                            self.stdout.write(self.style.SUCCESS(
                                f"Migrated: {model.__name__} id={getattr(obj, 'id', 'unknown')} -> {new_name}"
                            ))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(
                                f"Failed to migrate {model.__name__} id={getattr(obj, 'id', 'unknown')}: {e}"
                            ))

        self.stdout.write(self.style.SUCCESS(f"Done. Migrated: {migrated}. Skipped: {skipped}."))
