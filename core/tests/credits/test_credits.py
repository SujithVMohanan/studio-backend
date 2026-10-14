from datetime import timedelta

import pytest

from apps.bookings.services.cancel_service import CancelService
from apps.credits.models import CreditLedger
from apps.credits.services.credit_service import CreditService
from core.tests.helpers import NOW, TODAY, balance_of, raises_code

pytestmark = pytest.mark.django_db


def spend_rows(booking):
    return list(
        CreditLedger.objects.filter(booking=booking, cause=CreditLedger.Cause.SPEND)
        .order_by("id")
        .values_list("pack_id", "amount")
    )


def test_grant_records_a_grant_movement(member, grant):
    pack = grant(member, 10)

    rows = list(CreditLedger.objects.filter(member=member).values_list("pack_id", "amount", "cause"))
    assert rows == [(pack.id, 10, "grant")]
    assert balance_of(member) == 10


def test_balance_lists_each_pack_with_expiry(member, grant):
    soon = grant(member, 3, expires_on=TODAY + timedelta(days=7))
    later = grant(member, 5, expires_on=TODAY + timedelta(days=30))

    view = CreditService.get_balance(member=member, now=NOW)

    assert view.balance == 8
    assert [(p.pack.id, p.remaining, p.pack.expires_on) for p in view.packs] == [
        (soon.id, 3, soon.expires_on),
        (later.id, 5, later.expires_on),
    ]


def test_expired_and_future_packs_do_not_count(member, grant):
    grant(member, 5, granted_on=TODAY - timedelta(days=40), expires_on=TODAY - timedelta(days=1))
    grant(member, 4, granted_on=TODAY + timedelta(days=1), expires_on=TODAY + timedelta(days=30))

    assert balance_of(member) == 0


def test_expired_credits_cannot_be_spent(member, grant, make_class, book):
    grant(member, 5, granted_on=TODAY - timedelta(days=40), expires_on=TODAY - timedelta(days=1))

    with raises_code("INSUFFICIENT_CREDITS"):
        book(member, make_class(credit_cost=1))


def test_soonest_expiring_pack_is_spent_first(member, grant, make_class, book):
    grant(member, 5, expires_on=TODAY + timedelta(days=30))
    soon = grant(member, 5, expires_on=TODAY + timedelta(days=7))

    booking = book(member, make_class(credit_cost=3))

    assert spend_rows(booking) == [(soon.id, -3)]


def test_spend_spills_into_next_pack(member, grant, make_class, book):
    later = grant(member, 5, expires_on=TODAY + timedelta(days=30))
    soon = grant(member, 5, expires_on=TODAY + timedelta(days=7))

    booking = book(member, make_class(credit_cost=7))

    assert sorted(spend_rows(booking)) == sorted([(soon.id, -5), (later.id, -2)])
    assert balance_of(member) == 3


def test_balance_at_a_past_moment(member, grant, make_class, book):
    grant(member, 10)
    book(member, make_class(credit_cost=3), now=NOW + timedelta(hours=1))

    def at(delta):
        return CreditService.get_balance_at(member=member, at=NOW + delta).balance

    assert at(-timedelta(minutes=1)) == 0
    assert at(timedelta(minutes=30)) == 10
    assert at(timedelta(hours=2)) == 7


def test_ledger_accounts_for_every_credit(member, grant, make_class, book):
    grant(member, 10)
    book(member, make_class(credit_cost=3))
    refunded = book(member, make_class(credit_cost=2))
    CancelService.cancel_booking(member=member, booking_id=refunded.id, now=NOW)

    rows = list(CreditLedger.objects.filter(member=member).order_by("created_at", "id"))

    assert [r.cause for r in rows] == ["grant", "spend", "spend", "refund"]
    assert sum(r.amount for r in rows) == balance_of(member) == 7


def test_ledger_rows_are_append_only(member, grant):
    grant(member, 5)
    row = CreditLedger.objects.get(member=member)

    row.amount = 99
    with pytest.raises(RuntimeError):
        row.save()
    with pytest.raises(RuntimeError):
        row.delete()
