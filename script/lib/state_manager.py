# -*- coding: utf-8 -*-
"""
State Manager — centralized state read/write + silver locking.

Responsibilities:
1. Read/write domain state files (output/state/*.json)
2. Lock/unlock silver data after cutoff
3. Session tracking (open/close sessions)
"""
import os
import json
from datetime import datetime
from typing import Optional

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_DIR = os.path.join(BASE, "output", "state")
STORAGE_DIR = os.path.join(BASE, "output", "storage")


class DataLockError(Exception):
    """Raised when trying to write to locked silver data."""
    pass


class StateManager:
    """Manage state files and silver data locking."""

    def __init__(self):
        os.makedirs(STATE_DIR, exist_ok=True)

    # ── Silver Locking ──

    def is_locked(self, date_tag: str) -> bool:
        """Check if silver data for a date is locked."""
        lock_path = self._lock_path(date_tag)
        return os.path.exists(lock_path)

    def get_lock_info(self, date_tag: str) -> Optional[dict]:
        """Get lock metadata if locked, else None."""
        lock_path = self._lock_path(date_tag)
        if not os.path.exists(lock_path):
            return None
        with open(lock_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def lock_silver(self, date_tag: str, locked_by: str = "system", reason: str = "cutoff"):
        """Lock silver data — no more writes allowed."""
        lock_path = self._lock_path(date_tag)
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        lock_data = {
            "locked_at": datetime.now().isoformat(),
            "locked_by": locked_by,
            "reason": reason,
            "date_tag": date_tag,
        }
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
        print(f"  🔒 Silver locked: {date_tag} (by {locked_by}, reason: {reason})")

    def unlock_silver(self, date_tag: str):
        """Unlock silver data (admin override)."""
        lock_path = self._lock_path(date_tag)
        if os.path.exists(lock_path):
            os.remove(lock_path)
            print(f"  🔓 Silver unlocked: {date_tag}")

    def check_write_allowed(self, date_tag: str):
        """Raise DataLockError if silver is locked."""
        if self.is_locked(date_tag):
            info = self.get_lock_info(date_tag)
            raise DataLockError(
                f"Silver data for {date_tag} is locked since {info.get('locked_at')} "
                f"by {info.get('locked_by')} (reason: {info.get('reason')}). "
                f"Use --force to override."
            )

    def _lock_path(self, date_tag: str) -> str:
        return os.path.join(STORAGE_DIR, "silver", date_tag, "lock.json")

    # ── Silver Reading ──

    def read_silver(self, date_tag: str, extractor_name: str) -> Optional[dict]:
        """Read silver data for a specific extractor+date. Returns None if not found."""
        silver_path = os.path.join(STORAGE_DIR, "silver", date_tag, f"{extractor_name}.json")
        if not os.path.exists(silver_path):
            return None
        with open(silver_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def has_silver(self, date_tag: str) -> bool:
        """Check if silver directory exists and has data."""
        silver_dir = os.path.join(STORAGE_DIR, "silver", date_tag)
        if not os.path.exists(silver_dir):
            return False
        files = [f for f in os.listdir(silver_dir) if f.endswith(".json") and f != "lock.json"]
        return len(files) > 0

    # ── Domain State ──

    def read_state(self, filename: str) -> Optional[dict]:
        """Read a state file from output/state/."""
        path = os.path.join(STATE_DIR, filename)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_state(self, filename: str, data: dict):
        """Write a state file to output/state/."""
        path = os.path.join(STATE_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Session Tracking ──

    def open_session(self, task_id: str) -> dict:
        """Create a new session record."""
        import uuid
        session = {
            "session_id": str(uuid.uuid4())[:8],
            "task_id": task_id,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "steps": [],
        }
        self._save_session(session)
        print(f"  📋 Session opened: {session['session_id']} ({task_id})")
        return session

    def log_step(self, session: dict, step_name: str, status: str = "done", detail: str = ""):
        """Log a step in the session."""
        session["steps"].append({
            "name": step_name,
            "status": status,
            "at": datetime.now().isoformat(),
            "detail": detail,
        })
        self._save_session(session)

    def close_session(self, session: dict, status: str = "success", error: str = ""):
        """Close a session — finalize."""
        session["ended_at"] = datetime.now().isoformat()
        session["status"] = status
        if error:
            session["error"] = error
        # Calculate duration
        start = datetime.fromisoformat(session["started_at"])
        end = datetime.fromisoformat(session["ended_at"])
        session["duration_sec"] = round((end - start).total_seconds(), 1)
        self._save_session(session)
        emoji = "✅" if status == "success" else "❌"
        print(f"  {emoji} Session closed: {session['session_id']} ({status}, {session['duration_sec']}s)")

    def _save_session(self, session: dict):
        """Persist session to sessions.json (append/update)."""
        sessions_path = os.path.join(STATE_DIR, "sessions.json")
        sessions = []
        if os.path.exists(sessions_path):
            with open(sessions_path, "r", encoding="utf-8") as f:
                sessions = json.load(f)

        # Update existing or append
        found = False
        for i, s in enumerate(sessions):
            if s.get("session_id") == session["session_id"]:
                sessions[i] = session
                found = True
                break
        if not found:
            sessions.append(session)

        # Keep last 100 sessions
        sessions = sessions[-100:]

        with open(sessions_path, "w", encoding="utf-8") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
