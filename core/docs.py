from collections.abc import Callable
from typing import Any, cast

from drf_yasg.utils import swagger_auto_schema as _swagger_auto_schema


def swagger_auto_schema[F: Callable[..., Any]](**kwargs: Any) -> Callable[[F], F]:
    return cast(Callable[[F], F], _swagger_auto_schema(**kwargs))
