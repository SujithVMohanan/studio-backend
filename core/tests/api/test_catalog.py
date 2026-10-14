from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.bookings.services.cancel_service import CancelService
from apps.studios.models import Studio
from core.encryption.ids import encode_id
from core.tests.api.helpers import body, class_uid, results, studio_uid

pytestmark = pytest.mark.django_db

CREATE_STUDIO_URL = "/api/studios/create-studio/"
GET_STUDIOS_URL = "/api/studios/get-studios/"
CREATE_CLASS_URL = "/api/classes/create-class/"
GET_CLASSES_URL = "/api/classes/get-classes/"


def update_url(uid: str) -> str:
    return f"/api/studios/update-studio/{uid}/"


def future(**delta) -> datetime:
    return (timezone.now() + timedelta(**delta)).replace(microsecond=0)


def class_payload(studio, **overrides):
    return {
        "studio_uid": studio_uid(studio),
        "starts_at": future(days=2).isoformat(),
        "duration_minutes": 45,
        "spots": 8,
        "credit_cost": 2,
        **overrides,
    }


# Studios


def test_staff_creates_studio_with_default_cutoff(client_for, staff):
    response = client_for(staff).post(
        CREATE_STUDIO_URL, {"name": "Harbour Pilates", "timezone": "Europe/London"}, format="json"
    )

    assert response.status_code == 201
    data = body(response)
    assert data["name"] == "Harbour Pilates"
    assert data["timezone"] == "Europe/London"
    assert data["cancellation_cutoff_hours"] == 4
    assert Studio.objects.filter(name="Harbour Pilates").exists()


def test_create_studio_rejects_unknown_timezone(client_for, staff):
    response = client_for(staff).post(
        CREATE_STUDIO_URL, {"name": "Nowhere Gym", "timezone": "Mars/Olympus"}, format="json"
    )

    assert response.status_code == 400
    assert "timezone" in response.data["errors"]


def test_create_studio_rejects_duplicate_name(client_for, staff, studio):
    response = client_for(staff).post(
        CREATE_STUDIO_URL, {"name": studio.name, "timezone": "UTC"}, format="json"
    )

    assert response.status_code == 409
    assert response.data["code"] == "STUDIO_NAME_TAKEN"


def test_staff_updates_studio_cutoff(client_for, staff, studio):
    response = client_for(staff).patch(
        update_url(studio_uid(studio)), {"cancellation_cutoff_hours": 6}, format="json"
    )

    assert response.status_code == 200
    studio.refresh_from_db()
    assert studio.cancellation_cutoff_hours == 6
    assert studio.timezone == "America/New_York"


def test_update_unknown_studio_is_not_found(client_for, staff):
    missing = encode_id(999_999, Studio._meta.label_lower)

    response = client_for(staff).patch(update_url(missing), {"cancellation_cutoff_hours": 6}, format="json")

    assert response.status_code == 404
    assert response.data["code"] == "STUDIO_NOT_FOUND"


def test_update_with_tampered_uid_is_not_found(client_for, staff):
    response = client_for(staff).patch(update_url("A" * 22), {"cancellation_cutoff_hours": 6}, format="json")

    assert response.status_code == 404


def test_anyone_signed_in_can_list_and_filter_studios(client_for, member, studio, staff):
    Studio.objects.create(name="Other Place", timezone="UTC", created_by=staff)

    response = client_for(member).get(GET_STUDIOS_URL, {"name": "test"})

    assert response.status_code == 200
    assert [row["uid"] for row in results(response)] == [studio_uid(studio)]


# Classes


def test_staff_schedules_class(client_for, staff, studio):
    starts_at = future(days=2)

    response = client_for(staff).post(
        CREATE_CLASS_URL, class_payload(studio, starts_at=starts_at.isoformat()), format="json"
    )

    assert response.status_code == 201
    data = body(response)
    assert data["spots"] == 8
    assert data["spots_remaining"] == 8
    assert data["credit_cost"] == 2
    assert data["studio"]["uid"] == studio_uid(studio)
    assert data["starts_at_local"] == starts_at.astimezone(ZoneInfo("America/New_York")).isoformat()


@pytest.mark.parametrize(
    "override",
    [
        {"starts_at": (timezone.now() - timedelta(hours=1)).isoformat()},
        {"starts_at": "2030-01-01T10:00:00"},
        {"spots": 0},
        {"duration_minutes": 0},
        {"credit_cost": -1},
        {"spots": True},
    ],
    ids=["past", "naive", "zero-spots", "zero-duration", "negative-cost", "boolean-spots"],
)
def test_schedule_class_rejects_invalid_input(client_for, staff, studio, override):
    response = client_for(staff).post(CREATE_CLASS_URL, class_payload(studio, **override), format="json")

    assert response.status_code == 400


def test_schedule_class_for_unknown_studio_is_not_found(client_for, staff, studio):
    payload = class_payload(studio, studio_uid=encode_id(999_999, Studio._meta.label_lower))

    response = client_for(staff).post(CREATE_CLASS_URL, payload, format="json")

    assert response.status_code == 404
    assert response.data["code"] == "STUDIO_NOT_FOUND"


def test_browse_requires_a_date_range(client_for, member):
    assert client_for(member).get(GET_CLASSES_URL).status_code == 400


def test_browse_rejects_end_before_start(client_for, member):
    response = client_for(member).get(
        GET_CLASSES_URL,
        {"start": future(days=2).isoformat(), "end": future(days=1).isoformat()},
    )

    assert response.status_code == 400


def test_browse_returns_classes_in_range_with_spots_remaining(
    client_for, member, other_member, make_member, grant, make_class, book
):
    now = timezone.now()
    inside = make_class(starts_at=now + timedelta(days=1), spots=3)
    make_class(starts_at=now + timedelta(days=10), spots=3)

    for m in (member, other_member):
        grant(m, 5, now=now)
        book(m, inside, now=now)
    cancelled_by = make_member()
    grant(cancelled_by, 5, now=now)
    CancelService.cancel_booking(member=cancelled_by, booking_id=book(cancelled_by, inside, now=now).id, now=now)

    response = client_for(member).get(
        GET_CLASSES_URL,
        {"start": now.isoformat(), "end": (now + timedelta(days=2)).isoformat()},
    )

    assert response.status_code == 200
    rows = results(response)
    assert [row["uid"] for row in rows] == [class_uid(inside)]
    assert rows[0]["spots_remaining"] == 1


def test_browse_single_class_by_uid(client_for, member, make_class):
    session = make_class(starts_at=timezone.now() + timedelta(days=1))

    response = client_for(member).get(GET_CLASSES_URL, {"uid": class_uid(session)})

    assert [row["uid"] for row in results(response)] == [class_uid(session)]
