from typing import Dict, List, Tuple
from app.core.models import Finding, FindingResult, ModuleResult, OverallVerdict, Verdict

# Configurable module weights representing empirical forensic reliability
MODULE_WEIGHTS = {
    "image_metadata": 1.0,
    "image_ela": 1.2,
    "image_splicing": 1.3,
    "video_frames": 1.3,
    "video_timestamps": 1.2,
    "audio_tamper": 1.2,
    "audio_deepfake": 1.1,
}

SEVERITY_SCORES = {
    FindingResult.TAMPERED: 1.0,
    FindingResult.SUSPICIOUS: 0.5,
    FindingResult.PASS: 0.0,
}


def compute_verdict(module_results: Dict[str, ModuleResult]) -> Verdict:
    """Combines multi-modal forensic module findings into a calibrated verdict and score.
    
    Adheres to the non-negotiable principle: All scores derive from deterministic,
    reproducible metrics. Forensic outputs are indicators with confidence, not legal certainty.
    """
    per_module_scores: Dict[str, float] = {}
    weighted_scores_sum = 0.0
    total_weights = 0.0

    all_findings: List[Tuple[Finding, str]] = []
    has_applicable_findings = False

    for mod_name, mod_result in module_results.items():
        weight = MODULE_WEIGHTS.get(mod_name, 1.0)
        mod_score_sum = 0.0
        mod_conf_sum = 0.0

        for f in mod_result.findings:
            if f.result in (FindingResult.NOT_APPLICABLE, FindingResult.INCONCLUSIVE):
                continue

            has_applicable_findings = True
            all_findings.append((f, mod_name))
            sev = SEVERITY_SCORES.get(f.result, 0.0)
            mod_score_sum += sev * f.confidence * 100.0
            mod_conf_sum += f.confidence

        if mod_conf_sum > 0:
            m_score = mod_score_sum / mod_conf_sum
            per_module_scores[mod_name] = round(m_score, 1)
            weighted_scores_sum += m_score * weight
            total_weights += weight
        else:
            per_module_scores[mod_name] = 0.0

    overall_score = round(weighted_scores_sum / total_weights, 1) if total_weights > 0 else 0.0

    # Sort findings to isolate top human-readable reasons (TAMPERED first, then SUSPICIOUS)
    def rank_finding(item: Tuple[Finding, str]) -> float:
        f, _ = item
        if f.result == FindingResult.TAMPERED:
            return 2.0 + f.confidence
        if f.result == FindingResult.SUSPICIOUS:
            return 1.0 + f.confidence
        return 0.0

    all_findings.sort(key=rank_finding, reverse=True)

    top_reasons = []
    tampered_count = 0
    suspicious_count = 0

    for f, mod in all_findings:
        if f.result == FindingResult.TAMPERED:
            tampered_count += 1
            if len(top_reasons) < 3:
                top_reasons.append(f"[{f.module.upper()}] {f.explanation}")
        elif f.result == FindingResult.SUSPICIOUS:
            suspicious_count += 1
            if len(top_reasons) < 3:
                top_reasons.append(f"[{f.module.upper()}] {f.explanation}")

    # If few or no anomalies, include verified authentic checks
    if len(top_reasons) < 3:
        for f, mod in all_findings:
            if f.result == FindingResult.PASS and len(top_reasons) < 3:
                top_reasons.append(f"[{f.module.upper()}] {f.explanation}")

    if not top_reasons:
        top_reasons.append("No active indicators detected. Stream or container was inconclusive.")

    # Determine Overall Categorical Verdict
    if not has_applicable_findings:
        overall_verdict = OverallVerdict.INCONCLUSIVE
    elif tampered_count > 0 or overall_score >= 60.0:
        overall_verdict = OverallVerdict.LIKELY_TAMPERED
    elif suspicious_count > 0 or overall_score >= 30.0:
        overall_verdict = OverallVerdict.SUSPICIOUS
    else:
        overall_verdict = OverallVerdict.AUTHENTIC

    return Verdict(
        overall=overall_verdict,
        score=overall_score,
        top_reasons=top_reasons[:3],
        per_module_scores=per_module_scores,
    )
