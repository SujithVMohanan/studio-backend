
import logging
from datetime import datetime

from django.db import transaction

from apps.bookings.models import Booking
from apps.bookings.repository import BookingRepository
from apps.bookings.services.cutoff import is_refundable
from apps.bookings.services.waitlist_service import WaitlistService
from apps.credits.services.allocation import refund_booking
from apps.studios.repository import ClassSessionRepository
from apps.users.models import User
from core.exceptions.business import BusinessConflict, ResourceNotFound
from core.utils import clock


logger = logging.getLogger("studio")


def _booking_not_found() -> ResourceNotFound:
    return ResourceNotFound(
        "Booking not found.",
        code="BOOKING_NOT_FOUND",
    )


class CancelService:

    @staticmethod
    def cancel_booking(
        *,
        member: User,
        booking_id: int,
        now: datetime | None = None,
    ) -> Booking:
        current_time = now if now is not None else clock.now()

        booking = BookingRepository.get_for_member(member.id, booking_id)
        if booking is None:
            raise _booking_not_found()

        with transaction.atomic():
            session = ClassSessionRepository.lock_by_id(
                booking.class_session_id,
            )
            booking = BookingRepository.lock_for_member(
                member.id,
                booking_id,
            )

            if session is None or booking is None:
                raise _booking_not_found()

            if booking.status == Booking.Status.CANCELLED:
                raise BusinessConflict(
                    "This booking is already cancelled.",
                    code="ALREADY_CANCELLED",
                )

            studio = session.studio
            refundable = is_refundable(
                starts_at=session.starts_at,
                studio_tz=studio.timezone,
                cutoff_hours=studio.cancellation_cutoff_hours,
                now=current_time,
            )

            if refundable:
                refunded = refund_booking(
                    booking=booking,
                    now=current_time,
                )
                outcome = Booking.Outcome.REFUNDED
            else:
                refunded = 0
                outcome = Booking.Outcome.FORFEITED

            BookingRepository.mark_cancelled(
                booking,
                now=current_time,
                refunded=refunded,
                outcome=outcome,
            )

            if session.starts_at > current_time:
                WaitlistService.promote_from_waitlist(
                    session=session,
                    now=current_time,
                )

        logger.info(
            "booking_cancelled booking_id=%s member_id=%s outcome=%s refunded=%s",
            booking.id,
            member.id,
            outcome,
            refunded,
        )

        return booking
