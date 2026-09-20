"""
Global template context processors for Learnix.
"""

from django.conf import settings

def site_context(request):
    """
    Exposes platform-level brand variables across all templates.
    """
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Learnix'),
        'DEBUG': settings.DEBUG,
    }
