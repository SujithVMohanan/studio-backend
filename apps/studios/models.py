from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _



class Studio(models.Model):

    name                      = models.CharField(_("Name"), max_length=150,blank=False, unique=True)
    timezone                  = models.CharField(_("Timezone"), max_length=64,blank=False, default="UTC")
    cancellation_cutoff_hours = models.PositiveSmallIntegerField(_("Cancellation Cutoff Hours"), default=4)
    created_by                = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_studios"
    )
    created_at                = models.DateTimeField(auto_now_add=True)
    updated_at                = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "studios_studios"
        ordering = ("name", "id")

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def __str__(self) -> str:
        return self.name


class ClassSession(models.Model):
    
    studio           = models.ForeignKey(
        Studio, on_delete=models.PROTECT, related_name="class_sessions", db_index=False
    )
    starts_at        = models.DateTimeField(_("Start Time"))
    duration_minutes = models.PositiveIntegerField(_("Duration (minutes)"))
    spots            = models.PositiveIntegerField(_("Spots"))
    credit_cost      = models.PositiveIntegerField(_("Credit Cost"))
    created_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_classes"
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "studios_class_sessions"
        ordering = ("starts_at", "id")
        indexes = [
            models.Index(fields=["starts_at"], name="class_starts_at_idx"),
            models.Index(fields=["studio", "starts_at"], name="class_studio_starts_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(spots__gte=1), name="class_spots_gte_1"),
            models.CheckConstraint(condition=Q(duration_minutes__gte=1), name="class_duration_gte_1"),
        ]