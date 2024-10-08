from django.db import models
from core.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import requests
from decouple import config
from django.utils.crypto import get_random_string


def encrypt_value(value):
    return value 



class RegionManager(models.Manager):

    def get_queryset(self):

        return super().get_queryset().filter(is_active=True)

    def create_or_update(self, name):

        region, created = self.get_or_create(name=name)

        if not created:

            region.is_active = True

            region.save()

        return region


class CityManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def create_or_update(self, name, region):

        city, created = self.get_or_create(name=name, region=region)

        if not created:

            city.is_active = True
            city.save()

        return city
    
class Region(models.Model):
    """
    Represents geographical regions where Favour Express operates.
    """
    name = models.CharField(_("name of the region"), max_length=100)

    slug = models.SlugField(_("URL-friendly name"), unique=True, blank=True)

    is_active = models.BooleanField(_("indicates if the region is currently active"), default=True)

    objects = models.Manager()
    active = RegionManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Region")
        verbose_name_plural = _("Regions")
        indexes = [models.Index(fields=['slug'])]



class City(models.Model):
    """
    Represents cities or towns within regions.
    """
    name = models.CharField(_("name of the city"), max_length=100)

    slug = models.SlugField(_("URL-friendly name"), unique=True, blank=True)

    region = models.ForeignKey(Region, help_text=_("the region this city belongs to"), on_delete=models.CASCADE)

    abbr = models.CharField(_("abbreviation of the city"), max_length=10, null=True, blank=True)
    
    is_active = models.BooleanField(_("indicates if the city is currently active"), default=True)

    objects = models.Manager()
    active = CityManager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.region.name}"

    class Meta:
        ordering = ['name']
        verbose_name = _("City")
        verbose_name_plural = _("Cities")
        indexes = [models.Index(fields=['slug']), models.Index(fields=['region'])]


class BusTypeManager(models.Manager):

    def create_or_update(self, name, capacity):

        bus_type, created = self.get_or_create(name=name, defaults={'capacity': capacity})

        if not created and bus_type.capacity != capacity:

            bus_type.capacity = capacity

            bus_type.save()

        return bus_type

class BusType(models.Model):
    """
    Defines different types of buses available.
    """
    name = models.CharField(_("name of the bus type"), max_length=50)

    capacity = models.IntegerField(_("seating capacity of this bus type"))

    objects = BusTypeManager()

    def __str__(self):
        return f"{self.name} ({self.capacity} seats)"
    
    class Meta:
        ordering = ['name']
        verbose_name = _("Bus Type")
        verbose_name_plural = _("Bus Types")
        indexes = [models.Index(fields=['name'])]


class Bus(models.Model):
    """
    Represents individual buses in the fleet.
    """
    MAINTENANCE_CHOICES = [
        ('operational', _('Operational')),
        ('maintenance', _('Under Maintenance')),
        ('repair', _('Needs Repair')),
    ]
    
    bus_type = models.ForeignKey(BusType, help_text=_("the type of this bus"), on_delete=models.CASCADE)

    registration_number = models.CharField(_("unique identifier for the bus"), max_length=20, unique=True)

    is_active = models.BooleanField(_("indicates if the bus is currently in service"), default=True)

    maintenance_status = models.CharField(_("determines the status of the bus if in maintainance"), choices=MAINTENANCE_CHOICES, default='operational')

    def __str__(self):
        return f"{self.registration_number} ({self.bus_type.name})"

    class Meta:
        ordering = ['registration_number']
        verbose_name = _("Bus")
        verbose_name_plural = _("Buses")



class Route(models.Model):
    """
    Represents a route between two cities.
    """
    origin = models.ForeignKey(City, related_name='routes_as_origin', help_text=_("starting point of the route"), on_delete=models.CASCADE)

    destination = models.ForeignKey(City, help_text=_(" endpoint of the route"), related_name='routes_as_destination', on_delete=models.CASCADE)

    distance = models.DecimalField(_("distance of the route in kilometers"), null=True, blank=True, max_digits=8, decimal_places=2) 

    base_price = models.DecimalField(_("standard price for this route"), max_digits=10, decimal_places=2)

    vip_price = models.DecimalField(_("standard price for this route"), max_digits=10, decimal_places=2)

    is_active = models.BooleanField(_("indicates if the route is currently offered"), default=True)

    def __str__(self):
        return f"{self.origin.name} to {self.destination.name}"
    
    class Meta:
        unique_together = ['origin', 'destination']
        ordering = ['origin__name', 'destination__name']
        verbose_name = _("Route")
        verbose_name_plural = _("Routes")




