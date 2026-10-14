
from datetime import datetime
from typing import Any

from django.db.models import Q, QuerySet

from apps.bookings.models import Booking, WaitlistEntry


class BookingRepository:

    @staticmethod
    def create(**fields: Any) -> Booking:
        return Booking.objects.create(**fields)

    @staticmethod
    def get_by_member_key(
        member_id: int,
        key: str,
    ) -> Booking | None:
        filters = (
            Q(member_id=member_id)
            & Q(idempotency_key=key)
        )

        return Booking.objects.filter(filters).first()

    @staticmethod
    def member_has_confirmed(
        member_id: int,
        class_id: int,
    ) -> bool:
        filters = (
            Q(member_id=member_id)
            & Q(class_session_id=class_id)
            & Q(status=Booking.Status.CONFIRMED)
        )

        return Booking.objects.filter(filters).exists()

    @staticmethod
    def count_confirmed(class_id: int) -> int:
        filters = (
            Q(class_session_id=class_id)
            & Q(status=Booking.Status.CONFIRMED)
        )

        return Booking.objects.filter(filters).count()

    @staticmethod
    def list_for_member(
        member_id: int,
        *,
        status: str | None = None,
    ) -> QuerySet[Booking]:
        filters = Q(member_id=member_id)

        if status:
            filters &= Q(status=status)

        return (
            Booking.objects.filter(filters)
            .select_related("class_session__studio")
            .order_by("-booked_at", "-id")
        )


class WaitlistRepository:
    
    @staticmethod
    def mark_left_if_waiting(
        member_id: int,
        class_id: int,
        now: datetime,
    ) -> int:
        filters = (
            Q(member_id=member_id)
            & Q(class_session_id=class_id)
            & Q(status=WaitlistEntry.Status.WAITING)
        )

        return WaitlistEntry.objects.filter(filters).update(
            status=WaitlistEntry.Status.LEFT,
            left_at=now,
        )
