from rest_framework import serializers

from apps.credits.models import CreditLedger, CreditPack
from apps.users.models import User
from core.encryption.fields import EncodedIdField

PACK_ID_NAMESPACE   = CreditPack._meta.label_lower
LEDGER_ID_NAMESPACE = CreditLedger._meta.label_lower
USER_ID_NAMESPACE   = User._meta.label_lower


class CreditPackSchema(serializers.ModelSerializer):
    uid        = EncodedIdField(namespace=PACK_ID_NAMESPACE, source="id", read_only=True)
    member_uid = EncodedIdField(namespace=USER_ID_NAMESPACE, source="member_id", read_only=True)

    class Meta:
        model = CreditPack
        fields = ("uid", "member_uid", "credits", "granted_on", "expires_on", "created_at")
        read_only_fields = fields

        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data



class PackBalanceSchema(serializers.Serializer):

    uid        = EncodedIdField(namespace=PACK_ID_NAMESPACE, source="pack.id", read_only=True)
    credits    = serializers.IntegerField(source="pack.credits")
    remaining  = serializers.IntegerField()
    granted_on = serializers.DateField(source="pack.granted_on")
    expires_on = serializers.DateField(source="pack.expires_on")
    is_active  = serializers.BooleanField()
    is_expired = serializers.BooleanField()

    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data



class BalanceSchema(serializers.Serializer):

    at      = serializers.DateTimeField()
    balance = serializers.IntegerField()
    packs   = PackBalanceSchema(many=True)

    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data



class LedgerEntrySchema(serializers.ModelSerializer):
    uid      = EncodedIdField(namespace=LEDGER_ID_NAMESPACE, source="id", read_only=True)
    pack_uid = EncodedIdField(namespace=PACK_ID_NAMESPACE, source="pack_id", read_only=True)

    class Meta:
        model = CreditLedger
        fields = ("uid", "amount", "cause", "pack_uid", "created_at")
        read_only_fields = fields

    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data
