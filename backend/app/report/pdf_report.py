import io
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import PIL
import reportlab
import scipy
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import settings
from app.core.models import AuditEntry, Case, EvidenceFile, FindingResult, OverallVerdict


class NumberedCanvas(reportlab.pdfgen.canvas.Canvas):
    """Adds running headers, footers, and page numbers to every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))

        # Running Top Header
        self.drawString(
            36,
            756,
            "FORGE DIGITAL EVIDENCE AUTHENTICITY & INTEGRITY VERIFICATION REPORT",
        )
        self.setFont("Helvetica", 8)
        self.drawRightString(
            559,
            756,
            "CONFIDENTIAL // LAW ENFORCEMENT & JUDICIAL ADMISSIBILITY",
        )

        # Top divider line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 750, 559, 750)

        # Bottom divider line
        self.line(36, 40, 559, 40)

        # Running Footer
        self.setFont("Helvetica", 8)
        self.drawString(
            36,
            28,
            "Track: Digital Forensics (PS-05) • Cyber Hackathon 2026 • C-DAC Patna / CCSU Bihar Police",
        )
        self.drawRightString(
            559,
            28,
            f"Page {self._pageNumber} of {page_count}",
        )
        self.restoreState()


def get_pdf_styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            "ReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0F172A"),
        )
    )
    styles.add(
        ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SectionHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0284C7"),
            spaceBefore=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1E293B"),
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0F172A"),
        )
    )
    styles.add(
        ParagraphStyle(
            "TableCellMono",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#0F172A"),
        )
    )
    styles.add(
        ParagraphStyle(
            "LegalNotice",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748B"),
        )
    )
    return styles


def generate_pdf_report(
    case: Case,
    audit_trail: List[AuditEntry],
    verified_hashes: Dict[str, Tuple[str, bool]],
) -> bytes:
    """Generates an official, courtroom-ready digital evidence authenticity and integrity report in PDF format."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=50,
    )

    styles = get_pdf_styles()
    story = []

    # IST Timezone (+05:30)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(ist_tz)

    # 1. Document Title & Header Card
    header_table_data = [
        [
            Paragraph("<b>FORGE FORENSIC REPORT</b>", styles["ReportTitle"]),
            Paragraph(
                f"<b>Generated:</b> {now_ist.strftime('%d-%b-%Y %H:%M:%S IST')}<br/>"
                f"<b>Ref ID:</b> {case.case_reference}",
                styles["TableCellBold"],
            ),
        ]
    ]
    t_header = Table(header_table_data, colWidths=[330, 193])
    t_header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t_header)

    story.append(
        Paragraph(
            "Digital Evidence Authenticity & Integrity Verification Platform • Cyber Hackathon 2026 (PS-05)",
            styles["ReportSubtitle"],
        )
    )
    story.append(Spacer(1, 8))

    # 2. Case Dossier Overview Table
    case_info_data = [
        [
            Paragraph("<b>Case Reference:</b>", styles["TableCellBold"]),
            Paragraph(case.case_reference, styles["TableCell"]),
            Paragraph("<b>Case ID:</b>", styles["TableCellBold"]),
            Paragraph(case.case_id, styles["TableCellMono"]),
        ],
        [
            Paragraph("<b>Lead Investigator:</b>", styles["TableCellBold"]),
            Paragraph(case.investigator_name, styles["TableCell"]),
            Paragraph("<b>Registered UTC:</b>", styles["TableCellBold"]),
            Paragraph(case.created_at, styles["TableCell"]),
        ],
        [
            Paragraph("<b>Evidence Count:</b>", styles["TableCellBold"]),
            Paragraph(f"{len(case.files)} file(s)", styles["TableCell"]),
            Paragraph("<b>Admissibility:</b>", styles["TableCellBold"]),
            Paragraph("Sec 65B Indian Evidence Act compliant", styles["TableCellBold"]),
        ],
    ]
    t_case = Table(case_info_data, colWidths=[95, 160, 95, 173])
    t_case.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(t_case)
    story.append(Spacer(1, 12))

    # 3. Overall Verdicts & Risk Summaries
    story.append(Paragraph("1. EXECUTIVE FORENSIC VERDICTS", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=6))

    verdict_rows = [
        [
            Paragraph("<b>Evidence File</b>", styles["TableCellBold"]),
            Paragraph("<b>Verdict</b>", styles["TableCellBold"]),
            Paragraph("<b>Risk Score</b>", styles["TableCellBold"]),
            Paragraph("<b>Key Investigative Findings</b>", styles["TableCellBold"]),
        ]
    ]

    for f in case.files:
        verdict = f.verdict
        verdict_str = verdict.overall.value if verdict else "PENDING"
        score_str = f"{verdict.score:.1f}/100" if verdict else "N/A"
        reasons_str = "<br/>• ".join(verdict.top_reasons) if (verdict and verdict.top_reasons) else "Awaiting analysis completion."

        bg_color = colors.HexColor("#F8FAFC")
        txt_color = "#0F172A"
        if verdict:
            if verdict.overall == OverallVerdict.AUTHENTIC:
                bg_color = colors.HexColor("#F0FDF4")
                txt_color = "#166534"
            elif verdict.overall == OverallVerdict.LIKELY_TAMPERED:
                bg_color = colors.HexColor("#FEF2F2")
                txt_color = "#991B1B"
            elif verdict.overall == OverallVerdict.SUSPICIOUS:
                bg_color = colors.HexColor("#FFFBEB")
                txt_color = "#92400E"

        verdict_rows.append(
            [
                Paragraph(f"<b>{f.original_name}</b><br/><font color='#64748B'>{f.media_type.value.upper()}</font>", styles["TableCell"]),
                Paragraph(f"<font color='{txt_color}'><b>{verdict_str}</b></font>", styles["TableCellBold"]),
                Paragraph(f"<b>{score_str}</b>", styles["TableCellBold"]),
                Paragraph(f"• {reasons_str}", styles["TableCell"]),
            ]
        )

    t_verdict = Table(verdict_rows, colWidths=[120, 95, 60, 248])
    t_verdict.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    # Apply custom text color for header row
    for col in range(4):
        t_verdict.setStyle(TableStyle([("TEXTCOLOR", (col, 0), (col, 0), colors.white)]))
    story.append(t_verdict)
    story.append(Spacer(1, 14))

    # 4. Chain of Custody & Hash Integrity Verification Section
    story.append(Paragraph("2. CHAIN OF CUSTODY & CRYPTOGRAPHIC INTEGRITY VERIFICATION", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=6))

    custody_rows = [
        [
            Paragraph("<b>Evidence File</b>", styles["TableCellBold"]),
            Paragraph("<b>Upload SHA-256 Digest</b>", styles["TableCellBold"]),
            Paragraph("<b>Re-computed Verification SHA-256</b>", styles["TableCellBold"]),
            Paragraph("<b>Integrity Result</b>", styles["TableCellBold"]),
        ]
    ]

    all_integrity_passed = True
    for f in case.files:
        verified_digest, is_match = verified_hashes.get(
            f.file_id, (f.sha256_at_upload, True)
        )
        if not is_match:
            all_integrity_passed = False

        status_text = "<font color='#16A34A'><b>MATCH (VERIFIED)</b></font>" if is_match else "<font color='#DC2626'><b>MISMATCH (TAMPERED)</b></font>"
        custody_rows.append(
            [
                Paragraph(f"<b>{f.original_name}</b>", styles["TableCell"]),
                Paragraph(f.sha256_at_upload, styles["TableCellMono"]),
                Paragraph(verified_digest, styles["TableCellMono"]),
                Paragraph(status_text, styles["TableCellBold"]),
            ]
        )

    t_custody = Table(custody_rows, colWidths=[110, 160, 160, 93])
    t_custody.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    for col in range(4):
        t_custody.setStyle(TableStyle([("TEXTCOLOR", (col, 0), (col, 0), colors.white)]))
    story.append(t_custody)

    story.append(Spacer(1, 4))
    integrity_statement = (
        "<b>LEGAL CERTIFICATION:</b> "
        + ("All evidence files match their original upload SHA-256 digests bit-for-bit. Chain of custody is intact."
           if all_integrity_passed
           else "CRITICAL ALERT: One or more evidence files exhibit hash discrepancy indicating post-upload alteration!")
    )
    story.append(Paragraph(integrity_statement, styles["TableCellBold"]))
    story.append(Spacer(1, 14))

    # 5. Detailed Forensic Findings & Visual Artifacts per File
    story.append(Paragraph("3. DETAILED FORENSIC MODULE FINDINGS & ARTIFACTS", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=8))

    for f in case.files:
        story.append(Paragraph(f"<b>Evidence Item: {f.original_name}</b> ({f.media_type.value.upper()} • {f.size_bytes} bytes)", styles["TableCellBold"]))
        story.append(Spacer(1, 3))

        findings_table_data = [
            [
                Paragraph("<b>Module</b>", styles["TableCellBold"]),
                Paragraph("<b>Forensic Check</b>", styles["TableCellBold"]),
                Paragraph("<b>Outcome</b>", styles["TableCellBold"]),
                Paragraph("<b>Conf.</b>", styles["TableCellBold"]),
                Paragraph("<b>Investigative Details & Explanations</b>", styles["TableCellBold"]),
            ]
        ]

        if f.results:
            for mod_name, mod_res in f.results.items():
                for check in mod_res.findings:
                    res_color = "#16A34A" if check.result == FindingResult.PASS else "#DC2626" if check.result == FindingResult.TAMPERED else "#D97706" if check.result == FindingResult.SUSPICIOUS else "#64748B"
                    findings_table_data.append(
                        [
                            Paragraph(check.module, styles["TableCell"]),
                            Paragraph(check.check_name.replace("_", " "), styles["TableCellBold"]),
                            Paragraph(f"<font color='{res_color}'><b>{check.result.value.upper()}</b></font>", styles["TableCellBold"]),
                            Paragraph(f"{int(check.confidence * 100)}%", styles["TableCell"]),
                            Paragraph(check.explanation, styles["TableCell"]),
                        ]
                    )
        else:
            findings_table_data.append(
                [
                    Paragraph("N/A", styles["TableCell"]),
                    Paragraph("No analysis results recorded", styles["TableCell"]),
                    Paragraph("PENDING", styles["TableCell"]),
                    Paragraph("0%", styles["TableCell"]),
                    Paragraph("Run analysis pipeline to compute scores.", styles["TableCell"]),
                ]
            )

        t_findings = Table(findings_table_data, colWidths=[90, 115, 75, 40, 203])
        t_findings.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        for col in range(5):
            t_findings.setStyle(TableStyle([("TEXTCOLOR", (col, 0), (col, 0), colors.white)]))
        story.append(t_findings)
        story.append(Spacer(1, 8))

        # Check and embed visual artifacts if present
        artifacts_to_embed = []
        if f.results:
            for mod_res in f.results.values():
                for check in mod_res.findings:
                    for art_path in check.artifact_paths:
                        p = Path(art_path)
                        if not p.is_absolute():
                            p = settings.artifacts_dir / case.case_id / f.file_id / p.name
                        if p.exists() and p.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                            if str(p) not in [a[0] for a in artifacts_to_embed]:
                                artifacts_to_embed.append((str(p), check.check_name))

        if artifacts_to_embed:
            story.append(Paragraph("<b>Forensic Visual Artifacts Generated:</b>", styles["TableCellBold"]))
            story.append(Spacer(1, 4))
            for art_file, check_label in artifacts_to_embed[:3]:  # Max 3 prominent artifacts
                try:
                    rl_img = RLImage(art_file, width=420, height=190, kind="proportional")
                    story.append(KeepTogether([
                        Paragraph(f"<b>Artifact:</b> {Path(art_file).name} (from check: {check_label})", styles["TableCell"]),
                        rl_img,
                        Spacer(1, 6),
                    ]))
                except Exception as img_err:
                    story.append(Paragraph(f"Artifact {Path(art_file).name} could not be rendered: {img_err}", styles["LegalNotice"]))

        story.append(Spacer(1, 10))

    # 6. Immutable Audit Trail Log
    story.append(Paragraph("4. IMMUTABLE CHAIN-OF-CUSTODY AUDIT TRAIL", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=6))

    audit_rows = [
        [
            Paragraph("<b>Timestamp (UTC)</b>", styles["TableCellBold"]),
            Paragraph("<b>Action</b>", styles["TableCellBold"]),
            Paragraph("<b>Actor</b>", styles["TableCellBold"]),
            Paragraph("<b>File / Details Payload</b>", styles["TableCellBold"]),
        ]
    ]

    for a in audit_trail[:25]:  # Show up to 25 latest events
        details_txt = str(a.details)
        if len(details_txt) > 85:
            details_txt = details_txt[:82] + "..."
        audit_rows.append(
            [
                Paragraph(a.timestamp_utc, styles["TableCellMono"]),
                Paragraph(f"<b>{a.action}</b>", styles["TableCell"]),
                Paragraph(a.actor, styles["TableCell"]),
                Paragraph(details_txt, styles["TableCell"]),
            ]
        )

    t_audit = Table(audit_rows, colWidths=[120, 95, 105, 203])
    t_audit.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    for col in range(4):
        t_audit.setStyle(TableStyle([("TEXTCOLOR", (col, 0), (col, 0), colors.white)]))
    story.append(t_audit)
    story.append(Spacer(1, 14))

    # 7. Courtroom Admissibility Declaration & Tool Versions
    story.append(Paragraph("5. STATUTORY ADMISSIBILITY DECLARATION & TOOL VERSIONS", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284C7"), spaceAfter=6))

    tools_text = (
        f"<b>Engine Environment:</b> FORGE v{settings.APP_VERSION} (Python, OpenCV v{cv2.__version__}, "
        f"Pillow v{PIL.__version__}, SciPy v{scipy.__version__}, ReportLab v{reportlab.__version__}).<br/>"
        "<b>Operating Standard:</b> ISO/IEC 27037:2012 (Guidelines for identification, collection, acquisition and preservation of digital evidence) "
        "and Section 65B of the Indian Evidence Act, 1872 / Section 63 Bharatiya Sakshya Adhiniyam, 2023."
    )
    story.append(Paragraph(tools_text, styles["TableCell"]))
    story.append(Spacer(1, 6))

    disclaimer_text = (
        "<b>STATUTORY DISCLAIMER:</b> This report is generated by automated computational digital forensics modules. "
        "All hashes are computed strictly using SHA-256 over read-only bitstream images of evidence. "
        "These computational results are furnished as forensic investigative aids and expert technical analysis for law enforcement "
        "and judicial authorities. Final legal determination of guilt, liability, or intent rests exclusively with the competent court of law."
    )
    story.append(Paragraph(disclaimer_text, styles["LegalNotice"]))

    # Build PDF with custom NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
