"""Sample bridge module for CI workflow testing."""


def process_message(payload: dict) -> dict:
    """Process an incoming MQTT message payload."""
    if not payload:
        raise ValueError("Empty payload")

    topic = payload.get("mqtt_topic", "")
    data = payload.get("payload", b"")

    return {
        "topic": topic,
        "size": len(data),
        "processed": True,
    }


def validate_tag(name: str, value) -> bool:
    """Validate a tag name and value."""
    if not name or not isinstance(name, str):
        return False
    if "/" not in name:
        return False
    return True


def get_version() -> str:
    """Return the current bridge version."""
    return "0.1.0"
