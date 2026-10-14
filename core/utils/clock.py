from datetime import UTC, date, datetime

from django.utils import timezone


def now() -> datetime:
    return timezone.now()


def utc_today(at: datetime) -> date:
    return at.astimezone(UTC).date()
