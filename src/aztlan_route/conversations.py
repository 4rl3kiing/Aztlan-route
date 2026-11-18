"""Local SQLite conversation history; authentication material is never stored here."""
from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

from .identifiers import validate_identifier


class ConversationStore:
    def __init__(self, database: Path) -> None:
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            self.database.parent.chmod(0o700)
        self._initialize()
        if os.name == "posix":
            self.database.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    provider_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def create(self, provider_id: str, title: str = "New conversation") -> str:
        validate_identifier(provider_id, label="provider id")
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError("Title must contain 1 to 200 characters")
        conversation_id = str(uuid.uuid4())
        with self._connect() as db:
            db.execute(
                "INSERT INTO conversations(id, provider_id, title) VALUES (?, ?, ?)",
                (conversation_id, provider_id, title),
            )
        return conversation_id

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        if not isinstance(role, str) or role not in {"user", "assistant", "system"}:
            raise ValueError("Invalid message role")
        if not isinstance(content, str) or not content.strip() or len(content) > 1_000_000:
            raise ValueError("Message must contain 1 to 1000000 characters")
        with self._connect() as db:
            exists = db.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if exists is None:
                raise ValueError("Conversation does not exist")
            db.execute(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )

    def messages(self, conversation_id: str) -> list[tuple[str, str]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            ).fetchall()
        return [(role, content) for role, content in rows]

    def delete(self, conversation_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
