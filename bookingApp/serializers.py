from rest_framework.serializers import ModelSerializer

from .models import Trip, Route, Booking, City, Region, Bus, CustomerInfo, BusType, Payment, PaymentMethod
from core.serializers import LoginSerializer
from rest_framework.fields import IntegerField, SerializerMethodField, JSONField, CharField, DecimalField
from rest_framework import serializers
import uuid
from django.db import transaction
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from utils.helpers import send_sms
import logging

logger = logging.getLogger(__name__)

class RegionSerializer(ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'

class CitySerializer(ModelSerializer):
        class Meta:
            model = City
            fields = '__all__'

class CityFetchSerializer(ModelSerializer):
    region = RegionSerializer()
    class Meta:
        model = City
        fields = '__all__'

class RouteSerializer(ModelSerializer):

    class Meta:
        model = Route
        fields = '__all__'

class RouteFetchSerializer(ModelSerializer):
    origin = CitySerializer()
    destination = CitySerializer()

    class Meta:
        model = Route
        fields = '__all__'


class BookingSerializer(ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'

class BookingSerializerManager(ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'



class BusTypeSerializer(ModelSerializer):
    class Meta:
        model = BusType
        fields = '__all__'


class BusSerializer(ModelSerializer):
    class Meta:
        model = Bus
        fields = '__all__'


class BusTripSerializer(ModelSerializer):
    bus_type = BusTypeSerializer()
    class Meta:
        model = Bus
        fields = '__all__'


class TripsSerializer(ModelSerializer):
    available_seats = SerializerMethodField()

    class Meta:
        model = Trip
        depth=2
        fields = '__all__'


    def get_available_seats(self, obj):
        return obj.remaining_seats()
    
    
class TripWriteSerializer(ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'



class BookingFetchSerializer(ModelSerializer):
    trip = TripsSerializer()
    user = LoginSerializer()
    class Meta:
        model = Booking
        fields = '__all__'


class CustomerInfoSerializer(ModelSerializer):
    class Meta:
        model = CustomerInfo
        fields = '__all__'


class BookingCreationSerializer(ModelSerializer):
    customer_info = CustomerInfoSerializer()
    class Meta:
        model = Booking
        fields = '__all__'


class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'booking', 'amount', 'provider', 'transaction_id', 'payer_name', 'payer_phone', 'payment_time', 'is_refunded']
        read_only_fields = ['id', 'transaction_id', 'payment_time', 'is_refunded']


class PaymentMethodSerializer(ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'is_active']
        extra_kwargs = {'booking': {'required': False}}


class BookingPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['amount', 'provider', 'payer_name', 'payer_phone']
        extra_kwargs = {'booking': {'required': False}}


class BookingPayBookingSerializer(ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'
        extra_kwargs = {'user': {'required': False}}



class BookingPaymentResponseSerializer(serializers.Serializer):
    booking_slug = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    customer_info = CustomerInfoSerializer()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    seats = serializers.JSONField(required=False)
    payment = PaymentSerializer(required=False)


class TripIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['id']

    def to_internal_value(self, data):
        if isinstance(data, int):
            return {'id': data}
        return super().to_internal_value(data)

class BookingPayBookinSerializer(serializers.ModelSerializer):
    trip = serializers.PrimaryKeyRelatedField(queryset=Trip.objects.all())
    class Meta:
        model = Booking
        fields = ['trip', 'seats', 'is_round_trip']


class BookingPaymentCreationSerializer(serializers.Serializer):
    customer_info = CustomerInfoSerializer()
    booking = BookingPayBookinSerializer()
    payment = PaymentSerializer()

    def generate_unique_slug(self, base_slug):
        unique_slug = base_slug
        while Booking.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{get_random_string(4)}"
        return unique_slug

    def create(self, validated_data):
        customer_info_data = validated_data.pop('customer_info')
        booking_data = validated_data.pop('booking')
        payment_data = validated_data.pop('payment')

        with transaction.atomic():
            customer_info, _ = CustomerInfo.objects.get_or_create(
                identification=customer_info_data['identification'],
                defaults=customer_info_data
            )

            base_slug = slugify(f"{customer_info.username}-{booking_data['trip'].id}")
            unique_slug = self.generate_unique_slug(base_slug)

            booking = Booking.objects.create(
                customer_info=customer_info,
                slug=unique_slug,
                **booking_data
            )

            payment = Payment.objects.create(booking=booking, **payment_data)

            message = f"Hello { customer_info.username } reservation aller simple No: {booking.id}, { booking.trip.route.origin.abbr }-{ booking.trip.route.destination.abbr } sur { booking.trip.date } { booking.trip.departure_time }. Presentez vous 30 minutes avant le depart. Merci"
            sms_sent = send_sms(customer_info.phone_number, message)
            print(sms_sent)
            if not sms_sent:
                logger.warning(f"Failed to send confirmation SMS for booking {booking.id}")


        return {
            'customer_info': customer_info,
            'booking': booking,
            'payment': payment
        }

