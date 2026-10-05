from django.conf import settings


def site_context(request):
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Learnix'),
        'DEBUG': settings.DEBUG,
    }
