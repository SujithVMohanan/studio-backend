
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.bookings.schemas import BookingSchema
from apps.bookings.serializer import (
    IDEMPOTENCY_HEADER,
    IDEMPOTENCY_MAX_LEN,
    CreateBookingSerializer,
    GetBookingsQuerySerializer,
)
from apps.bookings.services.booking_service import BookingService
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

    permission_classes = [IsAuthenticated]
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

    permission_classes        = [IsAuthenticated,]
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
