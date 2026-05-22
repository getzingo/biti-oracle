from __future__ import annotations
import json
import os
import time

import requests
import threading

from utils.api.client.MoodInstructions import MoodInstructions
from utils.api.hmac_sign_payload import sign_payload
import sqlite3
from datetime import datetime
from typing import Optional
from utils.config import config

class Fortune:
    def __init__(self, sensor_val: int = 0, mood: str = None) -> None:
        self.db_path = config.db_storage.strip("/") + "/fortunes.db"
        self.result: Optional[str] = None
        self.created_at = datetime.now()
        self.instructions = MoodInstructions()
        if sensor_val:
            self._derive_mood_from_sensor(sensor_val)
        elif mood:
            self.mood = mood
        else:
            self.mood = "gentle"
        self._id: Optional[int] = None
        self.fortune_ready = False
        self._thread: Optional[threading.Thread] = None
        self.source: str = "api"  # 'api' or 'fallback'

        try:
            self.api_url = config.oracle_api_server_url.rstrip("/") or os.getenv("ORACLE_API_SERVER_URL").rstrip("/")
            self.token = config.oracle_api_server_token or os.getenv("ORACLE_API_SERVER_TOKEN", "")
        except AttributeError as e:
            print(f"Api client not setup, pls configure url + token!: {e}")
            exit(2)

    def _derive_mood_from_sensor(self, sensor_val: int):
        match sensor_val:
            case x if x <= 20:
                self.mood = "gentle"
            case x if 20 < x <= 40:
                self.mood = "dramatic"
            case x if 40 < x <= 60:
                self.mood = "cynical"
            case x if 60 < x <= 80:
                self.mood = "chaotic"
            case _:
                self.mood = "obliterating"

    def _trigger_oracle_api(self, prompt:str) -> str:
        """
        Rest POST to trigger the oracle api, answers with json response.
        :param prompt: Full string block as instructions for llm
        :return: task_id from oracle api
        """
        payload = {"action": "oracle", "data": {"mood": prompt}}
        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sign_payload(payload_bytes)
        }
        r = requests.post(f"{self.api_url}", data=payload_bytes, headers=headers, timeout=(3, 10))
        r.raise_for_status()
        print(r.json(), flush=True)
        return r.json()["task_id"]

    def _build_prompt(self) -> str:
        return self.instructions.base_instructions + "\n" + getattr(self.instructions, self.mood)

    def _get_fortune_status(self, task_id):
        path = f"/status/{task_id}"
        headers = {
            "X-Hub-Signature-256": sign_payload(path.encode("utf-8"))
        }
        r = requests.get(f"{self.api_url}/status/{task_id}", headers=headers, timeout=(2, 5))
        r.raise_for_status()
        return r.json()

    def _wait_for_result(self, task_id: str, timeout: float = 60.0, interval: float = 2.0):
        """if successful returns result of the oracle, or with None if failed"""
        deadline = time.monotonic() + timeout

        while True:
            response_data = self._get_fortune_status(task_id)
            status = response_data.get("status")
            result = response_data.get("result")
            if status == "completed" and result:
                return result
            elif status == "failed":
                return None

            if time.monotonic() >= deadline:
                raise TimeoutError(f"{task_id} timed out waiting for response")
            time.sleep(interval)

    def add_fortune(self, reading: str) -> None:
        self.result = reading

    @property
    def is_stored(self) -> bool:
        return self._id is not None

    def save(self) -> int:
        """returns row id"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS fortunes (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        mood       TEXT    NOT NULL,
                        result     TEXT,
                        created_at TEXT    NOT NULL
                   )"""
            )
            if self._id is None:
                cur = conn.execute(
                    "INSERT INTO fortunes (mood, result, created_at) VALUES (?, ?, ?)",
                    (self.mood, self.result, self.created_at.isoformat()),
                )
                self._id = cur.lastrowid
            return self._id

    @classmethod
    def from_row(cls, row: sqlite3.Row, db_path: str) -> Fortune:
        f = cls(mood=row["mood"])
        f._id = row["id"]
        f.result = row["result"]
        f.created_at = datetime.fromisoformat(row["created_at"])
        return f

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "mood": self.mood,
            "result": self.result,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"Fortune(mood={self.mood!r}, result={self.result!r}, "
            f"ready={self.fortune_ready})"
        )

    def start_generation(self):
        """starts oracle api generation in bg daemon
        usage:
            fortune = Fortune(sensor_val=33)
            fortune.start_generation()
            if fortune.fortune_ready:
                print(fortune.result)
        """
        self._thread = threading.Thread(
            target=self._generations_and_store,
            daemon=True,
        )
        self._thread.start()


    def _fallback_from_db(self) -> Optional[str]:
        """Retrieve a random fortune from the database matching the current mood."""
        import random
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT result FROM fortunes WHERE mood = ? ORDER BY RANDOM() LIMIT 1",
                    (self.mood,)
                ).fetchall()
                if rows:
                    return rows[0]["result"]
                # If no mood match, try any fortune
                rows = conn.execute(
                    "SELECT result FROM fortunes ORDER BY RANDOM() LIMIT 1"
                ).fetchall()
                if rows:
                    return rows[0]["result"]
        except Exception as e:
            print(f"Fallback DB query failed: {e}")
        return None

    def _generations_and_store(self):
        try:
            task_id = self._trigger_oracle_api(self._build_prompt())
            result = self._wait_for_result(task_id)
            if result:
                print(f"[API] Fortune received: {result}")
                self.result = result
                self.source = "api"
        except Exception as e:
            print(f"[API] Fortune generation failed: {e}")
            print("[FALLBACK] Attempting to retrieve fortune from database...")
            fallback = self._fallback_from_db()
            if fallback:
                print(f"[FALLBACK] Fortune from DB: {fallback}")
                self.result = fallback
                self.source = "fallback"
            else:
                print("[FALLBACK] No fortunes available in database.")
                self.result = None
                self.source = "none"
        finally:
            self.fortune_ready = True
