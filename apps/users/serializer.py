from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.users.models import User


def _password_field():
    return serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        max_length=128,
        style={"input_type": "password"},
    )


class RegisterUserSerializer(serializers.Serializer):
    email            = serializers.EmailField(max_length=254)
    full_name        = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    password         = _password_field()
    confirm_password = _password_field()

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": ["Passwords do not match."]}
            )
        try:
            validate_password(
                attrs["password"],
                user=User(email=attrs["email"], full_name=attrs["full_name"]),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs


class LoginUserSerializer(serializers.Serializer):
    email    = serializers.EmailField(max_length=254)
    password = _password_field()

    def validate_email(self, value):
        return value.strip().lower()


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField(trim_whitespace=True)


class LogoutUserSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)

    def validate_refresh(self, value):
        return (value or "").strip() or None
