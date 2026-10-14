from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.studios.models import ClassSession


class Booking(models.Model):

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    class Source(models.TextChoices):
        DIRECT   = "direct", "Direct"
        WAITLIST = "waitlist", "Waitlist"

    class Outcome(models.TextChoices):
        REFUNDED  = "refunded", "Refunded"
        FORFEITED = "forfeited", "Forfeited"

    member               = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    class_session        = models.ForeignKey(ClassSession, on_delete=models.PROTECT, related_name="bookings")
    status               = models.CharField(
        _("Status"), max_length=10, choices=Status.choices, default=Status.CONFIRMED
    )
    source               = models.CharField(_("Source"), max_length=10, choices=Source.choices, default=Source.DIRECT)
    credits_charged      = models.PositiveIntegerField(_("Credits Charged"))
    # NULL for waitlist promotions; NULLs never collide in the per-member unique constraint.
    idempotency_key      = models.CharField(  # noqa: DJ001
        _("Idempotency Key"), max_length=255, null=True, blank=True
    )
    booked_at            = models.DateTimeField(_("Booked At"), default=timezone.now)
    cancelled_at         = models.DateTimeField(_("Cancelled At"), null=True, blank=True)
    credits_refunded     = models.PositiveIntegerField(null=True, blank=True)
    cancellation_outcome = models.CharField(  # noqa: DJ001
        _("Cancellation Outcome"), max_length=10, choices=Outcome.choices, null=True, blank=True
    )

    class Meta:
        db_table = "bookings_bookings"
        ordering = ("-booked_at", "-id")
        indexes = [models.Index(fields=["class_session", "status"], name="booking_class_status_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "class_session"],
                condition=Q(status="confirmed"),
                name="uniq_confirmed_booking_per_member_class",
            ),
            models.UniqueConstraint(
                fields=["member", "idempotency_key"],
                name="uniq_booking_idempotency_key_per_member",
            ),
        ]

    def __str__(self) -> str:
        return f"Booking {self.pk} ({self.status})"




class WaitlistEntry(models.Model):

    class Status(models.TextChoices):
        WAITING  = "waiting", "Waiting"
        PROMOTED = "promoted", "Promoted"
        LEFT     = "left", "Left"

    member        = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="waitlist_entries"
    )
    class_session = models.ForeignKey(ClassSession, on_delete=models.PROTECT, related_name="waitlist_entries")
    status        = models.CharField(_("Status"), max_length=10, choices=Status.choices, default=Status.WAITING)
    joined_at     = models.DateTimeField(_("Joined At"), default=timezone.now)
    promoted_at   = models.DateTimeField(_("Promoted At"), null=True, blank=True)
    left_at       = models.DateTimeField(_("Left At"), null=True, blank=True)
    booking       = models.OneToOneField(
        Booking, on_delete=models.PROTECT, null=True, blank=True, related_name="waitlist_entry"
    )

    class Meta:
        db_table = "bookings_waitlist_entries"
        ordering = ("joined_at", "id")
        indexes = [
            models.Index(fields=["class_session", "status", "joined_at", "id"], name="waitlist_queue_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "class_session"],
                condition=Q(status="waiting"),
                name="uniq_waiting_entry_per_member_class",
            ),
        ]

    def __str__(self) -> str:
        return f"Waitlist {self.pk} ({self.status})"
