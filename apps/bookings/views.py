
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.bookings.schemas import BOOKING_ID_NAMESPACE, BookingSchema, WaitlistEntrySchema
from apps.bookings.serializer import (
    IDEMPOTENCY_HEADER,
    IDEMPOTENCY_MAX_LEN,
    CreateBookingSerializer,
    GetBookingsQuerySerializer,
    GetWaitlistQuerySerializer,
    WaitlistClassSerializer,
)
from apps.bookings.services.booking_service import BookingService
from apps.bookings.services.cancel_service import CancelService
from apps.bookings.services.waitlist_service import WaitlistService
from core.encryption.fields import decode_id_or_404
from core.permissions import IsMemberRole
from core.responses import ResponseInfo


IDEMPOTENCY_PARAMETER = openapi.Parameter(
    name=IDEMPOTENCY_HEADER,
    in_=openapi.IN_HEADER,
    type=openapi.TYPE_STRING,
    required=True,
    description=(
        "Unique per booking attempt. Retrying with the same key "
        "returns the original booking."
    ),
)


class CreateBookingApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class   = CreateBookingSerializer

    @swagger_auto_schema(
        request_body=CreateBookingSerializer,
        manual_parameters=[IDEMPOTENCY_PARAMETER],
        tags=["Bookings"],
        operation_summary="Book a class",
    )
    def post(self, request, *args, **kwargs):

        idempotency_key = (
            request.headers.get(IDEMPOTENCY_HEADER) or ""
        ).strip()

        if not idempotency_key or len(idempotency_key) > IDEMPOTENCY_MAX_LEN:
            return ResponseInfo.validation_error(
                {
                    IDEMPOTENCY_HEADER: [
                        f"Header is required (1-{IDEMPOTENCY_MAX_LEN} characters)."
                    ]
                },
                error_code="IDEMPOTENCY_KEY_REQUIRED",
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        booking, created = BookingService.book_class(
            member=request.user,
            class_id=serializer.validated_data["class_uid"],
            idempotency_key=idempotency_key,
        )

        response_data = BookingSchema(booking).data

        if created:
            return ResponseInfo.created(
                response_data,
                message="Class booked successfully.",
            )

        return ResponseInfo.ok(
            response_data,
            message="Booking already processed for this Idempotency-Key.",
        )


class GetBookingsApiView(generics.ListAPIView):

    permission_classes        = [IsAuthenticated, IsMemberRole]
    serializer_class          = BookingSchema
    query_serializer_class    = GetBookingsQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetBookingsQuerySerializer,
        tags=["Bookings"],
        operation_summary="My bookings",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        query_serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        return BookingService.list_bookings(
            member=self.request.user,
            validated_data=query_serializer.validated_data,
        )


class CancelBookingApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class   = BookingSchema

    @swagger_auto_schema(
        request_body=None,
        tags=["Bookings"],
        operation_summary="Cancel my booking",
    )
    def post(self, request, booking_uid: str, *args, **kwargs):

        booking_id = decode_id_or_404(booking_uid, BOOKING_ID_NAMESPACE)

        booking = CancelService.cancel_booking(
            member=request.user,
            booking_id=booking_id,
        )

        return ResponseInfo.ok(
            BookingSchema(booking).data,
            message="Booking cancelled successfully.",
        )


class JoinWaitlistApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class   = WaitlistClassSerializer

    @swagger_auto_schema(
        request_body=WaitlistClassSerializer,
        tags=["Waitlist"],
        operation_summary="Join waitlist",
    )
    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        entry = WaitlistService.join_waitlist(
            member=request.user,
            class_id=serializer.validated_data["class_uid"],
        )

        return ResponseInfo.created(
            WaitlistEntrySchema(entry).data,
            message="Joined the waitlist.",
        )


class LeaveWaitlistApiView(generics.GenericAPIView):

    permission_classes = [IsAuthenticated, IsMemberRole]
    serializer_class   = WaitlistClassSerializer

    @swagger_auto_schema(
        request_body=WaitlistClassSerializer,
        tags=["Waitlist"],
        operation_summary="Leave waitlist",
    )
    def post(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return ResponseInfo.validation_error(serializer.errors)

        entry = WaitlistService.leave_waitlist(
            member=request.user,
            class_id=serializer.validated_data["class_uid"],
        )

        return ResponseInfo.ok(
            WaitlistEntrySchema(entry).data,
            message="Left the waitlist.",
        )


class GetWaitlistApiView(generics.ListAPIView):

    permission_classes        = [IsAuthenticated, IsMemberRole]
    serializer_class          = WaitlistEntrySchema
    query_serializer_class    = GetWaitlistQuerySerializer

    @swagger_auto_schema(
        query_serializer=GetWaitlistQuerySerializer,
        tags=["Waitlist"],
        operation_summary="My waitlist entries",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        query_serializer = self.query_serializer_class(
            data=self.request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)

        return WaitlistService.list_waitlist(
            member=self.request.user,
            validated_data=query_serializer.validated_data,
        )
