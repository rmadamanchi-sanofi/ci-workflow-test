"""Tests for bridge.main module."""
import pytest
from bridge.main import process_message, validate_tag


class TestProcessMessage:
    def test_valid_payload(self):
        result = process_message({"mqtt_topic": "spBv1.0/test", "payload": b"data"})
        assert result["processed"] is True
        assert result["topic"] == "spBv1.0/test"
        assert result["size"] == 4

    def test_empty_payload_raises(self):
        with pytest.raises(ValueError, match="Empty payload"):
            process_message({})

    def test_none_payload_raises(self):
        with pytest.raises(ValueError):
            process_message(None)

    def test_missing_topic(self):
        result = process_message({"payload": b"data"})
        assert result["topic"] == ""


class TestValidateTag:
    def test_valid_tag(self):
        assert validate_tag("EdgeData/Temperature", 42.0) is True

    def test_empty_name(self):
        assert validate_tag("", 1) is False

    def test_no_slash(self):
        assert validate_tag("Temperature", 1) is False

    def test_none_name(self):
        assert validate_tag(None, 1) is False
