"""
Session Store — SQLite-backed memory for persisting pipeline results across sessions.
Enables returning sessions to diff against prior gap analyses.
"""

import json
import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src import config

logger = logging.getLogger(__name__)


class SessionStore:
    """SQLite-backed session storage for Placement Prep Agent."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        # Ensure the directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    session_name TEXT,
                    company TEXT,
                    role TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    jd_raw TEXT,
                    resume_raw TEXT,
                    jd_parsed TEXT,
                    resume_parsed TEXT,
                    gap_analysis TEXT,
                    practice_set TEXT,
                    interview_questions TEXT,
                    overall_score INTEGER
                )
            """)
            conn.commit()
            logger.info(f"[SESSION_STORE] Database initialized at {self.db_path}")
        finally:
            conn.close()

    def save_session(
        self,
        company: str,
        role: str,
        jd_raw: str,
        resume_raw: str,
        jd_parsed: dict,
        resume_parsed: dict,
        gap_analysis: dict,
        practice_set: dict,
        interview_questions: dict,
        overall_score: int,
        session_name: Optional[str] = None,
    ) -> str:
        """
        Save a complete pipeline result as a session.

        Returns:
            The session UUID.
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        name = session_name or f"{company} — {role} ({datetime.now().strftime('%b %d')})"

        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO sessions 
                (id, session_name, company, role, created_at, updated_at,
                 jd_raw, resume_raw, jd_parsed, resume_parsed,
                 gap_analysis, practice_set, interview_questions, overall_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, name, company, role, now, now,
                    jd_raw, resume_raw,
                    json.dumps(jd_parsed),
                    json.dumps(resume_parsed),
                    json.dumps(gap_analysis),
                    json.dumps(practice_set),
                    json.dumps(interview_questions),
                    overall_score,
                ),
            )
            conn.commit()
            logger.info(f"[SESSION_STORE] Saved session '{name}' (id={session_id[:8]}...)")
        finally:
            conn.close()

        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Load a session by ID."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if row:
                return self._row_to_dict(row)
            return None
        finally:
            conn.close()

    def find_prior_session(self, company: str) -> Optional[dict]:
        """
        Find the most recent prior session for a given company.
        This enables session memory — returning sessions can diff against prior runs.
        """
        conn = self._get_conn()
        try:
            row = conn.execute(
                """
                SELECT * FROM sessions 
                WHERE LOWER(company) = LOWER(?) 
                ORDER BY updated_at DESC 
                LIMIT 1
                """,
                (company,),
            ).fetchone()
            if row:
                logger.info(f"[SESSION_STORE] Found prior session for company '{company}'")
                return self._row_to_dict(row)
            logger.info(f"[SESSION_STORE] No prior session found for company '{company}'")
            return None
        finally:
            conn.close()

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions, most recent first."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT id, session_name, company, role, created_at, 
                       updated_at, overall_score
                FROM sessions 
                ORDER BY updated_at DESC 
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE id = ?", (session_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"[SESSION_STORE] Deleted session {session_id[:8]}...")
            return deleted
        finally:
            conn.close()

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a database row to a dict with parsed JSON fields."""
        d = dict(row)
        # Parse JSON blob fields
        for field in ("jd_parsed", "resume_parsed", "gap_analysis", "practice_set", "interview_questions"):
            if d.get(field):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d
