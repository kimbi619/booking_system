from rest_framework import serializers

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed    

from .models import User
from django.contrib.auth.models import Group,  Permission
from django.utils.translation import gettext_lazy as _


from django.contrib.auth.forms import UserCreationForm
from django import forms
import re
from utils.models import TrackingModel

from django.contrib.auth import authenticate
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


User = get_user_model()

class PhoneBackend(ModelBackend):
    def authenticate(self, request, phone=None, password=None, **kwargs):
        try:
            user = User.objects.get(Q(phone=phone))
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None




class CreateUserManager(UserCreationForm):
    phone_one = forms.CharField(required=False) 
    address_one = forms.CharField(required=False) 
    dob = forms.CharField(required=False) 
    bio = forms.CharField(required=False) 
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'password1', 'password2']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=256, min_length=6, write_only=True)
    phone = serializers.CharField(max_length=20)

    class Meta:
        model = User
        fields = '__all__'
    
    def validate_phone(self, value):
        phone_regex = re.compile(r'^\+\d{1,3}\d{6,12}$')
        
        if not phone_regex.match(value):
            raise serializers.ValidationError(
                _("Invalid phone number format. Please use the format +[country code][number], e.g., +237XXXXXXXXX")
            )
        
        valid_country_codes = ['+237',]
        if not any(value.startswith(code) for code in valid_country_codes):
            raise serializers.ValidationError(
                _("Invalid country code. Supported country codes are: {}").format(", ".join(valid_country_codes))
            )
        
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError(_("A user with this phone number already exists."))
        
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    

    

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'address', 'bio']  
        read_only_fields = ['phone', 'username']    


class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=255, min_length=5)
    class Meta:
        fields = ['phone']
    
    def validate(self, attrs):

        return super().validate(attrs)




class LoginSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=128, write_only=True)
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ['password',]

    groups = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()

    def get_groups(self, obj):
        return list(obj.groups.values_list('name', flat=True))

    def get_user_permissions(self, obj):
        return list(obj.user_permissions.values_list('codename', flat=True))