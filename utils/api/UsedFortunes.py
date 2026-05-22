from __future__ import annotations
import sqlite3
import os
from datetime import datetime, date
from utils.classes.Fortune import Fortune
from utils.config import config

class UsedFortunes:
    """
    Storage class for used fortunes.
    Stored as list of fortunes in fortune_file.
    Each fortune has:
    created_at: datetime
    fortune: str
    mood: str
    """
    def __init__(self):
        self.db_path = config.db_storage.strip("/") + "/fortunes.db"
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._ensure_table()

    def _ensure_table(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS fortunes (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        mood       TEXT    NOT NULL,
                        result     TEXT,
                        created_at TEXT    NOT NULL
                   )"""
            )

    def _fortune_from_row(self, row: sqlite3.Row) -> Fortune:
        """Reconstruct a Fortune object from a database row."""
        return Fortune.from_row(row, self.db_path)


    def store_fortune(self, fortune: Fortune):
        fortune.save()

    def get_todays_fortunes(self):
        today = date.today().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM fortunes WHERE created_at LIKE ?",
                (f"{today}%",),
            ).fetchall()
        if not rows:
            return ""

        fortunes = [self._fortune_from_row(row) for row in rows]
        lines = ["\n\nAlready said today — do not repeat, rhyme with, or echo these:"]
        for fortune in fortunes:
            lines.append(f" - {fortune.result}")
        return "\n".join(lines)


