

from datetime import date, datetime

from apps.credits.models import CreditPack, CreditLedger
from apps.credits.repository import CreditLedgerRepository, CreditPackRepository
from core.exceptions.business import BusinessConflict
from core.utils import clock



def spendable_balance(
    *,
    member_id: int,
    today: date,
    lock: bool = False,
) -> int:
    if lock:
        packs = CreditPackRepository.lock_spendable_for_member(member_id, today)
    else:
        packs = [
            pack
            for pack in CreditPackRepository.list_for_member(member_id)
            if pack.is_active_on(today)
        ]

    pack_ids = [pack.id for pack in packs]
    remaining = CreditLedgerRepository.remaining_by_pack(pack_ids)

    return sum(max(balance or 0, 0) for balance in remaining.values())


def plan_allocation(
    *,
    member_id: int,
    amount: int,
    today: date,
) -> list[tuple[CreditPack, int]]:
    
    if amount < 0:
        raise ValueError("Credit amount cannot be negative.")

    if amount == 0:
        return []

    packs = CreditPackRepository.lock_spendable_for_member(member_id, today)
    remaining = CreditLedgerRepository.remaining_by_pack(
        [pack.id for pack in packs]
    )

    plan: list[tuple[CreditPack, int]] = []
    needed = amount

    for pack in sorted(packs, key=lambda item: (item.expires_on, item.id)):
        available = max(remaining.get(pack.id, 0) or 0, 0)

        if available == 0:
            continue

        allocated = min(available, needed)
        plan.append((pack, allocated))
        needed -= allocated

        if needed == 0:
            return plan

    raise BusinessConflict(
        "Not enough credits to book this class.",
        code="INSUFFICIENT_CREDITS",
    )







def spend_for_booking(*, booking, now: datetime) -> int:

    plan = plan_allocation(
        member_id=booking.member_id,
        amount=booking.credits_charged,
        today=clock.utc_today(now),
    )
    return record_spend(booking=booking, plan=plan, now=now)


def record_spend(
    *,
    booking,
    plan: list[tuple[CreditPack, int]],
    now: datetime,
) -> int:
    CreditLedgerRepository.bulk_create(
        [
            CreditLedger(
                member_id=booking.member_id,
                pack=pack,
                booking=booking,
                amount=-taken,
                cause=CreditLedger.Cause.SPEND,
                created_at=now,
            )
            for pack, taken in plan
        ]
    )
    return sum(taken for _, taken in plan)




def refund_booking(*, booking, now: datetime) -> int:

    spends = CreditLedgerRepository.spend_rows_for_booking(booking.id)

    CreditLedgerRepository.bulk_create(
        [
            CreditLedger(
                member_id=row.member_id,
                pack_id=row.pack_id,
                booking=booking,
                amount=-row.amount,
                cause=CreditLedger.Cause.REFUND,
                created_at=now,
            )
            for row in spends
        ]
    )
    return sum(-row.amount for row in spends)