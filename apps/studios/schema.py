from rest_framework import serializers

from apps.studios.models import ClassSession, Studio
from apps.studios.serializer import CLASS_ID_NAMESPACE, STUDIO_ID_NAMESPACE
from core.encryption.fields import EncodedIdField


class StudioSchema(serializers.ModelSerializer):
    uid = EncodedIdField(namespace=STUDIO_ID_NAMESPACE, source="id", read_only=True)

    class Meta:
        model = Studio
        fields = ("uid", "name", "timezone", "cancellation_cutoff_hours", "created_at", "updated_at")
        read_only_fields = fields


class StudioSummarySchema(StudioSchema):
    class Meta(StudioSchema.Meta):
        fields = ("uid", "name", "timezone", "cancellation_cutoff_hours")
        read_only_fields = fields

    

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data




class ClassSessionSchema(serializers.ModelSerializer):

    uid             = EncodedIdField(namespace=CLASS_ID_NAMESPACE, source="id", read_only=True)
    studio          = StudioSummarySchema(read_only=True)
    starts_at_local = serializers.SerializerMethodField()
    ends_at         = serializers.DateTimeField(read_only=True)
    spots_remaining = serializers.SerializerMethodField()

    class Meta:
        model = ClassSession
        fields = (
            "uid", "studio", "starts_at", "starts_at_local", "ends_at",
            "duration_minutes", "spots", "credit_cost", "spots_remaining",
        )
        read_only_fields = fields

    def get_starts_at_local(self, obj: ClassSession) -> str:
        return obj.starts_at.astimezone(obj.studio.zone).isoformat()

    def get_spots_remaining(self, obj: ClassSession) -> int:
        return max(obj.spots - getattr(obj, "confirmed_count", 0), 0)


    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None:
                data[key] = ""
        return data

