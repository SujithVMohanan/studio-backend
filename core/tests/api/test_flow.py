from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.tests.api.helpers import STRONG_PASSWORD, bearer_client, body, login, results, utc_today

pytestmark = pytest.mark.django_db


def register(email: str) -> dict:
    response = APIClient().post(
        "/api/users/register/",
        {"email": email, "full_name": email, "password": STRONG_PASSWORD, "confirm_password": STRONG_PASSWORD},
        format="json",
    )
    assert response.status_code == 201, response.data
    return body(response)


def test_end_to_end_book_fill_waitlist_cancel_promote(staff):
    staff_api = bearer_client(login(staff.email, "pass")["access"])

    studio = body(staff_api.post(
        "/api/studios/create-studio/",
        {"name": "Flow Studio", "timezone": "Asia/Kolkata", "cancellation_cutoff_hours": 4},
        format="json",
    ))
    starts_at = (timezone.now() + timedelta(days=2)).replace(microsecond=0)
    session = body(staff_api.post(
        "/api/classes/create-class/",
        {
            "studio_uid": studio["uid"],
            "starts_at": starts_at.isoformat(),
            "duration_minutes": 60,
            "spots": 1,
            "credit_cost": 2,
        },
        format="json",
    ))

    alice = register("alice@test.local")
    bob = register("bob@test.local")
    alice_api = bearer_client(alice["access"])
    bob_api = bearer_client(bob["access"])

    today = utc_today()
    for person in (alice, bob):
        granted = staff_api.post(
            "/api/credits/grant-credit-pack/",
            {
                "member_uid": person["user"]["uid"],
                "credits": 5,
                "granted_on": today.isoformat(),
                "expires_on": (today + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        assert granted.status_code == 201

    booked = alice_api.post(
        "/api/bookings/create-booking/", {"class_uid": session["uid"]}, format="json", HTTP_IDEMPOTENCY_KEY="a-1"
    )
    assert booked.status_code == 201

    full = bob_api.post(
        "/api/bookings/create-booking/", {"class_uid": session["uid"]}, format="json", HTTP_IDEMPOTENCY_KEY="b-1"
    )
    assert full.status_code == 409
    assert full.data["code"] == "CLASS_FULL"

    joined = bob_api.post("/api/bookings/join-waitlist/", {"class_uid": session["uid"]}, format="json")
    assert joined.status_code == 201

    cancelled = alice_api.post(f"/api/bookings/cancel-booking/{body(booked)['uid']}/")
    assert cancelled.status_code == 200
    assert body(cancelled)["cancellation_outcome"] == "refunded"

    bob_entries = results(bob_api.get("/api/bookings/get-waitlist/"))
    assert [entry["status"] for entry in bob_entries] == ["promoted"]

    bob_bookings = results(bob_api.get("/api/bookings/get-bookings/", {"status": "confirmed"}))
    assert [(b["source"], b["class_session"]["uid"]) for b in bob_bookings] == [("waitlist", session["uid"])]
    assert bob_entries[0]["booking_uid"] == bob_bookings[0]["uid"]

    assert body(alice_api.get("/api/credits/get-balance/"))["balance"] == 5
    assert body(bob_api.get("/api/credits/get-balance/"))["balance"] == 3
    assert [(r["cause"], r["amount"]) for r in results(bob_api.get("/api/credits/get-ledger/"))] == [
        ("grant", 5),
        ("spend", -2),
    ]

    browse = staff_api.get(
        "/api/classes/get-classes/",
        {"start": timezone.now().isoformat(), "end": (starts_at + timedelta(hours=1)).isoformat()},
    )
    assert [(c["uid"], c["spots_remaining"]) for c in results(browse)] == [(session["uid"], 0)]
