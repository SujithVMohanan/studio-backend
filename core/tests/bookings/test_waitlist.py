from datetime import timedelta

import pytest

from apps.bookings.models import Booking, WaitlistEntry
from apps.bookings.services.cancel_service import CancelService
from apps.bookings.services.waitlist_service import WaitlistService
from core.tests.helpers import NOW, balance_of, raises_code

pytestmark = pytest.mark.django_db


def join(member, session, at=NOW):
    return WaitlistService.join_waitlist(member=member, class_id=session.id, now=at)


@pytest.fixture
def full_class(make_member, grant, make_class, book):
    holder = make_member()
    grant(holder, 5)
    session = make_class(spots=1, credit_cost=2)
    booking = book(holder, session)
    return session, holder, booking


def test_cannot_join_waitlist_while_spots_remain(member, make_class):
    with raises_code("SPOTS_AVAILABLE"):
        join(member, make_class(spots=5))


def test_join_and_reject_duplicates(member, full_class):
    session, holder, _ = full_class

    entry = join(member, session)
    assert entry.status == WaitlistEntry.Status.WAITING

    with raises_code("ALREADY_WAITLISTED"):
        join(member, session)
    with raises_code("ALREADY_BOOKED"):
        join(holder, session)


def test_leave_waitlist(member, full_class):
    session, _, _ = full_class
    join(member, session)

    left = WaitlistService.leave_waitlist(member=member, class_id=session.id, now=NOW)
    assert left.status == WaitlistEntry.Status.LEFT

    with raises_code("NOT_WAITLISTED"):
        WaitlistService.leave_waitlist(member=member, class_id=session.id, now=NOW)


def test_longest_waiting_member_is_promoted_and_charged(make_member, grant, full_class):
    session, holder, booking = full_class
    first, second = make_member(), make_member()
    grant(first, 5)
    grant(second, 5)
    first_entry = join(first, session, NOW)
    second_entry = join(second, session, NOW + timedelta(minutes=1))

    CancelService.cancel_booking(member=holder, booking_id=booking.id, now=NOW + timedelta(minutes=2))

    first_entry.refresh_from_db()
    second_entry.refresh_from_db()
    assert first_entry.status == WaitlistEntry.Status.PROMOTED
    assert first_entry.booking.source == Booking.Source.WAITLIST
    assert balance_of(first) == 3
    assert second_entry.status == WaitlistEntry.Status.WAITING
    assert balance_of(second) == 5


def test_member_who_cannot_afford_keeps_their_place(make_member, grant, full_class):
    session, holder, booking = full_class
    broke, funded = make_member(), make_member()
    grant(funded, 5)
    broke_entry = join(broke, session, NOW)
    funded_entry = join(funded, session, NOW + timedelta(minutes=1))

    CancelService.cancel_booking(member=holder, booking_id=booking.id, now=NOW + timedelta(minutes=2))

    broke_entry.refresh_from_db()
    funded_entry.refresh_from_db()
    assert broke_entry.status == WaitlistEntry.Status.WAITING
    assert funded_entry.status == WaitlistEntry.Status.PROMOTED


def test_no_promotion_once_class_has_started(member, make_member, grant, make_class, book):
    holder = make_member()
    grant(holder, 5)
    grant(member, 5)
    session = make_class(starts_at=NOW + timedelta(hours=1), spots=1)
    booking = book(holder, session)
    entry = join(member, session)

    CancelService.cancel_booking(member=holder, booking_id=booking.id, now=NOW + timedelta(hours=2))

    entry.refresh_from_db()
    assert entry.status == WaitlistEntry.Status.WAITING


def test_booking_directly_closes_waitlist_entry(member, grant, full_class, book):
    session, holder, booking = full_class
    entry = join(member, session)
    CancelService.cancel_booking(member=holder, booking_id=booking.id, now=NOW)

    grant(member, 5)
    book(member, session)

    entry.refresh_from_db()
    assert entry.status == WaitlistEntry.Status.LEFT
