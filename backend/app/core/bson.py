from typing import Any

from bson import ObjectId


def stringify_objectids(value: Any) -> Any:
    """Recursively convert MongoDB ObjectId values to strings."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: stringify_objectids(item) for key, item in value.items()}
    if isinstance(value, list):
        return [stringify_objectids(item) for item in value]
    return value
