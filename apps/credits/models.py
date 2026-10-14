from datetime import date
from typing import Any, NoReturn

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CreditPack(models.Model):

    member     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="credit_packs")
    credits    = models.PositiveIntegerField(_("Credits"))
    granted_on = models.DateField(_("Granted On"))
    expires_on = models.DateField(_("Expires On"))
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="granted_packs")
    created_at = models.DateTimeField(_("Created At"), default=timezone.now)

    class Meta:
        db_table = "credits_credit_packs"
        ordering = ("expires_on", "id")
        indexes = [models.Index(fields=["member", "expires_on"], name="pack_member_expiry_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(credits__gte=1), name="pack_credits_gte_1"),
            models.CheckConstraint(condition=Q(expires_on__gte=F("granted_on")), name="pack_expiry_after_grant"),
        ]

    def __str__(self) -> str:
        return f"{self.credits} credits for {self.member_id} until {self.expires_on}"

    def is_active_on(self, day: date) -> bool:
        return self.granted_on <= day <= self.expires_on



class CreditLedger(models.Model):

    class Cause(models.TextChoices):
        GRANT  = "grant", "Grant"
        SPEND  = "spend", "Spend"
        REFUND = "refund", "Refund"

    member     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="credit_movements")
    pack       = models.ForeignKey(CreditPack, on_delete=models.PROTECT, related_name="movements")
    amount     = models.IntegerField(_("Amount"),blank=False)
    cause      = models.CharField(  # noqa: DJ001
        _("Cause"), max_length=10, choices=Cause.choices, blank=True, null=True
    )
    created_at = models.DateTimeField(_("Created At"), default=timezone.now)
    booking    = models.ForeignKey(
                        "bookings.Booking", on_delete=models.PROTECT,
                        null=True, blank=True,
                        related_name="ledger_entries"
                    )

    class Meta:
        db_table = "credits_ledger"
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=["member", "created_at"], name="ledger_member_created_idx"),
            models.Index(fields=["pack", "created_at"], name="ledger_pack_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(cause="spend", amount__lt=0)
                    | Q(cause__in=["grant", "refund"], amount__gt=0)
                ),
                name="ledger_amount_sign_matches_cause",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cause} {self.amount:+d} for {self.member_id}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise RuntimeError("Credit ledger rows are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise RuntimeError("Credit ledger rows are append-only.")
