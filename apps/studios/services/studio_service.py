from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import QuerySet

from apps.studios.models import Studio
from apps.studios.repository import StudioRepository
from apps.users.models import User
from core.exceptions.business import BusinessConflict, ResourceNotFound


def _name_taken() -> BusinessConflict:
    return BusinessConflict("A studio with this name already exists.", code="STUDIO_NAME_TAKEN")


class StudioService:
    @staticmethod
    def create_studio(*, actor: User, validated_data: dict[str, Any]) -> Studio:
        try:
            with transaction.atomic():
                return StudioRepository.create(created_by=actor, **validated_data)
        except IntegrityError:
            raise _name_taken() from None

    @staticmethod
    def update_studio(*, studio_id: int, validated_data: dict[str, Any]) -> Studio:
        studio = StudioRepository.get_by_id(studio_id)
        if studio is None:
            raise ResourceNotFound("Studio not found.", code="STUDIO_NOT_FOUND")
        try:
            with transaction.atomic():
                return StudioRepository.update(studio, validated_data)
        except IntegrityError:
            raise _name_taken() from None

    @staticmethod
    def get_studios(*, validated_data: dict[str, Any]) -> QuerySet[Studio]:
        return StudioRepository.list_studios(
            studio_id=validated_data.get("uid"),
            name=validated_data.get("name"),
        )
