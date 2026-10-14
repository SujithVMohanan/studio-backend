from django.urls import path

from apps.bookings.views import (
    CancelBookingApiView,
    CreateBookingApiView,
    GetBookingsApiView,
    GetWaitlistApiView,
    JoinWaitlistApiView,
    LeaveWaitlistApiView,
)

app_name = "bookings"

urlpatterns = [
    path("create-booking/", CreateBookingApiView.as_view(), name="create-booking"),
    path("get-bookings/", GetBookingsApiView.as_view(), name="get-bookings"),
    path("cancel-booking/<str:booking_uid>/", CancelBookingApiView.as_view(), name="cancel-booking"),
    path("join-waitlist/", JoinWaitlistApiView.as_view(), name="join-waitlist"),
    path("leave-waitlist/", LeaveWaitlistApiView.as_view(), name="leave-waitlist"),
    path("get-waitlist/", GetWaitlistApiView.as_view(), name="get-waitlist"),
]