class Trip(models.Model):
    """
    Represents a single trip on a route.
    """
    MORNING = 'morning'

    EVENING = 'evening'

    TIME_CHOICES = [
        (MORNING, _('Morning')),
        (EVENING, _('Evening')),
    ]

    route = models.ForeignKey(Route, help_text=_(" the route of this trip"), on_delete=models.CASCADE)

    bus = models.ForeignKey(Bus, help_text=_("the bus assigned to this trip"), on_delete=models.CASCADE)

    departure_time = models.TimeField(_("time of departure"))

    arrival_time = models.TimeField(_("time of arrival"))

    time_of_day = models.CharField(_("morning or evening trip"), max_length=10, choices=TIME_CHOICES)

    created_at = models.DateTimeField(_("When this trip was created"), auto_now=True)

    date = models.DateField(_("Date"), null=True, blank=True)

    updated_at = models.DateTimeField(_("Last update to this field"), auto_now_add=True)

    created_by = models.CharField(_("The user who created this Trip"), null=True, blank=True, max_length=255)

    updateded_by = models.CharField(_("Last user to update this Trip"), null=True, blank=True, max_length=255)

    available_seats = models.IntegerField(_("number of seats available for booking"), null=True, blank=True)

    is_active = models.BooleanField(_("indicates if the trip is currently bookable"), default=True)

    def __str__(self):
        return f"{self.route} - {self.departure_time}"

    def remaining_seats(self):
        if self.available_seats is None:
            if self.bus and self.bus.bus_type and self.bus.bus_type.capacity is not None:
                self.available_seats = self.bus.bus_type.capacity
                self.save()
            else:
                return 0
        
        booked_seats = self.booking_set.aggregate(models.Sum('seats'))['seats__sum'] or 0
        return max(0, self.available_seats - booked_seats)

    def is_fully_booked(self):
        return self.remaining_seats() == 0

    def save(self, *args, **kwargs):
        if self.available_seats is None and self.bus and self.bus.bus_type:
            self.available_seats = self.bus.bus_type.capacity
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['departure_time']
        verbose_name = _("Trip")
        verbose_name_plural = _("Trips")



class CustomerInfo(models.Model):
    """
    Represents information about a user that is required for booking a trip.
    """

    identification = models.CharField(_("ID card number or passport"), max_length=50)

    phone_number = models.CharField(max_length=15)

    username = models.CharField(max_length=150)

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.identification}"
    
    class Meta:
        verbose_name = _("Customer Information")
        verbose_name_plural = _("Customer Information")
        


class Booking(models.Model):
    """
    Represents a booking made by a user.
    """
    
    CREATED = 'created'

    PENDING = 'pending'

    CONFIRMED = 'confirmed'

    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (CONFIRMED, _('Confirmed')),
        (CANCELLED, _('Cancelled')),
    ]

    SERVICE_TYPES = [
        ('vip', _('VIP')),
        ('standard', _('Standard')),
    ]

    customer_info = models.ForeignKey(CustomerInfo, on_delete=models.SET_NULL, null=True)

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)

    seats = models.IntegerField(_("number of seats booked"))

    booking_time = models.DateTimeField(_("when the booking was made"), auto_now_add=True)

    status = models.CharField(_("current status of the booking (pending, confirmed, cancelled)"), max_length=10, choices=STATUS_CHOICES, default=CREATED)

    is_round_trip = models.BooleanField(_("indicates if this is part of a round trip"), default=False)

    return_trip = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    is_deleted = models.BooleanField(_("indicates if this booking is safe delete or not"), default=False)

    slug = models.SlugField(_("URL-friendly name"), unique=True, blank=True)

    service_type = models.CharField(_("service type of the booking"), max_length=10, choices=SERVICE_TYPES, default='standard')

    def __str__(self):
        return f"Booking {self.id} - {self.user.username} - {self.trip}"

    def total_price(self):
        if self.service_type == 'vip':
            return self.seats * self.trip.route.vip_price
        return self.seats * self.trip.route.base_price
    
    def total_seats(self):
        return self.trip.available_seats - self.seats
    
    def is_cancelled(self):
        return self.status == self.CANCELLED
    
    def is_confirmed(self):
        return self.status == self.CONFIRMED
    
    def is_pending(self):
        return self.status == self.PENDING
    
    def is_cancellable(self):
        return (timezone.now() - self.booking_time).days < 1
    
    def send_sms_notification(self):
        url = "https://api.nexah.net/v1/sms"
        headers = {
            "Content-Type": "application/json",
        }
        data = {
            "user": config("SMS_API_USER"),
            "password":config("SMS_API_PASSWORD"),
            "mobiles": self.customer_info.phone_number,
            "senderid": config('SMS_SENDER_ID'),
            "sms": f"Your booking (ID: {self.id}) has been confirmed. Thank you for choosing our service!"
        }
        response = requests.post(url, json=data, headers=headers)
        return response.status_code == 200
    
    # def save(self, *args, **kwargs):
    #     if not self.slug:
    #         self.slug = slugify(self.customer_info.identification)
    #     super().save(*args, **kwargs)

    class Meta:
        ordering = ['-booking_time']
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")


