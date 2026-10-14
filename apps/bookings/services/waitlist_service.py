import logging
from datetime import datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from apps.bookings.models import Booking, WaitlistEntry
from apps.bookings.repository import BookingRepository, WaitlistRepository
from apps.credits.services.allocation import plan_allocation, record_spend
from apps.studios.models import ClassSession
from apps.studios.repository import ClassSessionRepository
from apps.users.models import User
from core.exceptions.business import BusinessConflict, ResourceNotFound
from core.utils import clock
from core.utils.db import constraint_name

logger = logging.getLogger("studio")

WAITING_CONSTRAINT   = "uniq_waiting_entry_per_member_class"
INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"


def _lock_class(class_id: int) -> ClassSession:
    session = ClassSessionRepository.lock_by_id(class_id)

    if session is None:
        raise ResourceNotFound(
            "Class not found.",
            code="CLASS_NOT_FOUND",
        )

    return session


def _already_waitlisted() -> BusinessConflict:
    return BusinessConflict(
        "You are already on the waitlist for this class.",
        code="ALREADY_WAITLISTED",
    )


class WaitlistService:
    @staticmethod
    def join_waitlist(
        *,
        member: User,
        class_id: int,
        now: datetime | None = None,
    ) -> WaitlistEntry:

        current_time = now if now is not None else clock.now()

        try:
            with transaction.atomic():
                session = _lock_class(class_id)

                if session.starts_at <= current_time:
                    raise BusinessConflict(
                        "This class has already started.",
                        code="CLASS_STARTED",
                    )

                confirmed, member_booked = BookingRepository.confirmed_summary(
                    class_id,
                    member.id,
                )

                if member_booked:
                    raise BusinessConflict(
                        "You already have a booking for this class.",
                        code="ALREADY_BOOKED",
                    )

                if WaitlistRepository.member_is_waiting(member.id, class_id):
                    raise _already_waitlisted()

                if confirmed < session.spots:
                    raise BusinessConflict(
                        "Spots are still available. Book the class instead.",
                        code="SPOTS_AVAILABLE",
                    )

                entry = WaitlistRepository.create(
                    member=member,
                    class_session=session,
                    joined_at=current_time,
                )

        except IntegrityError as exc:
            if constraint_name(exc) == WAITING_CONSTRAINT:
                raise _already_waitlisted() from None
            raise

        logger.info(
            "waitlist_joined entry_id=%s member_id=%s class_id=%s",
            entry.id,
            member.id,
            class_id,
        )

        return entry

    @staticmethod
    def leave_waitlist(
        *,
        member: User,
        class_id: int,
        now: datetime | None = None,
    ) -> WaitlistEntry:

        current_time = now if now is not None else clock.now()

        with transaction.atomic():
            _lock_class(class_id)

            entry = WaitlistRepository.lock_waiting_for_member(member.id, class_id)

            if entry is None:
                raise ResourceNotFound(
                    "You are not on the waitlist for this class.",
                    code="NOT_WAITLISTED",
                )

            return WaitlistRepository.mark_left(entry, now=current_time)

    @staticmethod
    def list_waitlist(
        *,
        member: User,
        validated_data: dict[str, Any],
    ) -> QuerySet[WaitlistEntry]:
        return WaitlistRepository.list_for_member(
            member.id,
            status=validated_data.get("status"),
        )

    @staticmethod
    def promote_from_waitlist(
        *,
        session: ClassSession,
        now: datetime,
    ) -> list[Booking]:

        free_spots = session.spots - BookingRepository.count_confirmed(session.id)
        promoted: list[Booking] = []

        if free_spots <= 0:
            return promoted

        today = clock.utc_today(now)

        for entry in WaitlistRepository.lock_queue(session.id):
            try:
                plan = plan_allocation(
                    member_id=entry.member_id,
                    amount=session.credit_cost,
                    today=today,
                )
            except BusinessConflict as exc:
                if exc.error_code != INSUFFICIENT_CREDITS:
                    raise
                continue

            booking = BookingRepository.create(
                member_id=entry.member_id,
                class_session=session,
                source=Booking.Source.WAITLIST,
                credits_charged=session.credit_cost,
                idempotency_key=None,
                booked_at=now,
            )

            record_spend(booking=booking, plan=plan, now=now)

            WaitlistRepository.mark_promoted(entry, booking=booking, now=now)

            promoted.append(booking)

            logger.info(
                "waitlist_promoted booking_id=%s member_id=%s class_id=%s",
                booking.id,
                entry.member_id,
                session.id,
            )

            if len(promoted) == free_spots:
                break

        return promoted
