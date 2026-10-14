from datetime import UTC, date

from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.schemas import BOOKING_ID_NAMESPACE
from apps.studios.serializer import CLASS_ID_NAMESPACE, STUDIO_ID_NAMESPACE
from apps.users.serializer import USER_ID_NAMESPACE
from core.encryption.ids import encode_id

STRONG_PASSWORD = "Str0ng#Pass2026"


def body(response) -> dict:
    return response.data["data"]


def results(response) -> list[dict]:
    return response.data["data"]["results"]


def utc_today() -> date:
    return timezone.now().astimezone(UTC).date()


def user_uid(user) -> str:
    return encode_id(user.id, USER_ID_NAMESPACE)


def studio_uid(studio) -> str:
    return encode_id(studio.id, STUDIO_ID_NAMESPACE)


def class_uid(session) -> str:
    return encode_id(session.id, CLASS_ID_NAMESPACE)


def booking_uid(booking) -> str:
    return encode_id(booking.id, BOOKING_ID_NAMESPACE)


def login(email: str, password: str) -> dict:
    response = APIClient().post(
        "/api/users/login/", {"email": email, "password": password}, format="json"
    )
    assert response.status_code == 200, response.data
    return body(response)


def bearer_client(access: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client
