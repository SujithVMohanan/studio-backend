from datetime import timedelta

import pytest
from django.utils import timezone

from apps.credits.models import CreditLedger
from core.tests.api.helpers import body, results, user_uid, utc_today

pytestmark = pytest.mark.django_db

GRANT_URL = "/api/credits/grant-credit-pack/"
BALANCE_URL = "/api/credits/get-balance/"
BALANCE_AT_URL = "/api/credits/get-balance-at/"
LEDGER_URL = "/api/credits/get-ledger/"


def grant_payload(member, **overrides):
    today = utc_today()
    return {
        "member_uid": user_uid(member),
        "credits": 10,
        "granted_on": today.isoformat(),
        "expires_on": (today + timedelta(days=30)).isoformat(),
        **overrides,
    }


def test_staff_grants_pack(client_for, staff, member):
    response = client_for(staff).post(GRANT_URL, grant_payload(member), format="json")

    assert response.status_code == 201
    data = body(response)
    assert data["member_uid"] == user_uid(member)
    assert data["credits"] == 10
    assert CreditLedger.objects.filter(member=member, cause="grant", amount=10).count() == 1


@pytest.mark.parametrize(
    "override",
    [
        {"credits": 0},
        {"credits": "ten"},
        {"expires_on": "2000-01-01"},
        {"member_uid": "not-a-valid-uid"},
    ],
    ids=["zero-credits", "non-integer", "expires-before-grant", "bad-uid"],
)
def test_grant_rejects_invalid_input(client_for, staff, member, override):
    response = client_for(staff).post(GRANT_URL, grant_payload(member, **override), format="json")

    assert response.status_code == 400


def test_grant_to_staff_account_is_rejected(client_for, staff):
    response = client_for(staff).post(GRANT_URL, grant_payload(staff), format="json")

    assert response.status_code == 404
    assert response.data["code"] == "MEMBER_NOT_FOUND"


def test_grant_to_inactive_member_is_rejected(client_for, staff, member):
    member.is_active = False
    member.save(update_fields=["is_active"])

    response = client_for(staff).post(GRANT_URL, grant_payload(member), format="json")

    assert response.status_code == 404
    assert response.data["code"] == "MEMBER_NOT_FOUND"


def test_balance_shows_packs_with_expiry(client_for, member, grant):
    now = timezone.now()
    today = utc_today()
    grant(member, 3, expires_on=today + timedelta(days=7), now=now)
    grant(member, 5, expires_on=today + timedelta(days=30), now=now)

    response = client_for(member).get(BALANCE_URL)

    assert response.status_code == 200
    data = body(response)
    assert data["balance"] == 8
    assert [(p["remaining"], p["expires_on"]) for p in data["packs"]] == [
        (3, (today + timedelta(days=7)).isoformat()),
        (5, (today + timedelta(days=30)).isoformat()),
    ]


def test_balance_at_reconstructs_the_past(client_for, member, grant):
    granted_at = timezone.now() - timedelta(hours=1)
    grant(member, 10, now=granted_at)
    client = client_for(member)

    before = client.get(BALANCE_AT_URL, {"at": (granted_at - timedelta(minutes=5)).isoformat()})
    after = client.get(BALANCE_AT_URL, {"at": (granted_at + timedelta(minutes=5)).isoformat()})

    assert (before.status_code, after.status_code) == (200, 200)
    assert body(before)["balance"] == 0
    assert body(after)["balance"] == 10


@pytest.mark.parametrize("params", [{}, {"at": "2026-01-01T10:00:00"}, {"at": "yesterday"}])
def test_balance_at_requires_an_aware_timestamp(client_for, member, params):
    assert client_for(member).get(BALANCE_AT_URL, params).status_code == 400


def test_ledger_lists_movements_and_filters_by_cause(client_for, member, grant, make_class, book):
    now = timezone.now()
    grant(member, 5, now=now)
    book(member, make_class(starts_at=now + timedelta(days=1), credit_cost=2), now=now)
    client = client_for(member)

    everything = client.get(LEDGER_URL)
    spends = client.get(LEDGER_URL, {"cause": "spend"})

    assert [(row["cause"], row["amount"]) for row in results(everything)] == [("grant", 5), ("spend", -2)]
    assert [(row["cause"], row["amount"]) for row in results(spends)] == [("spend", -2)]
    assert results(spends)[0]["booking_uid"]


def test_ledger_rejects_unknown_cause(client_for, member):
    assert client_for(member).get(LEDGER_URL, {"cause": "gift"}).status_code == 400
