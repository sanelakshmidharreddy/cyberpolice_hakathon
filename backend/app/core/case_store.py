import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from app.config import settings
from app.core.models import Case, EvidenceFile, FileStatus, MediaType, Verdict, ModuleResult


class CaseStore:
    """Manages case metadata and evidence file persistence in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    investigator_name TEXT NOT NULL,
                    case_reference TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evidence_files (
                    file_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    mime TEXT NOT NULL,
                    sha256_at_upload TEXT NOT NULL,
                    sha256_at_report TEXT,
                    storage_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    results TEXT,
                    verdict TEXT,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_case ON evidence_files(case_id);")
            conn.commit()

    def create_case(self, investigator_name: str, case_reference: str) -> Case:
        case = Case(
            case_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            investigator_name=investigator_name,
            case_reference=case_reference,
            files=[],
        )
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO cases (case_id, created_at, investigator_name, case_reference) VALUES (?, ?, ?, ?)",
                (case.case_id, case.created_at, case.investigator_name, case.case_reference),
            )
            conn.commit()
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT case_id, created_at, investigator_name, case_reference FROM cases WHERE case_id = ?", (case_id,))
            case_row = cursor.fetchone()
            if not case_row:
                return None

            cursor.execute("SELECT * FROM evidence_files WHERE case_id = ? ORDER BY uploaded_at ASC", (case_id,))
            file_rows = cursor.fetchall()
            files: List[EvidenceFile] = []
            for fr in file_rows:
                results_data = json.loads(fr["results"]) if fr["results"] else None
                verdict_data = json.loads(fr["verdict"]) if fr["verdict"] else None
                files.append(
                    EvidenceFile(
                        file_id=fr["file_id"],
                        original_name=fr["original_name"],
                        media_type=MediaType(fr["media_type"]),
                        size_bytes=fr["size_bytes"],
                        mime=fr["mime"],
                        sha256_at_upload=fr["sha256_at_upload"],
                        sha256_at_report=fr["sha256_at_report"],
                        storage_path=fr["storage_path"],
                        status=FileStatus(fr["status"]),
                        uploaded_at=fr["uploaded_at"],
                        results=results_data,
                        verdict=verdict_data,
                    )
                )

            return Case(
                case_id=case_row["case_id"],
                created_at=case_row["created_at"],
                investigator_name=case_row["investigator_name"],
                case_reference=case_row["case_reference"],
                files=files,
            )

    def list_cases(self) -> List[Case]:
        cases: List[Case] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT case_id FROM cases ORDER BY created_at DESC")
            rows = cursor.fetchall()
            for r in rows:
                c = self.get_case(r["case_id"])
                if c:
                    cases.append(c)
        return cases

    def add_file(self, case_id: str, file: EvidenceFile) -> EvidenceFile:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evidence_files (
                    file_id, case_id, original_name, media_type, size_bytes,
                    mime, sha256_at_upload, sha256_at_report, storage_path,
                    status, uploaded_at, results, verdict
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file.file_id,
                    case_id,
                    file.original_name,
                    file.media_type.value,
                    file.size_bytes,
                    file.mime,
                    file.sha256_at_upload,
                    file.sha256_at_report,
                    file.storage_path,
                    file.status.value,
                    file.uploaded_at,
                    json.dumps(file.results) if file.results else None,
                    json.dumps(file.verdict.model_dump()) if file.verdict else None,
                ),
            )
            conn.commit()
        return file

    def update_file(
        self,
        case_id: str,
        file_id: str,
        status: Optional[FileStatus] = None,
        sha256_at_report: Optional[str] = None,
        results: Optional[dict] = None,
        verdict: Optional[Verdict] = None,
    ):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            if status is not None:
                updates.append("status = ?")
                params.append(status.value)
            if sha256_at_report is not None:
                updates.append("sha256_at_report = ?")
                params.append(sha256_at_report)
            if results is not None:
                updates.append("results = ?")
                params.append(json.dumps(results))
            if verdict is not None:
                updates.append("verdict = ?")
                params.append(json.dumps(verdict.model_dump()))

            if updates:
                params.extend([case_id, file_id])
                sql = f"UPDATE evidence_files SET {', '.join(updates)} WHERE case_id = ? AND file_id = ?"
                cursor.execute(sql, params)
                conn.commit()


case_store = CaseStore()
