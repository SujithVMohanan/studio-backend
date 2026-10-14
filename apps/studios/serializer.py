from typing import Any

from rest_framework import serializers

from apps.studios.models import ClassSession, Studio
from apps.studios.validators import validate_iana_timezone
from core.encryption.fields import EncodedIdField
from core.utils.serializers import AwareDateTimeField, StrictIntegerField

STUDIO_ID_NAMESPACE = Studio._meta.label_lower
CLASS_ID_NAMESPACE  = ClassSession._meta.label_lower


class StudioSerializer(serializers.Serializer):
    
    name                      = serializers.CharField(max_length=150, trim_whitespace=True)
    timezone                  = serializers.CharField(max_length=64)
    cancellation_cutoff_hours = StrictIntegerField(min_value=0, default=4)

    def validate_timezone(self, value: str) -> str:
        return validate_iana_timezone(value)


class GetStudiosQuerySerializer(serializers.Serializer):
    uid  = EncodedIdField(namespace=STUDIO_ID_NAMESPACE, required=False)
    name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_name(self, value: str) -> str | None:
        return value.strip() or None


class CreateClassSerializer(serializers.Serializer):

    studio_uid       = EncodedIdField(namespace=STUDIO_ID_NAMESPACE)
    starts_at        = AwareDateTimeField()
    duration_minutes = StrictIntegerField(min_value=1)
    spots            = StrictIntegerField(min_value=1)
    credit_cost      = StrictIntegerField(min_value=0)


class GetClassesQuerySerializer(serializers.Serializer):
    
    start      = AwareDateTimeField(required=False, help_text="Inclusive, ISO 8601 with offset")
    end        = AwareDateTimeField(required=False, help_text="Exclusive, ISO 8601 with offset")
    studio_uid = EncodedIdField(namespace=STUDIO_ID_NAMESPACE, required=False)
    uid        = EncodedIdField(namespace=CLASS_ID_NAMESPACE, required=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("uid") is not None:
            return attrs
        start, end = attrs.get("start"), attrs.get("end")
        if start is None or end is None:
            raise serializers.ValidationError({"start": ["start and end are required."]})
        if end <= start:
            raise serializers.ValidationError({"end": ["end must be after start."]})
        return attrs