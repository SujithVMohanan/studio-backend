"""Data access layer for the users app."""

from django.utils import timezone

from apps.users.models import User


class UserRepository:
    @staticmethod
    def email_exists(email: str) -> bool:
        return User.objects.filter(email=email).exists()

    @staticmethod
    def get_by_email(email: str) -> User | None:
        return User.objects.filter(email=email).first()

    @staticmethod
    def get_active_by_id(user_id) -> User | None:
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
