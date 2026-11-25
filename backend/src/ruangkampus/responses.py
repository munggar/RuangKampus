from typing import Any


def success(data: Any = None, message: str = "OK", meta: Any = None) -> dict:
    return {"success": True, "message": message, "data": data, "meta": meta}


def failure(message: str, errors: list | None = None) -> dict:
    return {"success": False, "message": message, "errors": errors or []}
