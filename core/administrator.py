from django.shortcuts import render
from rest_framework import permissions, viewsets
from rest_framework.views import APIView, Response, status
from rest_framework.generics import GenericAPIView
from django.contrib.auth import authenticate

# Create your views here.
from .models import User
from core.utils import Util
from rest_framework_simplejwt.tokens import RefreshToken


from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes


from rest_framework.parsers import MultiPartParser
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse



def register(request):
    return render(request, 'auth/signup.html')