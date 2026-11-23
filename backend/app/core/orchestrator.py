import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.analyzers.base import BaseAnalyzer
from app.analyzers.image_metadata import ImageMetadataAnalyzer
from app.analyzers.image_ela import ImageELAAnalyzer
from app.analyzers.image_splicing import ImageSplicingAnalyzer
from app.analyzers.video_frames import VideoFramesAnalyzer
from app.analyzers.video_timestamps import VideoTimestampsAnalyzer
from app.analyzers.audio_tamper import AudioTamperAnalyzer
from app.analyzers.audio_deepfake import AudioDeepfakeAnalyzer
from app.core.audit import audit_logger
from app.core.case_store import case_store
from app.core.models import FileStatus, Finding, FindingResult, MediaType, ModuleResult, Verdict
from app.core.scoring import compute_verdict
from app.core.storage import storage

logger = logging.getLogger("forge.orchestrator")

# In-memory real-time module status registry: status_map[file_id][module_name] = status_str
_module_status_registry: Dict[str, Dict[str, str]] = {}

# Render Free Tier concurrency guard (512 MB RAM limit): Ensure only 1 forensic analysis pipeline executes at a time
_analysis_semaphore = asyncio.Semaphore(1)


def get_analyzers_for_media(media_type: MediaType) -> List[BaseAnalyzer]:
    """Selects the suite of forensic engines corresponding to media modality."""
    if media_type == MediaType.IMAGE:
        return [ImageMetadataAnalyzer(), ImageELAAnalyzer(), ImageSplicingAnalyzer()]
    elif media_type == MediaType.VIDEO:
        return [VideoFramesAnalyzer(), VideoTimestampsAnalyzer()]
    elif media_type == MediaType.AUDIO:
        return [AudioTamperAnalyzer(), AudioDeepfakeAnalyzer()]
    return []


def get_live_status(file_id: str) -> Dict[str, str]:
    """Returns real-time progress map for all modules assigned to an evidence file."""
    return _module_status_registry.get(file_id, {})


def _run_single_module(analyzer: BaseAnalyzer, working_path: Path, case_id: str, file_id: str) -> ModuleResult:
    """Worker function executed inside thread pool."""
    _module_status_registry.setdefault(file_id, {})[analyzer.name] = "running"
    try:
        res = analyzer.execute(working_path, case_id, file_id)
        _module_status_registry[file_id][analyzer.name] = "done"
        return res
    except Exception as exc:
        _module_status_registry[file_id][analyzer.name] = "failed"
        logger.exception(f"Fatal error in module {analyzer.name}: {exc}")
        return ModuleResult(
            module=analyzer.name,
            version=analyzer.version,
            findings=[
                Finding(
                    module=analyzer.name,
                    check_name="execution",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Module crashed: {str(exc)}",
                )
            ],
            error=str(exc),
        )


def analyze_evidence_file_sync(case_id: str, file_id: str):
    """Orchestrates forensic analysis over working copy with thread pool parallelism."""
    case = case_store.get_case(case_id)
    if not case:
        logger.error(f"Cannot analyze: case {case_id} not found.")
        return

    ev_file = next((f for f in case.files if f.file_id == file_id), None)
    if not ev_file:
        logger.error(f"Cannot analyze: file {file_id} not found in case {case_id}.")
        return

    analyzers = get_analyzers_for_media(ev_file.media_type)
    if not analyzers:
        case_store.update_file(case_id, file_id, status=FileStatus.DONE)
        return

    # Mark status as RUNNING
    case_store.update_file(case_id, file_id, status=FileStatus.RUNNING)
    for a in analyzers:
        _module_status_registry.setdefault(file_id, {})[a.name] = "queued"

    audit_logger.log(
        case_id=case_id,
        file_id=file_id,
        action="ANALYSIS_STARTED",
        actor="system",
        details={"modules": [a.name for a in analyzers], "media_type": ev_file.media_type.value},
        sha256=ev_file.sha256_at_upload,
    )

    # RULE: Never modify the uploaded original file. Work on copies.
    working_copy = storage.get_working_copy(ev_file.storage_path, case_id, file_id)

    module_results: Dict[str, ModuleResult] = {}
    timeout = settings.MODULE_TIMEOUT_SECONDS

    start_all = time.perf_counter()
    # Bound worker threads to 2 to conserve memory on Render 512 MB tier
    with ThreadPoolExecutor(max_workers=min(2, len(analyzers))) as executor:
        futures = {
            executor.submit(_run_single_module, analyzer, working_copy, case_id, file_id): analyzer
            for analyzer in analyzers
        }

        for fut in futures:
            analyzer = futures[fut]
            try:
                result = fut.result(timeout=timeout)
                module_results[analyzer.name] = result
            except FutureTimeout:
                _module_status_registry[file_id][analyzer.name] = "failed"
                logger.error(f"Module {analyzer.name} timed out after {timeout}s.")
                module_results[analyzer.name] = ModuleResult(
                    module=analyzer.name,
                    version=analyzer.version,
                    findings=[
                        Finding(
                            module=analyzer.name,
                            check_name="timeout",
                            result=FindingResult.INCONCLUSIVE,
                            confidence=0.5,
                            explanation=f"Analysis timed out after {timeout} seconds.",
                        )
                    ],
                    error="Timeout exceeded",
                )
            except Exception as e:
                _module_status_registry[file_id][analyzer.name] = "failed"
                logger.exception(f"Unexpected executor exception in {analyzer.name}: {e}")
                module_results[analyzer.name] = ModuleResult(
                    module=analyzer.name,
                    version=analyzer.version,
                    error=str(e),
                )

    total_duration_ms = (time.perf_counter() - start_all) * 1000.0

    # Calculate calibrated multi-modal forensic verdict
    verdict = compute_verdict(module_results)

    # Clean working copy from scratch space
    storage.cleanup_scratch(case_id)

    # Persist results in store
    results_serialized = {k: v.model_dump() for k, v in module_results.items()}
    case_store.update_file(
        case_id=case_id,
        file_id=file_id,
        status=FileStatus.DONE,
        results=results_serialized,
        verdict=verdict,
    )

    audit_logger.log(
        case_id=case_id,
        file_id=file_id,
        action="ANALYSIS_COMPLETED",
        actor="system",
        details={
            "duration_ms": round(total_duration_ms, 2),
            "verdict": verdict.overall.value,
            "score": verdict.score,
            "top_reasons": verdict.top_reasons,
        },
        sha256=ev_file.sha256_at_upload,
    )

    # Privacy Auto-Purge: Securely purge raw file if requested after analysis & artifacts are saved
    if ev_file.auto_purge:
        try:
            raw_path = storage.get_evidence_path(ev_file.storage_path)
            if raw_path.exists():
                import stat
                raw_path.chmod(stat.S_IWRITE)
                raw_path.unlink()
                audit_logger.log(
                    case_id=case_id,
                    file_id=file_id,
                    action="RAW_FILE_PURGED",
                    actor="FORGE Privacy Engine",
                    details={"reason": "Auto-purge enabled by user; raw file securely unlinked while preserving hashes & metrics."},
                    sha256=ev_file.sha256_at_upload,
                )
                logger.info(f"Auto-purged raw evidence file {ev_file.original_name} for case {case_id}")
        except Exception as purge_err:
            logger.warning(f"Failed to auto-purge raw evidence file: {purge_err}")


async def run_analysis_background(case_id: str, file_id: str):
    """Asynchronous wrapper for background execution protected by semaphore."""
    async with _analysis_semaphore:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, analyze_evidence_file_sync, case_id, file_id)
