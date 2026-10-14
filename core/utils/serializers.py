from datetime import datetime
from typing import Any

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers


class StrictIntegerField(serializers.IntegerField):
    def to_internal_value(self, data: Any) -> int:
        if isinstance(data, bool):
            self.fail("invalid")
        return super().to_internal_value(data)


class AwareDateTimeField(serializers.DateTimeField):
    default_error_messages = {
        "naive": "Include a timezone offset, for example 2026-10-20T10:00:00Z.",
    }

    def to_internal_value(self, value: Any) -> datetime:
        if isinstance(value, str):
            parsed = parse_datetime(value.strip())
            if parsed is not None and timezone.is_naive(parsed):
                self.fail("naive")
        return super().to_internal_value(value)


class BlankNullsMixin:
    """Render None values as "" in serialized output. Must come before the serializer class in the bases."""

    def to_representation(self, instance: Any) -> dict[str, Any]:
        data: dict[str, Any] = super().to_representation(instance)  # type: ignore[misc]
        return {key: ("" if value is None else value) for key, value in data.items()}
