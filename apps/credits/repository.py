
from datetime import date, datetime
from typing import Any

from django.db.models import Q, QuerySet, Sum

from apps.credits.models import CreditLedger, CreditPack


class CreditPackRepository:
    @staticmethod
    def create(**fields: Any) -> CreditPack:
        return CreditPack.objects.create(**fields)

    @staticmethod
    def list_for_member(member_id: int) -> list[CreditPack]:
        filters = Q(member_id=member_id)

        return list(
            CreditPack.objects.filter(filters).order_by("expires_on", "id")
        )

    @staticmethod
    def lock_spendable_for_member(
        member_id: int,
        today: date,
    ) -> list[CreditPack]:
        filters = (
            Q(member_id=member_id)
            & Q(granted_on__lte=today)
            & Q(expires_on__gte=today)
        )

        return list(
            CreditPack.objects.select_for_update()
            .filter(filters)
            .order_by("id")
        )


class CreditLedgerRepository:
    @staticmethod
    def create(**fields: Any) -> CreditLedger:
        return CreditLedger.objects.create(**fields)

    @staticmethod
    def remaining_by_pack(
        pack_ids: list[int],
        *,
        until: datetime | None = None,
    ) -> dict[int, int]:
        if not pack_ids:
            return {}

        filters = Q(pack_id__in=pack_ids)

        if until is not None:
            filters &= Q(created_at__lte=until)

        rows = (
            CreditLedger.objects.filter(filters)
            .values("pack_id")
            .annotate(total=Sum("amount"))
            .order_by()
        )

        return {
            row["pack_id"]: row["total"]
            for row in rows
        }

    @staticmethod
    def list_for_member(
        member_id: int,
        *,
        cause: str | None = None,
    ) -> QuerySet[CreditLedger]:
        filters = Q(member_id=member_id)

        if cause:
            filters &= Q(cause=cause)

        return CreditLedger.objects.filter(filters).order_by("created_at", "id")
