from django.db import IntegrityError


def constraint_name(exc: IntegrityError) -> str | None:
    diagnostic = getattr(exc.__cause__, "diag", None)
    return getattr(diagnostic, "constraint_name", None)
