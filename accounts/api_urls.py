from django.urls import path

from . import api_views

urlpatterns = [
    path('register/', api_views.RegisterView.as_view(), name='api-register'),
    path('login/', api_views.LoginView.as_view(), name='api-login'),
    path('logout/', api_views.LogoutView.as_view(), name='api-logout'),
    path('me/', api_views.MeView.as_view(), name='api-me'),
]
