from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core.views import health_check_view
from courses.views import StudentDashboardView

urlpatterns = [
    path('healthz/', health_check_view, name='health_check'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('courses/', include('courses.urls')),
    path('payments/', include('payments.urls')),
    path('dashboard/', StudentDashboardView.as_view(), name='dashboard'),
    path('', include('core.urls')),

    path('api/accounts/', include('accounts.api_urls')),
    path('api/courses/', include('courses.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )

handler404 = 'core.views.custom_page_not_found_view'
handler500 = 'core.views.custom_server_error_view'
handler403 = 'core.views.custom_permission_denied_view'
