import itertools
from datetime import timedelta
from uuid import uuid4

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.bookings.services.booking_service import BookingService
from apps.credits.services.credit_service import CreditService
from apps.studios.models import ClassSession, Studio
from apps.users.models import User
from core.tests.helpers import NOW
from core.utils import clock


@pytest.fixture(autouse=True)
def _fast_settings(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.AUTH_THROTTLE_DISABLED = True
    cache.clear()


@pytest.fixture
def staff(db) -> User:
    return User.objects.create_user(
        email="staff@test.local", password="pass", role=User.Role.STAFF, full_name="Staff"
    )


@pytest.fixture
def make_member(db):
    counter = itertools.count(1)

    def _make() -> User:
        n = next(counter)
        return User.objects.create_user(
            email=f"member{n}@test.local", password="pass", role=User.Role.MEMBER, full_name=f"Member {n}"
        )

    return _make


@pytest.fixture
def member(make_member) -> User:
    return make_member()


@pytest.fixture
def other_member(make_member) -> User:
    return make_member()


@pytest.fixture
def studio(staff) -> Studio:
    return Studio.objects.create(
        name="Test Studio", timezone="America/New_York", cancellation_cutoff_hours=4, created_by=staff
    )


@pytest.fixture
def make_class(studio, staff):
    def _make(*, starts_at=None, spots=10, credit_cost=1, duration_minutes=60) -> ClassSession:
        return ClassSession.objects.create(
            studio=studio,
            starts_at=starts_at or NOW + timedelta(days=1),
            duration_minutes=duration_minutes,
            spots=spots,
            credit_cost=credit_cost,
            created_by=staff,
        )

    return _make


@pytest.fixture
def grant(staff):
    def _grant(member, credits, *, granted_on=None, expires_on=None, now=NOW):
        today = clock.utc_today(now)
        return CreditService.grant_pack(
            actor=staff,
            validated_data={
                "member_uid": member.id,
                "credits": credits,
                "granted_on": granted_on or today,
                "expires_on": expires_on or today + timedelta(days=30),
            },
            now=now,
        )

    return _grant


@pytest.fixture
def book():
    def _book(member, session, *, key=None, now=NOW):
        booking, _ = BookingService.book_class(
            member=member, class_id=session.id, idempotency_key=key or uuid4().hex, now=now
        )
        return booking

    return _book


@pytest.fixture
def client_for():
    def _client(user) -> APIClient:
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _client
