
from django.urls import path

from .views import *


urlpatterns = [

    # Trips 
    path('trips/', TripsListCreateView.as_view(), name='trip-list-create'),
    path('trips/<int:pk>/', TripRetrieveUpdateDestroyView.as_view(), name='trip-detail'),

    #trip filter
    path('trips/filter/', TripFilterView.as_view(), name='trip-filter'),
    path('trips/filter/partial/', TripPartialFilterView.as_view(), name='trip-filter-partial'),

    #Available seats
    path('available-seats/', AvailableSeatsView.as_view(), name="available-seats"),

    # Routes
    path('routes/', RouteListCreateView.as_view(), name='route-list-create'),
    path('routes/<int:pk>/', RouteRetrieveUpdateDestroyView.as_view(), name='route-detail'),

    # Booking
    path('bookings/', BookingCreationView.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/', BookingItemAPIVIEW.as_view(), name='booking-detail'),

    # Cities
    path('towns/', CityListCreateView.as_view(), name='town-list-create'),
    path('towns/<int:pk>/', CityRetrieveUpdateDestroyView.as_view(), name='town-detail'),

    #Buses
    path('buses/', BusListCreateView.as_view(), name='bus-list-create'),
    path('buses/<int:pk>/', BusRetrieveUpdateDestroyView.as_view(), name='bus-detail'),

    #Bus Types
    path('bus-types/', BusTypeListCreateView.as_view(), name='bus-type-list-create'),

    #Customer Info
    path('customers/', CustomerInfoListCreateView.as_view(), name='customer-info-list-create'),

    path('booking-with-payment/', BookingPaymentCreationView.as_view(), name='create-booking-payment'),


    path('payments/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('payments/confirm/', ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('payments/<str:transaction_id>/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payment-methods/', PaymentMethodListView.as_view(), name='payment-method-list'),

] 

# urlpatterns = [

#     # Routes

#     # Booking
#     path('bookings/<int:id>/', BookingRetrieveUpdateDestroyView.as_view(), name='booking-detail'),

#     # Cities
#     path('towns/', CityListCreateView.as_view(), name='town-list-create'),
#     path('towns/<int:pk>/', CityRetrieveUpdateDestroyView.as_view(), name='town-detail'),

#     # Buses
# ]