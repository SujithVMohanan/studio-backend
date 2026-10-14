from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.studios.serializer import CLASS_ID_NAMESPACE
from core.encryption.ids import encode_id

pytestmark = pytest.mark.django_db

BOOK_URL = "/api/bookings/create-booking/"


@pytest.fixture
def live_class(make_class):
    return make_class(starts_at=timezone.now() + timedelta(days=1), credit_cost=1)


@pytest.fixture
def funded(grant):
    def _fund(member, credits=5):
        grant(member, credits, now=timezone.now())
        return member

    return _fund


def call(client, method, url):
    if method == "get":
        return client.get(url)
    return client.post(url, {}, format="json")


def post_booking(client, session, key="key-1"):
    return client.post(
        BOOK_URL,
        {"class_uid": encode_id(session.id, CLASS_ID_NAMESPACE)},
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )


def test_anonymous_request_is_rejected():
    assert APIClient().get("/api/bookings/get-bookings/").status_code == 401


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", "/api/studios/create-studio/"),
        ("post", "/api/classes/create-class/"),
        ("post", "/api/credits/grant-credit-pack/"),
        ("get", "/api/users/get-users/"),
    ],
)
def test_members_cannot_use_staff_endpoints(client_for, member, method, url):
    assert call(client_for(member), method, url).status_code == 403


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", BOOK_URL),
        ("get", "/api/bookings/get-bookings/"),
        ("post", "/api/bookings/join-waitlist/"),
        ("get", "/api/credits/get-balance/"),
        ("get", "/api/credits/get-ledger/"),
    ],
)
def test_staff_cannot_use_member_endpoints(client_for, staff, method, url):
    assert call(client_for(staff), method, url).status_code == 403


def test_booking_requires_idempotency_key(client_for, member, funded, live_class):
    funded(member)
    response = client_for(member).post(
        BOOK_URL, {"class_uid": encode_id(live_class.id, CLASS_ID_NAMESPACE)}, format="json"
    )

    assert response.status_code == 400
    assert response.data["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_retry_over_http_returns_same_booking(client_for, member, funded, live_class):
    funded(member)
    client = client_for(member)

    first = post_booking(client, live_class)
    again = post_booking(client, live_class)

    assert (first.status_code, again.status_code) == (201, 200)
    assert again.data["data"]["uid"] == first.data["data"]["uid"]
    assert Booking.objects.count() == 1


def test_members_only_see_their_own_bookings(client_for, member, other_member, funded, live_class):
    funded(member)
    post_booking(client_for(member), live_class)

    mine = client_for(member).get("/api/bookings/get-bookings/")
    theirs = client_for(other_member).get("/api/bookings/get-bookings/")

    assert mine.data["data"]["count"] == 1
    assert theirs.data["data"]["count"] == 0


def test_members_only_see_their_own_ledger(client_for, member, other_member, funded):
    funded(member)

    assert client_for(member).get("/api/credits/get-ledger/").data["data"]["count"] == 1
    assert client_for(other_member).get("/api/credits/get-ledger/").data["data"]["count"] == 0


def test_cannot_cancel_another_members_booking(client_for, member, other_member, funded, live_class):
    funded(member)
    uid = post_booking(client_for(member), live_class).data["data"]["uid"]

    response = client_for(other_member).post(f"/api/bookings/cancel-booking/{uid}/")

    assert response.status_code == 404
    assert response.data["code"] == "BOOKING_NOT_FOUND"
    assert Booking.objects.get().status == Booking.Status.CONFIRMED


def test_tampered_booking_uid_is_not_found(client_for, member):
    response = client_for(member).post(f"/api/bookings/cancel-booking/{'A' * 22}/")
    assert response.status_code == 404
