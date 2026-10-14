from django.urls import path

from apps.bookings.views import CreateBookingApiView, GetBookingsApiView

app_name = "bookings"

urlpatterns = [
    path("create-booking/", CreateBookingApiView.as_view(), name="create-booking"),
    path("get-bookings/", GetBookingsApiView.as_view(), name="get-bookings"),
]