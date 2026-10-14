
from datetime import datetime
from typing import Any

from django.db.models import Count, Q, QuerySet

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
    def confirmed_summary(
        class_id: int,
        member_id: int,
    ) -> tuple[int, bool]:
        filters = (
            Q(class_session_id=class_id)
            & Q(status=Booking.Status.CONFIRMED)
        )

        result = Booking.objects.filter(filters).aggregate(
            total=Count("id"),
            mine=Count("id", filter=Q(member_id=member_id)),
        )

        return result["total"], result["mine"] > 0

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

    @staticmethod
    def get_for_member(
        member_id: int,
        booking_id: int,
    ) -> Booking | None:
        filters = (
            Q(member_id=member_id)
            & Q(pk=booking_id)
        )

        return Booking.objects.filter(filters).first()

    @staticmethod
    def lock_for_member(
        member_id: int,
        booking_id: int,
    ) -> Booking | None:
        filters = (
            Q(member_id=member_id)
            & Q(pk=booking_id)
        )

        return Booking.objects.select_for_update().filter(filters).first()

    @staticmethod
    def mark_cancelled(
        booking: Booking,
        *,
        now: datetime,
        refunded: int,
        outcome: str,
    ) -> Booking:
        booking.status               = Booking.Status.CANCELLED
        booking.cancelled_at         = now
        booking.credits_refunded     = refunded
        booking.cancellation_outcome = outcome
        booking.save(
            update_fields=[
                "status",
                "cancelled_at",
                "credits_refunded",
                "cancellation_outcome",
            ]
        )
        return booking


class WaitlistRepository:

    @staticmethod
    def create(**fields: Any) -> WaitlistEntry:
        return WaitlistEntry.objects.create(**fields)

    @staticmethod
    def member_is_waiting(
        member_id: int,
        class_id: int,
    ) -> bool:
        filters = (
            Q(member_id=member_id)
            & Q(class_session_id=class_id)
            & Q(status=WaitlistEntry.Status.WAITING)
        )

        return WaitlistEntry.objects.filter(filters).exists()

    @staticmethod
    def lock_waiting_for_member(
        member_id: int,
        class_id: int,
    ) -> WaitlistEntry | None:
        filters = (
            Q(member_id=member_id)
            & Q(class_session_id=class_id)
            & Q(status=WaitlistEntry.Status.WAITING)
        )

        return WaitlistEntry.objects.select_for_update().filter(filters).first()

    @staticmethod
    def lock_queue(class_id: int) -> list[WaitlistEntry]:
        filters = (
            Q(class_session_id=class_id)
            & Q(status=WaitlistEntry.Status.WAITING)
            & Q(member__is_active=True)
        )

        return list(
            WaitlistEntry.objects.select_for_update(of=("self",))
            .filter(filters)
            .order_by("joined_at", "id")
        )

    @staticmethod
    def mark_left(
        entry: WaitlistEntry,
        *,
        now: datetime,
    ) -> WaitlistEntry:
        entry.status  = WaitlistEntry.Status.LEFT
        entry.left_at = now
        entry.save(update_fields=["status", "left_at"])
        return entry

    @staticmethod
    def mark_promoted(
        entry: WaitlistEntry,
        *,
        booking: Booking,
        now: datetime,
    ) -> WaitlistEntry:
        entry.status      = WaitlistEntry.Status.PROMOTED
        entry.promoted_at = now
        entry.booking     = booking
        entry.save(update_fields=["status", "promoted_at", "booking"])
        return entry

    @staticmethod
    def list_for_member(
        member_id: int,
        *,
        status: str | None = None,
    ) -> QuerySet[WaitlistEntry]:
        filters = Q(member_id=member_id)

        if status:
            filters &= Q(status=status)

        return (
            WaitlistEntry.objects.filter(filters)
            .select_related("class_session__studio")
            .order_by("joined_at", "id")
        )

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
