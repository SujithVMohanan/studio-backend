from datetime import UTC, datetime, timedelta

import pytest

from apps.bookings.models import Booking
from apps.bookings.services.cancel_service import CancelService
from apps.credits.models import CreditLedger
from core.tests.helpers import NOW, balance_of, raises_code

pytestmark = pytest.mark.django_db


def cancel(member, booking, at):
    return CancelService.cancel_booking(member=member, booking_id=booking.id, now=at)


def test_cancel_before_cutoff_refunds_in_full(member, grant, make_class, book):
    grant(member, 5)
    booking = book(member, make_class(credit_cost=2))

    result = cancel(member, booking, NOW)

    assert result.status == Booking.Status.CANCELLED
    assert result.cancellation_outcome == Booking.Outcome.REFUNDED
    assert result.credits_refunded == 2
    assert balance_of(member) == 5


def test_cancel_exactly_at_cutoff_still_refunds(member, grant, make_class, book):
    grant(member, 5)
    starts_at = NOW + timedelta(days=1)
    booking = book(member, make_class(starts_at=starts_at, credit_cost=2))

    result = cancel(member, booking, starts_at - timedelta(hours=4))

    assert result.cancellation_outcome == Booking.Outcome.REFUNDED


def test_cancel_after_cutoff_forfeits(member, grant, make_class, book):
    grant(member, 5)
    starts_at = NOW + timedelta(days=1)
    booking = book(member, make_class(starts_at=starts_at, credit_cost=2))

    result = cancel(member, booking, starts_at - timedelta(hours=4) + timedelta(seconds=1))

    assert result.cancellation_outcome == Booking.Outcome.FORFEITED
    assert result.credits_refunded == 0
    assert balance_of(member) == 3


def test_cutoff_uses_studio_wall_clock_across_dst(member, grant, make_class, book):
    # New York falls back at 06:00 UTC on 2026-11-01; the class starts 05:00 EST (10:00 UTC),
    # so the studio-local cutoff is 01:00 EDT (05:00 UTC), 4.5 real hours before the start.
    grant(member, 5)
    session = make_class(starts_at=datetime(2026, 11, 1, 10, 0, tzinfo=UTC), credit_cost=2)

    on_time = book(member, session)
    result = cancel(member, on_time, datetime(2026, 11, 1, 4, 59, tzinfo=UTC))
    assert result.cancellation_outcome == Booking.Outcome.REFUNDED

    late = book(member, session)
    result = cancel(member, late, datetime(2026, 11, 1, 5, 30, tzinfo=UTC))
    assert result.cancellation_outcome == Booking.Outcome.FORFEITED


def test_second_cancel_is_rejected_and_refunds_once(member, grant, make_class, book):
    grant(member, 5)
    booking = book(member, make_class(credit_cost=2))
    cancel(member, booking, NOW)

    with raises_code("ALREADY_CANCELLED"):
        cancel(member, booking, NOW)

    assert CreditLedger.objects.filter(booking=booking, cause=CreditLedger.Cause.REFUND).count() == 1
    assert balance_of(member) == 5


def test_cannot_cancel_someone_elses_booking(member, other_member, grant, make_class, book):
    grant(member, 5)
    booking = book(member, make_class())

    with raises_code("BOOKING_NOT_FOUND"):
        cancel(other_member, booking, NOW)

    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


def test_cancel_releases_the_spot(member, other_member, grant, make_class, book):
    grant(member, 5)
    grant(other_member, 5)
    session = make_class(spots=1)
    cancel(member, book(member, session), NOW)

    assert book(other_member, session).status == Booking.Status.CONFIRMED
