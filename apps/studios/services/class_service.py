

from datetime import datetime
from typing import Any

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from apps.studios.models import ClassSession
from apps.studios.repository import ClassSessionRepository, StudioRepository
from apps.users.models import User
from core.exceptions.business import ResourceNotFound
from core.utils import clock


class ClassService:
    @staticmethod
    def schedule_class(
        *,
        actor: User,
        validated_data: dict[str, Any],
        now: datetime | None = None,
    ) -> ClassSession:
        current_time = now if now is not None else clock.now()
        starts_at = validated_data["starts_at"]

        if starts_at <= current_time:
            raise ValidationError(
                {"starts_at": ["Class must start in the future."]}
            )

        studio = StudioRepository.get_by_id(validated_data["studio_uid"])
        if studio is None:
            raise ResourceNotFound(
                "Studio not found.",
                code="STUDIO_NOT_FOUND",
            )

        return ClassSessionRepository.create(
            studio=studio,
            starts_at=starts_at,
            duration_minutes=validated_data["duration_minutes"],
            spots=validated_data["spots"],
            credit_cost=validated_data["credit_cost"],
            created_by=actor,
        )

    @staticmethod
    def browse_classes(
        *,
        validated_data: dict[str, Any],
    ) -> QuerySet[ClassSession]:
        return ClassSessionRepository.browse(
            start=validated_data.get("start"),
            end=validated_data.get("end"),
            studio_id=validated_data.get("studio_uid"),
            class_id=validated_data.get("uid"),
        )
