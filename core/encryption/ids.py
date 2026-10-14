
import base64
import binascii
import struct

from django.utils.crypto import constant_time_compare, salted_hmac

_KEY_SALT = "studio.encoded-id"
_ID_FORMAT = ">Q"
_ID_SIZE = struct.calcsize(_ID_FORMAT)
_MAC_SIZE = 8
_TOKEN_LENGTH = 22
_MAX_ID = (1 << 64) - 1
_PADDING = "=" * (-_TOKEN_LENGTH % 4)


class InvalidEncodedId(ValueError):
    """Raised when an encoded ID is invalid."""


def _mac(namespace: str, payload: bytes) -> bytes:
    return salted_hmac(
        key_salt=f"{_KEY_SALT}:{namespace}",
        value=payload,
        algorithm="sha256",
    ).digest()[:_MAC_SIZE]


def _mask(namespace: str, mac: bytes, payload: bytes) -> bytes:
    key = salted_hmac(
        key_salt=f"{_KEY_SALT}:{namespace}:mask",
        value=mac,
        algorithm="sha256",
    ).digest()

    return bytes(
        value ^ mask
        for value, mask in zip(payload, key[: len(payload)], strict=True)
    )


def encode_id(pk: int, namespace: str) -> str:
    if (
        isinstance(pk, bool)
        or not isinstance(pk, int)
        or not 0 <= pk <= _MAX_ID
    ):
        raise InvalidEncodedId(
            "ID must be a non-negative 64-bit integer."
        )

    if not isinstance(namespace, str) or not namespace:
        raise InvalidEncodedId("Namespace is required.")

    payload = struct.pack(_ID_FORMAT, pk)
    mac = _mac(namespace, payload)
    masked_payload = _mask(namespace, mac, payload)

    token = base64.urlsafe_b64encode(mac + masked_payload)
    return token.rstrip(b"=").decode("ascii")


def decode_id(token: str, namespace: str) -> int:
    if (
        not isinstance(token, str)
        or len(token) != _TOKEN_LENGTH
        or not isinstance(namespace, str)
        or not namespace
    ):
        raise InvalidEncodedId("Invalid ID.")

    try:
        raw = base64.b64decode(
            token + _PADDING,
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise InvalidEncodedId("Invalid ID.") from exc

    if len(raw) != _MAC_SIZE + _ID_SIZE:
        raise InvalidEncodedId("Invalid ID.")

    mac = raw[:_MAC_SIZE]
    masked_payload = raw[_MAC_SIZE:]
    payload = _mask(namespace, mac, masked_payload)

    expected_mac = _mac(namespace, payload)

    if not constant_time_compare(mac, expected_mac):
        raise InvalidEncodedId("Invalid ID.")

    (pk,) = struct.unpack(_ID_FORMAT, payload)
    return int(pk)