class Payment(models.Model):
    """
    Represents a payment made by a user for a booking.
    """

    MTN = 'mtn'

    ORANGE = 'orange'

    PROVIDER_CHOICES = [
        (MTN, 'MTN Mobile Money'),
        (ORANGE, 'Orange Money'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, null=True, blank=True)

    amount = models.DecimalField(_("amount paid"), max_digits=10, decimal_places=2)

    provider = models.CharField(_("payment provider (MTN or Orange)"), max_length=10, choices=PROVIDER_CHOICES)

    transaction_id = models.CharField(_("unique identifier for the transaction"), max_length=100, unique=True)

    payer_name = models.CharField(_("name of the person who made the payment"), max_length=100)

    payer_phone = models.CharField(_(" phone number used for payment"), max_length=20)

    payment_time = models.DateTimeField(_("when the payment was made"), auto_now_add=True)

    is_refunded = models.BooleanField(_("indicates if the payment has been refunded"), default=False)

    def __str__(self):
        return f"Payment {self.id} - {self.booking.id} - {self.amount}"

    def clean(self):
        if self.amount != self.booking.total_price():
            raise ValidationError(_("Payment amount does not match booking total."))

    def refund(self):
        if not self.is_refunded:
            self.is_refunded = True
            self.save()

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            while True:
                transaction_id = get_random_string(length=20)
                if not Payment.objects.filter(transaction_id=transaction_id).exists():
                    self.transaction_id = transaction_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payment {self.id} - {self.booking.id if self.booking else 'No Booking'} - {self.amount}"

    class Meta:
        ordering = ['-payment_time']
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")



class PaymentMethod(models.Model):
    """
    Represents different payment methods available to users.
    """
    
    name = models.CharField(_("name of the payment method"), max_length=50)

    is_active = models.BooleanField(_("indicates if the payment method is currently available"), default=True)

    client_id = models.CharField(_("client ID for the payment provider"), max_length=100)

    client_secret = models.CharField(_("client secret for the payment provider"), max_length=100)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        self.client_secret = encrypt_value(self.client_secret)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")


class Review(models.Model):
    """
    Represents a review of a trip by a user.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)

    rating = models.PositiveIntegerField(_("rating of the trip (1 to 5)"), validators=[MinValueValidator(1), MaxValueValidator(5)])

    comment = models.TextField(_("optional comment about the trip"))

    review_time = models.DateTimeField(_("when the review was made"), auto_now_add=True)

    def __str__(self):
        return f"Review {self.id} - {self.trip} - {self.rating}"
    
    class Meta:
        ordering = ['-review_time']
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
    


class ContactMessage(models.Model):
    """
    Represents a message sent by a user via the contact form.
    """

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    name = models.CharField(_("name of the person sending the message"), max_length=100)

    email = models.EmailField(_("email address of the person sending the message"))

    message = models.TextField(_("content of the message"))

    sent_time = models.DateTimeField(_("when the message was sent"), auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.sent_time}"
    
    class Meta:
        ordering = ['-sent_time']
        verbose_name = _("Contact Message")
        verbose_name_plural = _("Contact Messages")


class ProDiscount(models.Model):
    """
    Represent users that are eligible for a discount based on their user status and usage of the system
    """
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    discount = models.DecimalField(_("discount percentage"), max_digits=5, decimal_places=2)

    def __str__(self):
        return f"Pro Discount for {self.user.username} - {self.discount}%"
    


class Discount(models.Model):
    """
    Represents a discount code that can be applied to bookings.
    """

    code = models.CharField(_("unique discount code"), max_length=20, unique=True)

    percentage = models.DecimalField(_("discount percentage"), max_digits=5, decimal_places=2)

    start_date = models.DateTimeField(_("start date of the discount code"))

    end_date = models.DateTimeField(_("end date of the discount code"))

    is_active = models.BooleanField(_("indicates if the discount is currently usable"), default=True)

    def __str__(self):
        return f"Discount {self.code} - {self.percentage}%"

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError(_("End date must be after start date."))

    class Meta:
        ordering = ['-start_date']
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")


class SMSNotification(models.Model):
    """
    Represents an SMS notification to be sent to a user.
    """

    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (SENT, _('Sent')),
        (FAILED, _('Failed')),
    ]

    recipient = models.ForeignKey(User, help_text=_("the user receiving the SMS"), on_delete=models.CASCADE)

    message = models.TextField(_("content of the SMS"))

    sent_time = models.DateTimeField(_("when the SMS was sent"), auto_now_add=True)

    is_sent = models.BooleanField(_("indicates if the SMS was successfully sent"), default=False)

    def __str__(self):
        return f"SMS to {self.recipient.username} - {self.sent_time}"