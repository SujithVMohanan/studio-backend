from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.users.models import User
from core.encryption.fields import EncodedIdField

USER_ID_NAMESPACE = User._meta.label_lower


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


class GetUsersQuerySerializer(serializers.Serializer):
    uid       = EncodedIdField(namespace=USER_ID_NAMESPACE, required=False, help_text="Encoded user id")
    email     = serializers.CharField(required=False, allow_blank=True, max_length=254)
    name      = serializers.CharField(required=False, allow_blank=True, max_length=255)
    role      = serializers.ChoiceField(choices=User.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        for key in ("email", "name"):
            attrs[key] = (attrs.get(key) or "").strip() or None
        return attrs


class DeleteUsersSerializer(serializers.Serializer):
    uids = serializers.ListField(
        child=EncodedIdField(namespace=USER_ID_NAMESPACE),
        allow_empty=False,
        max_length=100,
    )

    def validate_uids(self, value):
        return list(dict.fromkeys(value))
