from datetime import timedelta

import pytest

from apps.bookings.models import Booking
from apps.bookings.services.booking_service import BookingService
from apps.bookings.services.cancel_service import CancelService
from core.tests.helpers import NOW, balance_of, raises_code

pytestmark = pytest.mark.django_db


def test_booking_confirms_and_charges(member, grant, make_class, book):
    grant(member, 5)

    booking = book(member, make_class(credit_cost=2))

    assert booking.status == Booking.Status.CONFIRMED
    assert booking.credits_charged == 2
    assert balance_of(member) == 3


def test_cannot_book_a_started_class(member, grant, make_class, book):
    grant(member, 5)

    with raises_code("CLASS_STARTED"):
        book(member, make_class(starts_at=NOW - timedelta(minutes=1)))


def test_cannot_book_the_same_class_twice(member, grant, make_class, book):
    grant(member, 5)
    session = make_class()
    book(member, session)

    with raises_code("ALREADY_BOOKED"):
        book(member, session)


def test_full_class_rejects_new_bookings(member, other_member, grant, make_class, book):
    grant(member, 5)
    grant(other_member, 5)
    session = make_class(spots=1)
    book(member, session)

    with raises_code("CLASS_FULL"):
        book(other_member, session)


def test_insufficient_credits_leaves_nothing_behind(member, grant, make_class, book):
    grant(member, 1)

    with raises_code("INSUFFICIENT_CREDITS"):
        book(member, make_class(credit_cost=2))

    assert Booking.objects.count() == 0
    assert balance_of(member) == 1


def test_can_rebook_after_cancelling(member, grant, make_class, book):
    grant(member, 5)
    session = make_class()
    first = book(member, session)
    CancelService.cancel_booking(member=member, booking_id=first.id, now=NOW)

    second = book(member, session)

    assert second.id != first.id
    assert second.status == Booking.Status.CONFIRMED


def test_retry_with_same_key_returns_original_booking(member, grant, make_class):
    grant(member, 5)
    session = make_class(credit_cost=2)

    first, created = BookingService.book_class(
        member=member, class_id=session.id, idempotency_key="k1", now=NOW
    )
    again, created_again = BookingService.book_class(
        member=member, class_id=session.id, idempotency_key="k1", now=NOW
    )

    assert created is True
    assert created_again is False
    assert again.id == first.id
    assert Booking.objects.count() == 1
    assert balance_of(member) == 3


def test_same_key_for_a_different_class_conflicts(member, grant, make_class):
    grant(member, 5)
    BookingService.book_class(member=member, class_id=make_class().id, idempotency_key="k1", now=NOW)

    with raises_code("IDEMPOTENCY_CONFLICT"):
        BookingService.book_class(member=member, class_id=make_class().id, idempotency_key="k1", now=NOW)


def test_same_key_is_scoped_per_member(member, other_member, grant, make_class):
    grant(member, 5)
    grant(other_member, 5)
    session = make_class()

    _, created_a = BookingService.book_class(member=member, class_id=session.id, idempotency_key="k1", now=NOW)
    _, created_b = BookingService.book_class(
        member=other_member, class_id=session.id, idempotency_key="k1", now=NOW
    )

    assert created_a and created_b
