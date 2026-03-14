import pytest
from pydantic import ValidationError
from app.schemas.common import EventCreate
from datetime import datetime

def test_validate_id_regex():
    """
    Test that IDs must match ^[a-zA-Z0-9_\\-]+$
    """
    valid_payload = {
        "type": "test.event",
        "actor": {"kind": "user", "id": "user_123-valid"},
        "entities": [{"kind": "item", "id": "item-456"}],
        "payload": {"foo": "bar"},
        "occurred_at": "2024-03-14T12:00:00Z",
        "idempotency_key": "key-1"
    }
    # Should pass
    EventCreate(**valid_payload)

    invalid_payload = valid_payload.copy()
    invalid_payload["actor"]["id"] = "user@123!" # Invalid chars
    
    with pytest.raises(ValidationError) as excinfo:
        EventCreate(**invalid_payload)
    assert "actor" in str(excinfo.value)

def test_validate_occurred_at_format():
    """
    Test that occurred_at must be a valid datetime (ISO-8601).
    Pydantic handles this partially, but we want to ensure it's strictly enforced.
    """
    payload = {
        "type": "test.event",
        "actor": {"kind": "user", "id": "u1"},
        "entities": [],
        "payload": {},
        "occurred_at": "not-a-date",
        "idempotency_key": "k1"
    }
    with pytest.raises(ValidationError):
        EventCreate(**payload)

def test_required_fields():
    """
    Test that missing required fields trigger validation errors.
    """
    incomplete_payload = {
        "type": "test.event",
        # actor missing
        "entities": [],
        "payload": {},
        "occurred_at": "2024-03-14T12:00:00Z",
        "idempotency_key": "k1"
    }
    with pytest.raises(ValidationError):
        EventCreate(**incomplete_payload)

def test_kind_and_type_constraints():
    """
    Test that 'type' and 'kind' have length constraints or allowed values.
    """
    payload = {
        "type": "", # Too short
        "actor": {"kind": "user", "id": "u1"},
        "entities": [],
        "payload": {},
        "occurred_at": "2024-03-14T12:00:00Z",
        "idempotency_key": "k1"
    }
    with pytest.raises(ValidationError):
        EventCreate(**payload)
