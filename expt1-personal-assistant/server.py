"""
Expt 1: The "Personal Assistant" Memory Server
MCP server exposing save_note / search_notes tools backed by a local SQLite database.
"""
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.db")

mcp = FastMCP("Personal Assistant")


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_FILE)


def _init_db() -> None:
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


_init_db()


@mcp.tool()
def save_note(content: str, tags: Optional[List[str]] = None) -> str:
    """Save a new note to persistent memory (CREATE).

    Args:
        content: The text of the note to remember.
        tags: Optional list of tags to categorize the note (e.g. ["work", "deadline"]).
    """
    tags = tags or []
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO notes (content, tags, created_at) VALUES (?, ?, ?)",
        (content, ",".join(tags), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    note_id = cur.lastrowid
    conn.close()
    return f"Saved note #{note_id}: \"{content}\" (tags: {', '.join(tags) or 'none'})"


@mcp.tool()
def search_notes(query: str) -> str:
    """Search saved notes by keyword, matching against note content or tags (READ).

    Args:
        query: The search term to look for.
    """
    conn = _get_conn()
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT id, content, tags, created_at FROM notes "
        "WHERE content LIKE ? OR tags LIKE ? ORDER BY id",
        (like, like),
    ).fetchall()
    conn.close()

    if not rows:
        return f"No notes found matching '{query}'."

    lines = [f"Found {len(rows)} note(s) matching '{query}':"]
    for note_id, content, tags, created_at in rows:
        tag_str = f" [{tags}]" if tags else ""
        lines.append(f"- #{note_id} ({created_at[:10]}){tag_str}: {content}")
    return "\n".join(lines)


@mcp.tool()
def list_notes() -> str:
    """List all saved notes (READ)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, content, tags, created_at FROM notes ORDER BY id"
    ).fetchall()
    conn.close()
    if not rows:
        return "No notes have been saved yet."
    lines = [f"{len(rows)} note(s):"]
    for note_id, content, tags, created_at in rows:
        tag_str = f" [{tags}]" if tags else ""
        lines.append(f"- #{note_id} ({created_at[:10]}){tag_str}: {content}")
    return "\n".join(lines)


@mcp.tool()
def delete_note(note_id: int) -> str:
    """Delete a note by its id (DELETE).

    Args:
        note_id: The numeric id of the note to delete.
    """
    conn = _get_conn()
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted:
        return f"Deleted note #{note_id}."
    return f"No note found with id #{note_id}."


if __name__ == "__main__":
    mcp.run()
