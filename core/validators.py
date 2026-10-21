import os

from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_MB = 2
ALLOWED_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]


def validate_image_file(value):
    if not value:
        return
    extension = os.path.splitext(value.name)[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            "Only JPG, PNG or WebP images are allowed."
        )
    if value.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise ValidationError(
            f"Image must be at most {MAX_IMAGE_SIZE_MB} MB."
        )
