from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.users.models import User
from apps.users.repository import UserRepository
from core.exceptions.auth import AuthValidationError
from core.utils.tokens import issue_tokens

_EMAIL_TAKEN = {"email": ["This email is already registered."]}


class UserService:
    @staticmethod
    def register_user(*, validated_data: dict) -> tuple[dict, User]:
        email = validated_data["email"]

        if UserRepository.email_exists(email):
            raise AuthValidationError(_EMAIL_TAKEN, code="EMAIL_ALREADY_EXISTS")

        try:
            with transaction.atomic():
                user = UserRepository.create_member(
                    email=email,
                    password=validated_data["password"],
                    full_name=validated_data["full_name"],
                )
        except IntegrityError:
            raise AuthValidationError(_EMAIL_TAKEN, code="EMAIL_ALREADY_EXISTS") from None

        return issue_tokens(user), user

    @staticmethod
    def get_users(*, validated_data: dict):
        return UserRepository.list_users(
            user_id   = validated_data.get("uid"),
            email     = validated_data.get("email"),
            name      = validated_data.get("name"),
            role      = validated_data.get("role"),
            is_active = validated_data.get("is_active"),
        )

    @staticmethod
    def delete_users(*, actor: User, validated_data: dict) -> dict:
        user_ids = validated_data["uids"]

        if actor.pk in user_ids:
            raise ValidationError({"uids": ["You cannot delete your own account."]})
        if UserRepository.list_superuser_ids(user_ids):
            raise ValidationError({"uids": ["Superuser accounts cannot be deleted."]})

        with transaction.atomic():
            deleted = UserRepository.deactivate_by_ids(user_ids)
            if not deleted:
                raise NotFound("User not found.")
            UserRepository.revoke_outstanding_tokens(user_ids)

        return {"deleted": deleted}
