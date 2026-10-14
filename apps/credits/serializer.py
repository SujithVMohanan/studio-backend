from typing import Any

from rest_framework import serializers

from apps.credits.models import CreditLedger
from apps.users.models import User
from core.encryption.fields import EncodedIdField
from core.utils.serializers import AwareDateTimeField, StrictIntegerField


class GrantCreditPackSerializer(serializers.Serializer[Any]):
    member_uid = EncodedIdField(namespace=User._meta.label_lower)
    credits    = StrictIntegerField(min_value=1)
    granted_on = serializers.DateField()
    expires_on = serializers.DateField()

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["expires_on"] < attrs["granted_on"]:
            raise serializers.ValidationError({"expires_on": ["expires_on must be on or after granted_on."]})
        return attrs


class GetLedgerQuerySerializer(serializers.Serializer[Any]):
    cause = serializers.ChoiceField(choices=CreditLedger.Cause.choices, required=False)


class BalanceAtQuerySerializer(serializers.Serializer[Any]):
    at = AwareDateTimeField(help_text="ISO 8601 with offset, e.g. 2026-10-14T10:00:00Z")
