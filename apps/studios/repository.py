
"""Data access layer for the studios app."""

from datetime import datetime
from typing import Any

from django.db.models import Count, IntegerField, Q, QuerySet, Value

from apps.studios.models import ClassSession, Studio


class StudioRepository:

    @staticmethod
    def create(**fields: Any) -> Studio:
        return Studio.objects.create(**fields)

    @staticmethod
    def get_by_id(studio_id: int) -> Studio | None:
        return Studio.objects.filter(pk=studio_id).first()

    @staticmethod
    def update(studio: Studio, fields: dict[str, Any]) -> Studio:
        if not fields:
            return studio

        for field, value in fields.items():
            setattr(studio, field, value)

        update_fields = list(fields)
        if "updated_at" not in update_fields:
            update_fields.append("updated_at")

        studio.save(update_fields=update_fields)
        return studio

    @staticmethod
    def list_studios(
        *,
        studio_id: int | None = None,
        name: str | None = None,
    ) -> QuerySet[Studio]:
        filters = Q()

        if studio_id is not None:
            filters &= Q(pk=studio_id)

        if name:
            filters &= Q(name__icontains=name.strip())

        return Studio.objects.filter(filters).order_by("name", "id")


class ClassSessionRepository:

    @staticmethod
    def create(**fields: Any) -> ClassSession:
        return ClassSession.objects.create(**fields)

    @staticmethod
    def lock_by_id(class_id: int) -> ClassSession | None:
        return (
            ClassSession.objects.select_for_update(of=("self",))
            .select_related("studio")
            .filter(pk=class_id)
            .first()
        )

    @staticmethod
    def browse(
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        studio_id: int | None = None,
        class_id: int | None = None,
    ) -> QuerySet[ClassSession]:
        filters = Q()

        if class_id is not None:
            filters &= Q(pk=class_id)

        if start is not None:
            filters &= Q(starts_at__gte=start)

        if end is not None:
            filters &= Q(starts_at__lt=end)

        if studio_id is not None:
            filters &= Q(studio_id=studio_id)

        return (
                ClassSession.objects.select_related("studio")
                .filter(filters)
                .annotate(confirmed_count=Count("bookings", filter=Q(bookings__status="confirmed")))
                .order_by("starts_at", "id")
        )
