

from datetime import date

from apps.credits.models import CreditPack
from apps.credits.repository import CreditLedgerRepository, CreditPackRepository
from core.exceptions.business import BusinessConflict


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
