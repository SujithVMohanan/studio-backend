import pytest
from rest_framework.test import APIClient

from apps.users.models import User
from core.tests.api.helpers import STRONG_PASSWORD, bearer_client, body, login

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/users/register/"
LOGIN_URL = "/api/users/login/"
REFRESH_URL = "/api/users/refresh/"
LOGOUT_URL = "/api/users/logout/"
ME_URL = "/api/users/me/"


def register(**overrides):
    payload = {
        "email": "New.Member@Test.Local",
        "full_name": "New Member",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
        **overrides,
    }
    return APIClient().post(REGISTER_URL, payload, format="json")


def test_register_creates_member_and_returns_tokens():
    response = register()

    assert response.status_code == 201
    data = body(response)
    assert data["access"]
    assert data["refresh"]
    assert data["user"]["email"] == "new.member@test.local"
    assert data["user"]["role"] == User.Role.MEMBER


def test_register_cannot_self_assign_staff_role():
    response = register(role="staff")

    assert response.status_code == 201
    assert User.objects.get(email="new.member@test.local").role == User.Role.MEMBER


def test_register_rejects_duplicate_email():
    register()
    response = register(email="new.member@test.local")

    assert response.status_code == 400
    assert response.data["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_rejects_mismatched_passwords():
    response = register(confirm_password="Different#Pass2026")

    assert response.status_code == 400
    assert "confirm_password" in response.data["errors"]


def test_register_rejects_weak_password():
    response = register(password="123", confirm_password="123")

    assert response.status_code == 400
    assert "password" in response.data["errors"]


def test_login_returns_tokens(member):
    tokens = login(member.email, "pass")

    assert tokens["access"]
    assert tokens["refresh"]
    assert tokens["user"]["email"] == member.email


@pytest.mark.parametrize(
    ("email", "password"),
    [("member1@test.local", "wrong"), ("nobody@test.local", "pass")],
)
def test_login_rejects_bad_credentials(member, email, password):
    response = APIClient().post(LOGIN_URL, {"email": email, "password": password}, format="json")

    assert response.status_code == 401
    assert response.data["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_disabled_account(member):
    member.is_active = False
    member.save(update_fields=["is_active"])

    response = APIClient().post(LOGIN_URL, {"email": member.email, "password": "pass"}, format="json")

    assert response.status_code == 401
    assert response.data["code"] == "ACCOUNT_DISABLED"


def test_me_returns_current_user(member):
    tokens = login(member.email, "pass")

    response = bearer_client(tokens["access"]).get(ME_URL)

    assert response.status_code == 200
    assert body(response)["email"] == member.email


def test_refresh_rotates_and_old_refresh_is_rejected(member):
    tokens = login(member.email, "pass")

    rotated = APIClient().post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")
    reused = APIClient().post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json")

    assert rotated.status_code == 200
    assert body(rotated)["refresh"] != tokens["refresh"]
    assert reused.status_code == 401
    assert reused.data["code"] == "INVALID_REFRESH_TOKEN"


def test_refresh_rejects_garbage_token():
    response = APIClient().post(REFRESH_URL, {"refresh": "not-a-token"}, format="json")

    assert response.status_code == 401
    assert response.data["code"] == "INVALID_REFRESH_TOKEN"


def test_logout_revokes_access_and_refresh(member):
    tokens = login(member.email, "pass")
    client = bearer_client(tokens["access"])

    response = client.post(LOGOUT_URL, {"refresh": tokens["refresh"]}, format="json")

    assert response.status_code == 200
    assert client.get(ME_URL).status_code == 401
    assert APIClient().post(REFRESH_URL, {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_logout_rejects_someone_elses_refresh(member, other_member):
    mine = login(member.email, "pass")
    theirs = login(other_member.email, "pass")

    response = bearer_client(mine["access"]).post(LOGOUT_URL, {"refresh": theirs["refresh"]}, format="json")

    assert response.status_code == 401
    assert response.data["code"] == "INVALID_REFRESH_TOKEN"
