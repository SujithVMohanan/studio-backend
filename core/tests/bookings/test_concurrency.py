import threading
from datetime import timedelta
from uuid import uuid4

import pytest
from django.db import connections

from apps.bookings.models import Booking
from apps.bookings.services.booking_service import BookingService
from core.tests.helpers import NOW

pytestmark = pytest.mark.django_db(transaction=True)


def run_concurrently(calls):
    barrier = threading.Barrier(len(calls))
    results: list[str] = []
    lock = threading.Lock()

    def worker(call):
        try:
            barrier.wait()
            _, created = call()
            outcome = "created" if created else "replayed"
        except Exception as exc:
            outcome = getattr(exc, "error_code", None) or repr(exc)
        finally:
            connections.close_all()
        with lock:
            results.append(outcome)

    threads = [threading.Thread(target=worker, args=(call,)) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def booking_call(member, session, key=None):
    return lambda: BookingService.book_class(
        member=member, class_id=session.id, idempotency_key=key or uuid4().hex, now=NOW
    )


def test_class_never_oversells(make_member, grant, make_class):
    session = make_class(spots=3)
    members = [make_member() for _ in range(10)]
    for m in members:
        grant(m, 5)

    results = run_concurrently([booking_call(m, session) for m in members])

    assert sorted(results) == ["CLASS_FULL"] * 7 + ["created"] * 3
    assert Booking.objects.filter(class_session=session, status=Booking.Status.CONFIRMED).count() == 3


def test_same_key_retries_create_one_booking(member, grant, make_class):
    grant(member, 5)
    session = make_class()

    results = run_concurrently([booking_call(member, session, key="retry-1") for _ in range(5)])

    assert sorted(results) == ["created"] + ["replayed"] * 4
    assert Booking.objects.filter(member=member).count() == 1


def test_credits_cannot_be_double_spent(member, grant, make_class):
    grant(member, 2)
    sessions = [make_class(credit_cost=2, starts_at=NOW + timedelta(days=d)) for d in (1, 2, 3)]

    results = run_concurrently([booking_call(member, s) for s in sessions])

    assert sorted(results) == ["INSUFFICIENT_CREDITS"] * 2 + ["created"]
