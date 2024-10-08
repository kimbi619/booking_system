from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.utils.translation import gettext_lazy as _
import uuid
from django_extensions.db.models import TimeStampedModel, ActivatorModel

from safedelete.models import SafeDeleteModel
from django.contrib.postgres.fields import ArrayField

# Create your models here.
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.models import Group
from django.db import migrations
from django.utils.text import slugify


from datetime import datetime, timedelta
from utils.models import TrackingModel




class customUserManager(UserManager):
    def _create_user(self, username, phone, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError("The given username must be set")
        if not phone:
            raise ValueError("The given phone must be set")
        
        # email = self.normalize_email(email)
        # phone = self.normalize_email(phone)
        

        username = self.model.normalize_username(username)
        user = self.model(username=username, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


    def create_user(self, phone, username=None, password=None, **extra_fields):
        
        if not username:

            if "first_name" in extra_fields and "last_name" in extra_fields:
                username = self.generate_username(extra_fields["first_name"], extra_fields["last_name"])

            else:
                raise ValueError("Username cannot be generated without first name and last name")

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(username, phone, password, **extra_fields)



    def create_superuser(self, phone, username=None,  password=None, **extra_fields):
        
        if not username:
            if "first_name" in extra_fields and "last_name" in extra_fields:
                username = self.generate_username(extra_fields["first_name"], extra_fields["last_name"])

            else:
                raise ValueError("Username cannot be generated without first name and last name")
            
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(username, phone, password, **extra_fields)


    def generate_username(self, first_name, last_name):
        """
        Generate a username based on the first name and last name.
        """
       
        base_username = self.model.normalize_username(first_name + last_name)
        username = base_username
        counter = 1
       
        while self.model.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username



class User(AbstractBaseUser, PermissionsMixin, TrackingModel):
    """
    Custom user model with enhanced fields for better user management.
    An abstract base class implementing a fully featured User model with
    admin-compliant permissions.

    Email and password are required. Other fields are optional.
    """
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True, 
        blank=True,
        null=True,
        help_text=_(
            "Optional. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    
    first_name = models.CharField(_("first name"), max_length=150, blank=True,
                                  help_text=_("User's first name"))
    
    last_name = models.CharField(_("last name"), max_length=150, blank=True,
                                 help_text=_("User's last name"))
    
    email = models.EmailField(_("email address"), null=True, blank=True,
                              help_text=_("User's email address (optional)"))
    
    id_number = models.CharField(max_length=22, null=True, blank=True,
        help_text=_("User ID card or passport number"), unique=True)

    date_of_birth = models.DateField(null=True, blank=True,
                                     help_text=_("User's date of birth"))
    
    avatar = models.ImageField(upload_to='avatars', null=True, blank=True,
                               help_text=_("User's profile picture"))
    
    phone = models.CharField(_("Mobile contact number"), max_length=20, unique=True, blank=False, null=False,
                             help_text=_("User's primary phone number"))
    
    phone_verified = models.BooleanField(_("phone verified"), default=False,
        help_text=_("Indicates whether the user's phone number has been verified"),
    )

    phone_verification_code = models.CharField(max_length=6, null=True, blank=True,
        help_text=_("Verification code for phone number"), unique=True)

    address = models.CharField(_('Residential address'), max_length=256, null=True, blank=True,
                               help_text=_("User's primary residential address"))

    bio = models.TextField(_("Biography"), max_length=500, null=True, blank=True,
                           help_text=_("A brief description about the user"))
    
    address_alt = models.CharField(_('Alternative address'), max_length=256, null=True, blank=True,
                                   help_text=_("User's secondary address"))

    default_language = models.CharField(_("Preferred language"), max_length=50, null=True, blank=True,
                                        help_text=_("User's preferred language for the interface"))

    secondary_language = models.CharField(_("Secondary language"), max_length=50, null=True, blank=True,
                                          help_text=_("User's secondary language preference"))

    profile = models.JSONField(_("coverage"), null=True, blank=True, help_text=_("JSON field detailing the profile settings of the user"))

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    
    is_married = models.BooleanField(
        _("Is Married"),
        default=False,
        help_text=_("Indicates whether the user is married."),
    )

    has_children = models.BooleanField(
        _("Has Children"),
        default=False,
        help_text=_("Indicates whether the user has children."),
    )

    number_of_children = models.IntegerField(
        _("Number of Children"),
        default=0,
        help_text=_("Number of children the user has."),
    )
    
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active. Unselect this instead of deleting accounts."),
    )

    date_joined = models.DateTimeField(_("date joined"), default=timezone.now,
                                       help_text=_("Date and time when the user joined the platform"))
    
    email_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Indicates whether the user's email address has been verified"),
    )

    gender = models.CharField(max_length=50, null=True, blank=True,
                              help_text=_("User's gender (optional)"))

    EMAIL_FIELD = "phone"
    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name", "last_name"]


    objects = customUserManager()

    def save(self, *args, **kwargs):
        if not self.username:

            base_username = slugify(self.first_name + self.last_name)
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
        
            self.username = username
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name
    
    def __str__(self):
        return self.email
    
    def token(self):
        token = RefreshToken.for_user(self)
        return {
            "refresh": str(token),
            "access": str(token.access_token),
        }
    
    def get_username(self):
        return self.username
    


class BaseModel(TimeStampedModel, ActivatorModel, SafeDeleteModel):
    """
    Base model for all other models in the system, providing common fields and functionality.
    """
    id = models.UUIDField(
        default=uuid.uuid4, unique=True, primary_key=True,
        help_text=_("Unique identifier for the record")
    )
    
    is_deleted = models.BooleanField(default=False,
                                     help_text=_("Indicates if the record has been soft-deleted"))
    
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True,
                                      help_text=_("Date and time when the record was created"))
    
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True,
                                      help_text=_("Date and time when the record was last updated"))
    
    created_by = models.CharField(_("Created by"), max_length=100, null=True, blank=True,
                                  help_text=_("Email of the user who created the record"))

    updated_by = models.CharField(_("Updated by"), max_length=100, null=True, blank=True,
                                  help_text=_("Email of the user who last updated the record"))

    class Meta:
        abstract = True

