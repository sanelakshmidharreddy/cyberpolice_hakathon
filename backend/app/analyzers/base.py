import time
import traceback
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from app.core.models import Finding, FindingResult, MediaType, ModuleResult


class BaseAnalyzer(ABC):
    """Abstract Base Class for all FORGE forensic analysis engines."""

    name: str = "base_analyzer"
    version: str = "1.0.0"
    supported_media: List[MediaType] = [MediaType.IMAGE]

    def execute(self, file_path: Path, case_id: str, file_id: str) -> ModuleResult:
        """Executes analyzer with timing, exception containment, and typed ModuleResult."""
        start_time = time.perf_counter()
        findings: List[Finding] = []
        error: Optional[str] = None

        try:
            findings = self.analyze(file_path, case_id, file_id)
        except Exception as exc:
            error = f"Analyzer failure in {self.name}: {str(exc)}"
            # Return inconclusive finding on unhandled failure without crashing pipeline
            findings.append(
                Finding(
                    module=self.name,
                    check_name=f"{self.name}_execution",
                    result=FindingResult.INCONCLUSIVE,
                    confidence=0.5,
                    explanation=f"Execution halted due to unexpected error: {str(exc)}",
                    evidence={"traceback": traceback.format_exc()},
                )
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return ModuleResult(
            module=self.name,
            version=self.version,
            duration_ms=round(duration_ms, 2),
            findings=findings,
            error=error,
        )

    @abstractmethod
    def analyze(self, file_path: Path, case_id: str, file_id: str) -> List[Finding]:
        """Core analytical implementation to be overridden by subclasses."""
        pass
