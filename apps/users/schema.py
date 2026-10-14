from rest_framework import serializers

from apps.users.models import User
from core.encryption.fields import EncodedIdField
from core.utils.serializers import BlankNullsMixin


class LoginResponseSchema(BlankNullsMixin, serializers.ModelSerializer):
    uid = EncodedIdField(
        namespace=User._meta.label_lower,
        source="id",
        read_only=True,
    )

    class Meta:
        model = User
        fields = (
            "uid",
            "full_name",
            "email",
            "role",
            "is_active",
            "date_joined",
        )
        read_only_fields = fields


class GetUsersApiSchema(LoginResponseSchema):
    class Meta(LoginResponseSchema.Meta):
        fields = LoginResponseSchema.Meta.fields + (
            "is_staff",
            "last_login",
        )
        read_only_fields = fields
