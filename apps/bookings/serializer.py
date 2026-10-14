from rest_framework import serializers

from apps.bookings.models import Booking, WaitlistEntry
from apps.studios.serializer import CLASS_ID_NAMESPACE
from core.encryption.fields import EncodedIdField

IDEMPOTENCY_HEADER  = "Idempotency-Key"
IDEMPOTENCY_MAX_LEN = 255


class CreateBookingSerializer(serializers.Serializer):
    class_uid = EncodedIdField(namespace=CLASS_ID_NAMESPACE)


class GetBookingsQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Booking.Status.choices, required=False)


class WaitlistClassSerializer(serializers.Serializer):
    class_uid = EncodedIdField(namespace=CLASS_ID_NAMESPACE)


class GetWaitlistQuerySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=WaitlistEntry.Status.choices, required=False)
