import pytest
from rest_framework.test import APIClient

from apps.users.models import User
from core.tests.api.helpers import body, results, user_uid

pytestmark = pytest.mark.django_db

GET_USERS_URL = "/api/users/get-users/"
DELETE_USERS_URL = "/api/users/delete-users/"


def delete_users(client, *users):
    return client.delete(DELETE_USERS_URL, {"uids": [user_uid(u) for u in users]}, format="json")


def test_staff_lists_users_with_role_filter(client_for, staff, member, other_member):
    response = client_for(staff).get(GET_USERS_URL, {"role": "member"})

    assert response.status_code == 200
    assert {row["email"] for row in results(response)} == {member.email, other_member.email}


def test_staff_filters_users_by_email(client_for, staff, member, other_member):
    response = client_for(staff).get(GET_USERS_URL, {"email": member.email})

    assert [row["uid"] for row in results(response)] == [user_uid(member)]


def test_get_users_excludes_current_user_and_superusers(client_for, staff, member):
    root = User.objects.create_superuser(email="root@test.local", password="pass")

    emails = {row["email"] for row in results(client_for(staff).get(GET_USERS_URL))}

    assert member.email in emails
    assert staff.email not in emails
    assert root.email not in emails


def test_staff_deletes_member_and_member_can_no_longer_log_in(client_for, staff, member):
    response = delete_users(client_for(staff), member)

    assert response.status_code == 200
    assert body(response) == {"deleted": 1}
    member.refresh_from_db()
    assert member.is_active is False

    login = APIClient().post("/api/users/login/", {"email": member.email, "password": "pass"}, format="json")
    assert login.status_code == 401


def test_staff_cannot_delete_themselves(client_for, staff):
    response = delete_users(client_for(staff), staff)

    assert response.status_code == 400
    staff.refresh_from_db()
    assert staff.is_active is True


def test_superuser_cannot_be_deleted(client_for, staff):
    root = User.objects.create_superuser(email="root@test.local", password="pass")

    response = delete_users(client_for(staff), root)

    assert response.status_code == 400
    root.refresh_from_db()
    assert root.is_active is True


def test_deleting_already_inactive_user_is_not_found(client_for, staff, member):
    member.is_active = False
    member.save(update_fields=["is_active"])

    assert delete_users(client_for(staff), member).status_code == 404


def test_superuser_passes_staff_checks(client_for, member):
    root = User.objects.create_superuser(email="root@test.local", password="pass")

    assert client_for(root).get(GET_USERS_URL).status_code == 200
