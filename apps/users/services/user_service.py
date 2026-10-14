
from django.db import IntegrityError, transaction

from apps.users.models import User
from apps.users.repository import UserRepository
from core.exceptions.auth import AuthValidationError
from core.utils.tokens import issue_tokens


_EMAIL_TAKEN = {
    "email": ["This email is already registered."],
}


class UserService:
    @staticmethod
    def register_user(*, validated_data: dict) -> tuple[dict, User]:
        email = validated_data["email"]

        if UserRepository.email_exists(email):
            raise AuthValidationError(
                _EMAIL_TAKEN,
                code="EMAIL_ALREADY_EXISTS",
            )

        try:
            with transaction.atomic():
                user = UserRepository.create_member(
                    email=email,
                    password=validated_data["password"],
                    full_name=validated_data["full_name"],
                )
        except IntegrityError:
            raise AuthValidationError(
                _EMAIL_TAKEN,
                code="EMAIL_ALREADY_EXISTS",
            ) from None

        tokens = issue_tokens(user)

        return tokens, user
