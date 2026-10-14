from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from rest_framework.exceptions import APIException

from apps.credits.services.credit_service import CreditService

NOW = datetime(2026, 2, 10, 12, 0, tzinfo=UTC)
TODAY = NOW.date()


def balance_of(member, *, now: datetime = NOW) -> int:
    return CreditService.get_balance(member=member, now=now).balance


@contextmanager
def raises_code(code: str):
    with pytest.raises(APIException) as info:
        yield info
    assert getattr(info.value, "error_code", None) == code, info.value
