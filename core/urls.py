
from django.urls import path, re_path, include
from rest_framework_simplejwt.views import (
    TokenRefreshView
)

from django.views.generic.base import TemplateView
from rest_framework.routers import DefaultRouter

from .views import *


urlpatterns = [
    path('register/', RegisterAPIView.as_view()),
    path('login/', LoginAPIView.as_view(), name='Login'),
    path('verify-phone/', VerifyPhoneAPIView.as_view(), name='verify-phone'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UserView.as_view(), name='get_user'),
    path('me/profile/<int:user_id>/', UpdateUserInformation.as_view(), name='update_user'),

    path('verify-email/', VerifyEmail.as_view(), name='verify-email'),
    path('users/', ListUsers.as_view(), name='list_users'),
   
    # RESET PASSWORD
    path('reset-password', ChangePassword.as_view(), name='password_reset_confirm'),
    path('request-password-reset/', RequestPasswordReset.as_view(), name='password_reset'),



] 