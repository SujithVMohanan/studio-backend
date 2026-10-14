from rest_framework import serializers

from apps.credits.models import CreditLedger, CreditPack
from apps.credits.types import BalanceView, PackBalance
from apps.users.models import User
from core.encryption.fields import EncodedIdField
from core.utils.serializers import BlankNullsMixin

PACK_ID_NAMESPACE    = CreditPack._meta.label_lower
LEDGER_ID_NAMESPACE  = CreditLedger._meta.label_lower
USER_ID_NAMESPACE    = User._meta.label_lower
BOOKING_ID_NAMESPACE = "bookings.booking"


class CreditPackSchema(BlankNullsMixin, serializers.ModelSerializer[CreditPack]):
    uid        = EncodedIdField(namespace=PACK_ID_NAMESPACE, source="id", read_only=True)
    member_uid = EncodedIdField(namespace=USER_ID_NAMESPACE, source="member_id", read_only=True)

    class Meta:
        model = CreditPack
        fields = ("uid", "member_uid", "credits", "granted_on", "expires_on", "created_at")
        read_only_fields = fields


class PackBalanceSchema(BlankNullsMixin, serializers.Serializer[PackBalance]):
    uid        = EncodedIdField(namespace=PACK_ID_NAMESPACE, source="pack.id", read_only=True)
    credits    = serializers.IntegerField(source="pack.credits")
    remaining  = serializers.IntegerField()
    granted_on = serializers.DateField(source="pack.granted_on")
    expires_on = serializers.DateField(source="pack.expires_on")
    is_active  = serializers.BooleanField()
    is_expired = serializers.BooleanField()


class BalanceSchema(BlankNullsMixin, serializers.Serializer[BalanceView]):
    at      = serializers.DateTimeField()
    balance = serializers.IntegerField()
    packs   = PackBalanceSchema(many=True)


class LedgerEntrySchema(BlankNullsMixin, serializers.ModelSerializer[CreditLedger]):
    uid         = EncodedIdField(namespace=LEDGER_ID_NAMESPACE, source="id", read_only=True)
    pack_uid    = EncodedIdField(namespace=PACK_ID_NAMESPACE, source="pack_id", read_only=True)
    booking_uid = EncodedIdField(namespace=BOOKING_ID_NAMESPACE, source="booking_id", read_only=True)

    class Meta:
        model = CreditLedger
        fields = ("uid", "amount", "cause", "pack_uid", "booking_uid", "created_at")
        read_only_fields = fields
