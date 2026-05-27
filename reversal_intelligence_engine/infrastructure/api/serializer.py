# ================================
# Serializer Layer
# ================================

from dataclasses import asdict, is_dataclass

from infrastructure.observability.timeline_builder import build_timeline


def serialize_response(data):
    """
    Recursively converts workflow and domain objects into
    JSON-serializable structures for API responses.
    Handles dataclasses, dicts, lists, and primitives.
    """

    if is_dataclass(data):
        return asdict(data)

    if isinstance(data, dict):
        return {key: serialize_response(value) for key, value in data.items()}

    if isinstance(data, list):
        return [serialize_response(item) for item in data]

    return data


def serialize_recommendations(state):
    """Returns serialized final recommendations from workflow state."""
    return serialize_response(state.get("final_output", []))


def serialize_execution_log(state):
    return state.get("execution_log", [])


def serialize_timeline(state):

    return build_timeline(state)