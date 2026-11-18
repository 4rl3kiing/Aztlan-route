import pytest

from aztlan_route.conversations import ConversationStore


def test_conversation_roundtrip_and_delete(tmp_path):
    store = ConversationStore(tmp_path / "state" / "history.sqlite3")
    conversation_id = store.create("qwen", "Architecture")
    store.add_message(conversation_id, "user", "Design the system")
    store.add_message(conversation_id, "assistant", "Use separated adapters")
    assert store.messages(conversation_id) == [
        ("user", "Design the system"),
        ("assistant", "Use separated adapters"),
    ]
    store.delete(conversation_id)
    assert store.messages(conversation_id) == []


def test_rejects_invalid_role_and_empty_message(tmp_path):
    store = ConversationStore(tmp_path / "history.db")
    conversation_id = store.create("qwen")
    with pytest.raises(ValueError):
        store.add_message(conversation_id, "root", "bad")
    with pytest.raises(ValueError):
        store.add_message(conversation_id, "user", " ")
