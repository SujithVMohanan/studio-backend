from datetime import timedelta

import pytest
from django.utils import timezone

from apps.studios.models import ClassSession
from core.encryption.ids import encode_id
from core.tests.api.helpers import body, booking_uid, class_uid, results

pytestmark = pytest.mark.django_db

BOOK_URL = "/api/bookings/create-booking/"
GET_BOOKINGS_URL = "/api/bookings/get-bookings/"
JOIN_URL = "/api/bookings/join-waitlist/"
LEAVE_URL = "/api/bookings/leave-waitlist/"
GET_WAITLIST_URL = "/api/bookings/get-waitlist/"


def cancel_url(uid: str) -> str:
    return f"/api/bookings/cancel-booking/{uid}/"


def post_booking(client, uid: str, key: str = "key-1"):
    return client.post(BOOK_URL, {"class_uid": uid}, format="json", HTTP_IDEMPOTENCY_KEY=key)


@pytest.fixture
def now():
    return timezone.now()


@pytest.fixture
def live_class(make_class, now):
    return make_class(starts_at=now + timedelta(days=1), credit_cost=1)


@pytest.fixture
def full_class(make_member, grant, make_class, book, now):
    holder = make_member()
    grant(holder, 5, now=now)
    session = make_class(starts_at=now + timedelta(days=1), spots=1)
    book(holder, session, now=now)
    return session


# Booking


def test_booking_over_http_charges_credits(client_for, member, grant, live_class, now):
    grant(member, 5, now=now)

    response = post_booking(client_for(member), class_uid(live_class))

    assert response.status_code == 201
    data = body(response)
    assert data["status"] == "confirmed"
    assert data["credits_charged"] == 1
    assert data["class_session"]["uid"] == class_uid(live_class)


def test_booking_a_full_class_conflicts(client_for, member, grant, full_class, now):
    grant(member, 5, now=now)

    response = post_booking(client_for(member), class_uid(full_class))

    assert response.status_code == 409
    assert response.data["code"] == "CLASS_FULL"


def test_booking_without_credits_conflicts(client_for, member, live_class):
    response = post_booking(client_for(member), class_uid(live_class))

    assert response.status_code == 409
    assert response.data["code"] == "INSUFFICIENT_CREDITS"


def test_booking_unknown_class_is_not_found(client_for, member):
    missing = encode_id(999_999, ClassSession._meta.label_lower)

    response = post_booking(client_for(member), missing)

    assert response.status_code == 404
    assert response.data["code"] == "CLASS_NOT_FOUND"


def test_booking_rejects_malformed_class_uid(client_for, member):
    assert post_booking(client_for(member), "bad").status_code == 400


def test_booking_rejects_oversized_idempotency_key(client_for, member, live_class):
    response = post_booking(client_for(member), class_uid(live_class), key="k" * 256)

    assert response.status_code == 400
    assert response.data["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_list_bookings_filters_by_status(client_for, member, grant, make_class, book, now):
    grant(member, 5, now=now)
    kept = book(member, make_class(starts_at=now + timedelta(days=1)), now=now)
    dropped = book(member, make_class(starts_at=now + timedelta(days=2)), now=now)
    client = client_for(member)
    client.post(cancel_url(booking_uid(dropped)))

    confirmed = client.get(GET_BOOKINGS_URL, {"status": "confirmed"})
    cancelled = client.get(GET_BOOKINGS_URL, {"status": "cancelled"})

    assert [row["uid"] for row in results(confirmed)] == [booking_uid(kept)]
    assert [row["uid"] for row in results(cancelled)] == [booking_uid(dropped)]


def test_list_bookings_rejects_unknown_status(client_for, member):
    assert client_for(member).get(GET_BOOKINGS_URL, {"status": "maybe"}).status_code == 400


# Cancellation


def test_cancel_over_http_refunds_once(client_for, member, grant, live_class, book, now):
    grant(member, 5, now=now)
    booking = book(member, live_class, now=now)
    client = client_for(member)

    first = client.post(cancel_url(booking_uid(booking)))
    second = client.post(cancel_url(booking_uid(booking)))

    assert first.status_code == 200
    data = body(first)
    assert data["status"] == "cancelled"
    assert data["cancellation_outcome"] == "refunded"
    assert data["credits_refunded"] == 1
    assert second.status_code == 409
    assert second.data["code"] == "ALREADY_CANCELLED"
    assert body(client.get("/api/credits/get-balance/"))["balance"] == 5


def test_cancel_inside_cutoff_forfeits(client_for, member, grant, make_class, book, now):
    grant(member, 5, now=now)
    booking = book(member, make_class(starts_at=now + timedelta(hours=2), credit_cost=2), now=now)

    response = client_for(member).post(cancel_url(booking_uid(booking)))

    assert body(response)["cancellation_outcome"] == "forfeited"
    assert body(client_for(member).get("/api/credits/get-balance/"))["balance"] == 3


# Waitlist


def test_join_list_and_leave_waitlist(client_for, member, full_class):
    client = client_for(member)
    payload = {"class_uid": class_uid(full_class)}

    joined = client.post(JOIN_URL, payload, format="json")
    waiting = client.get(GET_WAITLIST_URL, {"status": "waiting"})
    left = client.post(LEAVE_URL, payload, format="json")
    again = client.post(LEAVE_URL, payload, format="json")

    assert joined.status_code == 201
    assert body(joined)["status"] == "waiting"
    assert [row["uid"] for row in results(waiting)] == [body(joined)["uid"]]
    assert left.status_code == 200
    assert body(left)["status"] == "left"
    assert again.status_code == 404
    assert again.data["code"] == "NOT_WAITLISTED"
    assert results(client.get(GET_WAITLIST_URL, {"status": "waiting"})) == []


def test_join_waitlist_with_open_spots_conflicts(client_for, member, live_class):
    response = client_for(member).post(JOIN_URL, {"class_uid": class_uid(live_class)}, format="json")

    assert response.status_code == 409
    assert response.data["code"] == "SPOTS_AVAILABLE"


def test_join_waitlist_twice_conflicts(client_for, member, full_class):
    client = client_for(member)
    payload = {"class_uid": class_uid(full_class)}
    client.post(JOIN_URL, payload, format="json")

    response = client.post(JOIN_URL, payload, format="json")

    assert response.status_code == 409
    assert response.data["code"] == "ALREADY_WAITLISTED"
