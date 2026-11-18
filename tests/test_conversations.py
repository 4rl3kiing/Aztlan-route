import os

import pytest

from aztlan_route.conversations import ConversationStore


def test_conversation_roundtrip_and_delete(tmp_path):
    database = tmp_path / "state" / "history.sqlite3"
    store = ConversationStore(database)
    conversation_id = store.create("qwen", "Architecture")
    store.add_message(conversation_id, "user", "Design the system")
    store.add_message(conversation_id, "assistant", "Use separated adapters")
    assert store.messages(conversation_id) == [
        ("user", "Design the system"),
        ("assistant", "Use separated adapters"),
    ]
    store.delete(conversation_id)
    assert store.messages(conversation_id) == []
    if os.name == "posix":
        assert database.stat().st_mode & 0o777 == 0o600
        assert database.parent.stat().st_mode & 0o777 == 0o700


def test_rejects_invalid_role_and_empty_message(tmp_path):
    store = ConversationStore(tmp_path / "history.db")
    conversation_id = store.create("qwen")
    with pytest.raises(ValueError):
        store.add_message(conversation_id, "root", "bad")
    with pytest.raises(ValueError):
        store.add_message(conversation_id, "user", " ")


def test_missing_conversation_raises_value_error(tmp_path):
    store = ConversationStore(tmp_path / "history.db")
    with pytest.raises(ValueError, match="does not exist"):
        store.add_message("missing", "user", "message")


@pytest.mark.parametrize("provider_id", ["x" * 65, "café", "../escape"])
def test_rejects_invalid_provider_id(tmp_path, provider_id):
    store = ConversationStore(tmp_path / "history.db")
    with pytest.raises(ValueError, match="provider id"):
        store.create(provider_id)
