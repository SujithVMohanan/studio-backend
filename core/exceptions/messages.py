from typing import Any


def get_error_message(errors: Any) -> str:
    if errors is None or errors == "":
        return ""
    if isinstance(errors, str):
        return errors
    if isinstance(errors, list):
        return get_error_message(errors[0]) if errors else ""
    if isinstance(errors, dict):
        if not errors:
            return ""
        return get_error_message(next(iter(errors.values())))
    return str(errors)
