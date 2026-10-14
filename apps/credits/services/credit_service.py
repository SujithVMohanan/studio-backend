

from datetime import datetime
from typing import Any

from django.db import transaction
from django.db.models import QuerySet

from apps.credits.models import CreditLedger, CreditPack
from apps.credits.repository import CreditLedgerRepository, CreditPackRepository
from apps.credits.types import BalanceView, PackBalance
from apps.users.models import User
from apps.users.repository import UserRepository
from core.exceptions.business import ResourceNotFound
from core.utils import clock


class CreditService:

    @staticmethod
    def grant_pack(
        *,
        actor: User,
        validated_data: dict[str, Any],
        now: datetime | None = None,
    ) -> CreditPack:
        current_time = now if now is not None else clock.now()

        member = UserRepository.get_active_by_id(validated_data["member_uid"])
        if member is None or member.role != User.Role.MEMBER:
            raise ResourceNotFound(
                "Member not found.",
                code="MEMBER_NOT_FOUND",
            )

        with transaction.atomic():
            
            pack = CreditPackRepository.create(
                member=member,
                credits=validated_data["credits"],
                granted_on=validated_data["granted_on"],
                expires_on=validated_data["expires_on"],
                granted_by=actor,
                created_at=current_time,
            )

            CreditLedgerRepository.create(
                member=member,
                pack=pack,
                amount=pack.credits,
                cause=CreditLedger.Cause.GRANT,
                created_at=current_time,
            )

        return pack

    @staticmethod
    def get_balance(
        *,
        member: User,
        now: datetime | None = None,
    ) -> BalanceView:
        current_time = now if now is not None else clock.now()

        return CreditService._balance(
            member=member,
            at=current_time,
            until=None,
        )

    @staticmethod
    def get_balance_at(
        *,
        member: User,
        at: datetime,
    ) -> BalanceView:
        return CreditService._balance(
            member=member,
            at=at,
            until=at,
        )

    @staticmethod
    def list_ledger(
        *,
        member: User,
        validated_data: dict[str, Any],
    ) -> QuerySet[CreditLedger]:
        return CreditLedgerRepository.list_for_member(
            member.id,
            cause=validated_data.get("cause"),
        )

    @staticmethod
    def _balance(
        *,
        member: User,
        at: datetime,
        until: datetime | None,
    ) -> BalanceView:
        today = clock.utc_today(at)
        packs = CreditPackRepository.list_for_member(member.id)

        remaining_by_pack = CreditLedgerRepository.remaining_by_pack(
            [pack.id for pack in packs],
            until=until,
        )

        items = [
            PackBalance(
                pack=pack,
                remaining=remaining_by_pack[pack.id],
                is_active=pack.is_active_on(today),
                is_expired=pack.expires_on < today,
            )
            for pack in packs
            if pack.id in remaining_by_pack
        ]

        balance = sum(
            item.remaining
            for item in items
            if item.is_active
        )

        return BalanceView(
            at=at,
            balance=balance,
            packs=items,
        )
