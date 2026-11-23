import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.models import AuditEntry

logger = logging.getLogger("forge.audit")


class AuditLogger:
    """Append-only audit trail logger for forensic chain of custody."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _init_db(self):
        """Initializes SQLite audit table if not existing."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    file_id TEXT,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details TEXT NOT NULL,
                    sha256 TEXT
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_logs(case_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_file ON audit_logs(file_id);")
            conn.commit()

    def log(
        self,
        case_id: str,
        action: str,
        file_id: Optional[str] = None,
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
        sha256: Optional[str] = None,
    ) -> AuditEntry:
        """Appends an immutable audit entry."""
        now_iso = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details or {})

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_logs (timestamp_utc, case_id, file_id, action, actor, details, sha256)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (now_iso, case_id, file_id, action, actor, details_json, sha256),
            )
            entry_id = cursor.lastrowid
            conn.commit()

        entry = AuditEntry(
            id=entry_id,
            timestamp_utc=now_iso,
            case_id=case_id,
            file_id=file_id,
            action=action,
            actor=actor,
            details=details or {},
            sha256=sha256,
        )
        logger.info(f"AUDIT [{action}] case={case_id} file={file_id} sha256={sha256}")
        return entry

    def get_case_audit_trail(self, case_id: str) -> List[AuditEntry]:
        """Fetches chronological audit trail for a case."""
        entries: List[AuditEntry] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, timestamp_utc, case_id, file_id, action, actor, details, sha256 FROM audit_logs WHERE case_id = ? ORDER BY id ASC",
                (case_id,),
            )
            for row in cursor.fetchall():
                entries.append(
                    AuditEntry(
                        id=row["id"],
                        timestamp_utc=row["timestamp_utc"],
                        case_id=row["case_id"],
                        file_id=row["file_id"],
                        action=row["action"],
                        actor=row["actor"],
                        details=json.loads(row["details"]),
                        sha256=row["sha256"],
                    )
                )
        return entries


# Global singleton instance
audit_logger = AuditLogger()
