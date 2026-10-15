"""Data access layer for the users app."""

from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from apps.users.models import User


class UserRepository:
    @staticmethod
    def email_exists(email: str) -> bool:
        return User.objects.filter(email=email).exists()

    @staticmethod
    def get_by_email(email: str) -> User | None:
        return User.objects.filter(email=email).first()

    @staticmethod
    def get_active_by_id(user_id: int | str) -> User | None:
        return User.objects.filter(pk=user_id, is_active=True).first()

    @staticmethod
    def create_member(*, email: str, password: str, full_name: str = "") -> User:
        return User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            role=User.Role.MEMBER,
        )

    @staticmethod
    def update_last_login(user: User) -> None:
        now = timezone.now()
        User.objects.filter(pk=user.pk).update(last_login=now)
        user.last_login = now

    @staticmethod
    def list_users(
        *,
        exclude_user_id: int,
        user_id: int | None = None,
        email: str | None = None,
        name: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> QuerySet[User]:
        filters = Q()
        if user_id is not None:
            filters &= Q(pk=user_id)
        if email:
            filters &= Q(email__icontains=email)
        if name:
            filters &= Q(full_name__icontains=name)
        if role:
            filters &= Q(role=role)
        if is_active is not None:
            filters &= Q(is_active=is_active)

        return (
            User.objects.filter(filters)
            .exclude(Q(pk=exclude_user_id) | Q(is_superuser=True))
            .only(
                "id",
                "full_name",
                "email",
                "role",
                "is_active",
                "is_staff",
                "last_login",
                "date_joined",
            )
            .order_by("-id")
        )

    @staticmethod
    def list_superuser_ids(user_ids: list[int]) -> list[int]:
        return list(
            User.objects.filter(pk__in=user_ids, is_superuser=True)
            .values_list("id", flat=True)
        )

    @staticmethod
    def deactivate_by_ids(user_ids: list[int]) -> int:
        return User.objects.filter(pk__in=user_ids, is_active=True).update(is_active=False)

    @staticmethod
    def revoke_outstanding_tokens(user_ids: list[int]) -> int:
        tokens = OutstandingToken.objects.filter(
            user_id__in=user_ids,
            expires_at__gt=timezone.now(),
        ).only("id")
        created = BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=token) for token in tokens],
            ignore_conflicts=True,
        )
        return len(created)
