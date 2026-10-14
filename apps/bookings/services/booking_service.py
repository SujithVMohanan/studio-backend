
import logging
from datetime import datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from apps.bookings.models import Booking
from apps.bookings.repository import BookingRepository, WaitlistRepository
from apps.credits.services.allocation import spend_for_booking
from apps.studios.repository import ClassSessionRepository
from apps.users.models import User
from core.exceptions.business import BusinessConflict, ResourceNotFound
from core.utils import clock
from core.utils.db import constraint_name

logger = logging.getLogger("studio")

IDEMPOTENCY_CONSTRAINT = "uniq_booking_idempotency_key_per_member"
CONFIRMED_CONSTRAINT   = "uniq_confirmed_booking_per_member_class"


def _replay(
    existing: Booking,
    class_id: int,
) -> tuple[Booking, bool]:
    if existing.class_session_id != class_id:
        raise BusinessConflict(
            "This Idempotency-Key was already used for a different request.",
            code="IDEMPOTENCY_CONFLICT",
        )

    return existing, False


class BookingService:
    @staticmethod
    def book_class(
        *,
        member: User,
        class_id: int,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> tuple[Booking, bool]:
        
        current_time = now if now is not None else clock.now()

        existing = BookingRepository.get_by_member_key(
            member.id,
            idempotency_key,
        )
        if existing is not None:
            return _replay(existing, class_id)

        try:
            with transaction.atomic():
                session = ClassSessionRepository.lock_by_id(class_id)

                if session is None:
                    raise ResourceNotFound(
                        "Class not found.",
                        code="CLASS_NOT_FOUND",
                    )

                if session.starts_at <= current_time:
                    raise BusinessConflict(
                        "This class has already started.",
                        code="CLASS_STARTED",
                    )

                if BookingRepository.member_has_confirmed(member.id, class_id):
                    raise BusinessConflict(
                        "You already have a booking for this class.",
                        code="ALREADY_BOOKED",
                    )

                if BookingRepository.count_confirmed(class_id) >= session.spots:
                    raise BusinessConflict(
                        "This class is full.",
                        code="CLASS_FULL",
                    )

                booking = BookingRepository.create(
                    member=member,
                    class_session=session,
                    source=Booking.Source.DIRECT,
                    credits_charged=session.credit_cost,
                    idempotency_key=idempotency_key,
                    booked_at=current_time,
                )

                spend_for_booking(
                    booking=booking,
                    now=current_time,
                )

                WaitlistRepository.mark_left_if_waiting(
                    member.id,
                    class_id,
                    current_time,
                )

        except IntegrityError as exc:
            constraint = constraint_name(exc)

            if constraint == IDEMPOTENCY_CONSTRAINT:
                existing = BookingRepository.get_by_member_key(
                    member.id,
                    idempotency_key,
                )

                if existing is not None:
                    return _replay(existing, class_id)

            if constraint == CONFIRMED_CONSTRAINT:
                raise BusinessConflict(
                    "You already have a booking for this class.",
                    code="ALREADY_BOOKED",
                ) from None

            raise

        logger.info(
            "booking_created booking_id=%s member_id=%s class_id=%s",
            booking.id,
            member.id,
            class_id,
        )

        return booking, True

    @staticmethod
    def list_bookings(
        *,
        member: User,
        validated_data: dict[str, Any],
    ) -> QuerySet[Booking]:
        return BookingRepository.list_for_member(
            member.id,
            status=validated_data.get("status"),
        )
