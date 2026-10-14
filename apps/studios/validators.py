from functools import cache
from zoneinfo import available_timezones

from rest_framework import serializers


@cache
def _zones() -> frozenset[str]:
    return frozenset(available_timezones())


def validate_iana_timezone(value: str) -> str:
    value = value.strip()
    if value not in _zones():
        raise serializers.ValidationError("Enter a valid IANA timezone, for example America/New_York.")
    return value
