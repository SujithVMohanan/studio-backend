
from rest_framework import serializers

from apps.users.models import User
from core.encryption.fields import EncodedIdField


class LoginResponseSchema(serializers.ModelSerializer):

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


    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data
