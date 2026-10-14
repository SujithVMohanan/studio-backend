from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from core.encryption.ids import InvalidEncodedId, decode_id, encode_id


class EncodedIdField(serializers.Field[int, str, str, Any]):
    default_error_messages = {
        "invalid": "Invalid ID.",
    }

    def __init__(self, namespace: str, **kwargs: Any) -> None:
        if not namespace or not isinstance(namespace, str):
            raise ValueError("A valid namespace is required.")

        self.namespace = namespace
        super().__init__(**kwargs)

    def to_representation(self, value: int) -> str:
        return encode_id(value, self.namespace)

    def to_internal_value(self, data: str) -> int:
        try:
            return decode_id(data, self.namespace)
        except InvalidEncodedId:
            self.fail("invalid")


def decode_id_or_404(token: str, namespace: str) -> int:
    try:
        return decode_id(token, namespace)
    except InvalidEncodedId as exc:
        raise NotFound("Resource not found.") from exc
