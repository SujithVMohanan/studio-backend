from rest_framework import serializers

from apps.bookings.models import Booking
from apps.studios.models import ClassSession
from apps.studios.serializer import CLASS_ID_NAMESPACE
from core.encryption.fields import EncodedIdField
from core.utils.serializers import BlankNullsMixin

BOOKING_ID_NAMESPACE = Booking._meta.label_lower


class ClassSummarySchema(BlankNullsMixin, serializers.ModelSerializer):
    uid             = EncodedIdField(namespace=CLASS_ID_NAMESPACE, source="id", read_only=True)
    studio_name     = serializers.CharField(source="studio.name", read_only=True)
    studio_timezone = serializers.CharField(source="studio.timezone", read_only=True)

    class Meta:
        model = ClassSession
        fields = ("uid", "studio_name", "studio_timezone", "starts_at", "duration_minutes", "credit_cost")
        read_only_fields = fields


class BookingSchema(BlankNullsMixin, serializers.ModelSerializer):
    uid           = EncodedIdField(namespace=BOOKING_ID_NAMESPACE, source="id", read_only=True)
    class_session = ClassSummarySchema(read_only=True)

    class Meta:
        model = Booking
        fields = (
            "uid", "class_session", "status", "source", "credits_charged",
            "booked_at", "cancelled_at", "credits_refunded", "cancellation_outcome",
        )
        read_only_fields = fields
