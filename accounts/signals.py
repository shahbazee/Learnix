"""
Signals for the accounts application.
Automatically provisions a UserProfile upon User creation.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """
    Ensures every Django User has an associated UserProfile.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
