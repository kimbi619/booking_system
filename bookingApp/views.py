from django.shortcuts import render
from rest_framework.views import APIView, status
from rest_framework.response import Response

from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import GenericAPIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework import generics, filters

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
import uuid
from rest_framework.filters import OrderingFilter
from django.db.models import Sum
from django.utils.crypto import get_random_string
from django_filters.rest_framework import DjangoFilterBackend

class TripsListCreateView(generics.ListCreateAPIView):
    queryset = Trip.objects.all()
    # serializer_class = TripsSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TripsSerializer
        return TripWriteSerializer

    def perform_create(self, serializer):
        trip = serializer.save()
        if trip.available_seats is None:
            trip.save()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

class TripRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Trip.objects.all()
    serializer_class = TripsSerializer


class TripFilterView(APIView):  
    @swagger_auto_schema(
        operation_description="Get filtered trips based on origin, destination, and date",
        manual_parameters=[
            openapi.Parameter('origin', openapi.IN_QUERY, description="Origin ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('destination', openapi.IN_QUERY, description="Destination ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('date', openapi.IN_QUERY, description="Trip date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
        ],
        responses={200: TripsSerializer(many=True)}
    )
    def get(self, request):
        origin = request.query_params.get('origin', None)
        destination = request.query_params.get('destination', None)
        trip_date = request.query_params.get('date', None)

        trips = Trip.objects.filter(route__origin__id=origin, route__destination__id=destination, date=trip_date)
        serializer = TripsSerializer(trips, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class TripPartialFilterView(generics.ListAPIView):  
    queryset = Trip.objects.all()
    serializer_class = TripsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'route': ['exact'],
        'bus': ['exact'],
        'departure_time': ['exact', 'gte', 'lte'],
        'arrival_time': ['exact', 'gte', 'lte'],
        'time_of_day': ['exact'],
        'date': ['exact', 'gte', 'lte'],
        'available_seats': ['exact', 'gte', 'lte'],
        'is_active': ['exact'],
    }
    ordering_fields = ['departure_time', 'arrival_time', 'date', 'available_seats']

    @swagger_auto_schema(
        operation_description="Get a filtered list of trips based on various parameters",
        manual_parameters=[
            openapi.Parameter('route', openapi.IN_QUERY, description="Filter by route ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('bus', openapi.IN_QUERY, description="Filter by bus ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('departure_time', openapi.IN_QUERY, description="Filter by exact departure time (HH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('departure_time__gte', openapi.IN_QUERY, description="Filter by departure time greater than or equal to (HH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('departure_time__lte', openapi.IN_QUERY, description="Filter by departure time less than or equal to (HH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('arrival_time', openapi.IN_QUERY, description="Filter by exact arrival time (HH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('arrival_time__gte', openapi.IN_QUERY, description="Filter by arrival time greater than or equal to (HH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('arrival_time__lte', openapi.IN_QUERY, description="Filter by arrival time less than or equal to (HH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('time_of_day', openapi.IN_QUERY, description="Filter by time of day (morning/evening)", type=openapi.TYPE_STRING),
            openapi.Parameter('date', openapi.IN_QUERY, description="Filter by exact date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('date__gte', openapi.IN_QUERY, description="Filter by date greater than or equal to (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('date__lte', openapi.IN_QUERY, description="Filter by date less than or equal to (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('available_seats', openapi.IN_QUERY, description="Filter by exact number of available seats", type=openapi.TYPE_INTEGER),
            openapi.Parameter('available_seats__gte', openapi.IN_QUERY, description="Filter by available seats greater than or equal to", type=openapi.TYPE_INTEGER),
            openapi.Parameter('available_seats__lte', openapi.IN_QUERY, description="Filter by available seats less than or equal to", type=openapi.TYPE_INTEGER),
            openapi.Parameter('is_active', openapi.IN_QUERY, description="Filter by active status (true/false)", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('ordering', openapi.IN_QUERY, description="Order results by field (prefix with '-' for descending order)", type=openapi.TYPE_STRING),
        ],
        responses={200: TripsSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AvailableSeatsView(APIView):
    def get(self, request):
        bus_id = request.query_params.get('bus_id')
        trip_id = request.query_params.get('trip_id')

        if not bus_id or not trip_id:
            return Response({"error": "Both bus_id and trip_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bus = get_object_or_404(Bus, id=bus_id)
            trip = get_object_or_404(Trip.objects.select_related('bus__bus_type'), id=trip_id, bus=bus)
        except (Bus.DoesNotExist, Trip.DoesNotExist):
            return Response({"error": "Invalid bus_id or trip_id."}, status=status.HTTP_404_NOT_FOUND)

        booked_seats = trip.booking_set.aggregate(Sum('seats'))['seats__sum'] or 0
        total_seats = trip.available_seats if trip.available_seats is not None else trip.bus.bus_type.capacity
        available_seats = max(0, total_seats - booked_seats)

        return Response({
            "bus": {
                "id": bus.id,
                "registration_number": bus.registration_number,
                "bus_type": bus.bus_type.name,
                "capacity": bus.bus_type.capacity
            },
            "trip": {
                "id": trip.id,
                "route": str(trip.route),
                "departure_time": trip.departure_time.strftime('%H:%M'),
                "arrival_time": trip.arrival_time.strftime('%H:%M'),
                "time_of_day": trip.time_of_day
            },
            "total_seats": total_seats,
            "booked_seats": booked_seats,
            "available_seats": available_seats
        })


class RouteListCreateView(generics.ListCreateAPIView):
    queryset = Route.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RouteFetchSerializer
        return RouteSerializer

    @swagger_auto_schema(
        operation_description="Get all routes",
        responses={200: RouteFetchSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


    @swagger_auto_schema(
        operation_description="Create a new route",
        request_body=RouteSerializer,
        responses={201: RouteSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class RouteRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    retrieve_serializer_class = RouteFetchSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return self.retrieve_serializer_class
        return self.serializer_class
    


class BookingsAPIVIEW(GenericAPIView):
    serializer_class = BookingSerializerManager

    def get(self, request):
        
        bookings = Booking.objects.filter(is_deleted=False)
        serializer = BookingSerializer(bookings, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class BookingRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.filter(is_deleted=False)
    serializer_class = BookingSerializer
    lookup_field = 'id'

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()
    

class BookingItemAPIVIEW(APIView):
    serializer_class = BookingSerializer
    
    def get(self, request, id):
        booking = Booking.objects.filter(is_deleted=False, id=id)
        
        serializer = self.serializer_class(booking)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        booking = Booking.objects.get(id=id)
        serializer = self.serializer_class(booking, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, id):
        booking = Booking.objects.get(id=id)
        booking.is_deleted = True
        booking.save()
        return Response(status=status.HTTP_204_NO_CONTENT)  
      
    
class CityListCreateView(generics.ListCreateAPIView):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class CityRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = City.objects.all()
    serializer_class = CityFetchSerializer


class BusListCreateView(generics.ListCreateAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    permission_classes = [IsAuthenticated]


class BusRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Bus.objects.all()
    serializer_class = BusSerializer
    permission_classes = [IsAuthenticated]


class BusTypeListCreateView(generics.ListCreateAPIView):
    queryset = BusType.objects.all()
    serializer_class = BusTypeSerializer
    permission_classes = [IsAuthenticated]


class CustomerInfoListCreateView(generics.ListCreateAPIView):
    queryset = CustomerInfo.objects.all()
    serializer_class = CustomerInfoSerializer


class BookingCreationView(generics.CreateAPIView):
    serializer_class = BookingCreationSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_data = serializer.validated_data.pop('customer_info')
        booking_data = serializer.validated_data

        customer, created = CustomerInfo.objects.get_or_create(
            identification=customer_data['identification'],
            defaults={**customer_data}
        )

        booking = Booking.objects.create(
            customer_info=customer,
            **booking_data
        )

        # Generate a unique slug for the booking
        booking.slug = f"{booking.id}{uuid.uuid4().hex[:6]}"
        booking.save()


        # Prepare response data
        response_data = {
            "booking_id": booking.id,
            "booking_slug": booking.slug,
            "status": booking.status,
            "customer_info": {
                "id": customer.id,
                "username": customer.username,
                "phone_number": customer.phone_number,
                "identification": customer.identification
            },
            "total_price": str(booking.total_price()),
            "seats": booking.seats
        }

        return Response(response_data, status=status.HTTP_201_CREATED)
    
    # def schedule_payment_check(self, booking, trip):
    #     # Calculate the time to check for payment
    #     now = timezone.now()
    #     departure_time = trip.departure_time
    #     two_hours_before = departure_time - timezone.timedelta(hours=2)
        
    #     if now < two_hours_before:
    #         # Schedule the task to run 2 hours before departure or after a fixed duration, whichever comes first
    #         check_time = min(two_hours_before, now + timezone.timedelta(hours=1))  # Example: 1 hour fixed duration
    #         # Here you would use your task scheduler (e.g., Celery) to schedule the payment check
    #         # For example: check_payment_status.apply_async((booking.id,), eta=check_time)
    #         pass
    #     else:
    #         # If it's already less than 2 hours before departure, schedule the check for 15 minutes from now
    #         check_time = now + timezone.timedelta(minutes=15)
    #         # Schedule the task
    #         # For example: check_payment_status.apply_


class BookingPaymentCreationView(APIView):
    @swagger_auto_schema(
        request_body=BookingPaymentCreationSerializer,
        responses={
            status.HTTP_201_CREATED: BookingPaymentResponseSerializer,
            status.HTTP_400_BAD_REQUEST: 'Bad Request',
        },
        operation_description="Create a new booking with customer information and payment",
        operation_summary="Create Booking with Payment",
    )
    def post(self, request, *args, **kwargs):
        serializer = BookingPaymentCreationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        response_data = {
            "customer_info": CustomerInfoSerializer(result['customer_info']).data,
            "booking": BookingSerializer(result['booking']).data,
            "payment": PaymentSerializer(result['payment']).data
        }

        return Response(response_data, status=status.HTTP_201_CREATED)
    

class InitiatePaymentView(GenericAPIView):
    @transaction.atomic
    def post(self, request):
        booking_id = request.data.get('booking_id')
        provider = request.data.get('provider')
        payer_name = request.data.get('payer_name')
        payer_phone = request.data.get('payer_phone')

        booking = get_object_or_404(Booking, id=booking_id)
        
        payment_method = get_object_or_404(PaymentMethod, name=provider, is_active=True)

        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price(),
            provider=provider,
            transaction_id=get_random_string(32),
            payer_name=payer_name,
            payer_phone=payer_phone
        )

        success = self.simulate_payment_processing()

        if success:
            return Response({
                "message": "Payment initiated successfully",
                "transaction_id": payment.transaction_id,
                "amount": str(payment.amount),
                "provider": payment.provider
            }, status=status.HTTP_200_OK)
        else:
            payment.delete()  
            return Response({
                "message": "Payment initiation failed"
            }, status=status.HTTP_400_BAD_REQUEST)

    def simulate_payment_processing(self):
        import random
        return random.random() < 0.9


class ConfirmPaymentView(APIView):
    @swagger_auto_schema(
        operation_description="verify payment with the backend after it has been made",
        manual_parameters=[
            openapi.Parameter('transaction_id', openapi.IN_QUERY, description="Transaction ID", type=openapi.TYPE_STRING),
        ],
        responses={200: TripsSerializer(many=True)}
    )
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        payment = get_object_or_404(Payment, transaction_id=transaction_id)

        payment.booking.is_paid = True
        payment.booking.save()

        return Response({
            "message": "Payment confirmed successfully",
            "transaction_id": payment.transaction_id,
            "amount": str(payment.amount),
            "provider": payment.provider
        }, status=status.HTTP_200_OK)


class PaymentDetailView(generics.RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    lookup_field = 'transaction_id'

class PaymentMethodListView(generics.ListAPIView):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer