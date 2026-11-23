import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.core.models import Case, EvidenceFile, FileStatus, MediaType, Verdict, ModuleResult


class CaseStore:
    """Manages case metadata and evidence file persistence in SQLite with BSA 2023 Section 63 support."""

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
                    case_reference TEXT NOT NULL,
                    bsa_data TEXT
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
                    auto_purge INTEGER DEFAULT 0,
                    is_forward_simulation INTEGER DEFAULT 0,
                    forward_source_hash TEXT,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_case ON evidence_files(case_id);")

            # Backward-compatible migrations for existing local databases
            migrations = [
                ("cases", "bsa_data", "TEXT"),
                ("evidence_files", "auto_purge", "INTEGER DEFAULT 0"),
                ("evidence_files", "is_forward_simulation", "INTEGER DEFAULT 0"),
                ("evidence_files", "forward_source_hash", "TEXT"),
            ]
            for table, col, col_type in migrations:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
                except sqlite3.OperationalError:
                    # Column already exists
                    pass

            conn.commit()

    def create_case(
        self,
        investigator_name: str,
        case_reference: str,
        case_id: Optional[str] = None,
        offense_type: Optional[str] = None,
        requestor_name: Optional[str] = None,
        authority_basis: Optional[str] = None,
        examination_scope: Optional[str] = None,
        producer_name: Optional[str] = None,
        parentage_and_address: Optional[str] = None,
        device_source_type: Optional[str] = None,
        make_and_model: Optional[str] = None,
        color: Optional[str] = None,
        serial_or_imei: Optional[str] = None,
        lawful_control_role: Optional[str] = None,
        seized_at_ist: Optional[str] = None,
        seizure_location: Optional[str] = None,
        collection_method: Optional[str] = None,
        expert_name: Optional[str] = None,
        expert_designation: Optional[str] = None,
        lab_organization: Optional[str] = None,
    ) -> Case:
        assigned_id = case_id.strip() if case_id and case_id.strip() else str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        bsa_dict = {
            "offense_type": offense_type or "Suspected Digital Document / Media Tampering",
            "requestor_name": requestor_name or investigator_name,
            "authority_basis": authority_basis or "Station Diary Entry / Seizure Memo",
            "examination_scope": examination_scope or "Verification of authenticity, metadata integrity & temporal continuity",
            "producer_name": producer_name or "Not Specified",
            "parentage_and_address": parentage_and_address or "Not Specified",
            "device_source_type": device_source_type or "Mobile",
            "make_and_model": make_and_model or "Unspecified Device",
            "color": color or "Black",
            "serial_or_imei": serial_or_imei or "SN/IMEI: Not Disclosed",
            "lawful_control_role": lawful_control_role or "Owned",
            "seized_at_ist": seized_at_ist,
            "seizure_location": seizure_location,
            "collection_method": collection_method or "Direct Logical Copy",
            "expert_name": expert_name or "Dr. A. K. Sharma",
            "expert_designation": expert_designation or "Senior Scientific Officer (Digital Forensics)",
            "lab_organization": lab_organization or "State Cyber Forensic Laboratory / CCSU Bihar Police",
        }

        case = Case(
            case_id=assigned_id,
            created_at=created_at,
            investigator_name=investigator_name,
            case_reference=case_reference,
            **bsa_dict,
            files=[],
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cases (case_id, created_at, investigator_name, case_reference, bsa_data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    case.case_id,
                    case.created_at,
                    case.investigator_name,
                    case.case_reference,
                    json.dumps(bsa_dict),
                ),
            )
            conn.commit()
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT case_id, created_at, investigator_name, case_reference, bsa_data FROM cases WHERE case_id = ?",
                (case_id,),
            )
            case_row = cursor.fetchone()
            if not case_row:
                return None

            cursor.execute(
                "SELECT * FROM evidence_files WHERE case_id = ? ORDER BY uploaded_at ASC",
                (case_id,),
            )
            file_rows = cursor.fetchall()
            files: List[EvidenceFile] = []
            for fr in file_rows:
                results_data = json.loads(fr["results"]) if fr["results"] else None
                verdict_data = json.loads(fr["verdict"]) if fr["verdict"] else None
                
                # Check for columns safely
                auto_purge_val = bool(fr["auto_purge"]) if "auto_purge" in fr.keys() else False
                is_fwd_val = bool(fr["is_forward_simulation"]) if "is_forward_simulation" in fr.keys() else False
                fwd_hash = fr["forward_source_hash"] if "forward_source_hash" in fr.keys() else None

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
                        auto_purge=auto_purge_val,
                        is_forward_simulation=is_fwd_val,
                        forward_source_hash=fwd_hash,
                        results=results_data,
                        verdict=verdict_data,
                    )
                )

            bsa_extra: Dict[str, Any] = {}
            if "bsa_data" in case_row.keys() and case_row["bsa_data"]:
                try:
                    bsa_extra = json.loads(case_row["bsa_data"])
                except Exception:
                    pass

            return Case(
                case_id=case_row["case_id"],
                created_at=case_row["created_at"],
                investigator_name=case_row["investigator_name"],
                case_reference=case_row["case_reference"],
                **bsa_extra,
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
                    status, uploaded_at, results, verdict, auto_purge,
                    is_forward_simulation, forward_source_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    1 if file.auto_purge else 0,
                    1 if file.is_forward_simulation else 0,
                    file.forward_source_hash,
                ),
            )
            conn.commit()
        return file

    def update_file(
        self,
        case_id: str,
        file_id: str,
        status: Optional[FileStatus] = None,
        results: Optional[Dict[str, Any]] = None,
        verdict: Optional[Verdict] = None,
        sha256_at_report: Optional[str] = None,
    ):
        updates = []
        params = []
        if status:
            updates.append("status = ?")
            params.append(status.value)
        if results is not None:
            updates.append("results = ?")
            params.append(json.dumps(results))
        if verdict is not None:
            updates.append("verdict = ?")
            params.append(json.dumps(verdict.model_dump()))
        if sha256_at_report is not None:
            updates.append("sha256_at_report = ?")
            params.append(sha256_at_report)

        if not updates:
            return

        params.extend([case_id, file_id])
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE evidence_files SET {', '.join(updates)} WHERE case_id = ? AND file_id = ?"
            cursor.execute(query, params)
            conn.commit()


case_store = CaseStore()
