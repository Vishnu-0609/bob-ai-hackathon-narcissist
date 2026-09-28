import os
import io
import csv
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from app.models.entities import Report, Incident, PMCase, AMCase, Match, Reconciliation, AuditLog
from app.services.bob_rationale import BobRationaleService
from app.services.bob_evidence_gap import BobEvidenceGapService
from app.services.audit_service import AuditService


class ReportService:
    @staticmethod
    def generate_reconciliation_pdf(
        incident: Incident,
        pm_case: PMCase,
        am_case: AMCase,
        match: Optional[Match],
        reconciliation: Optional[Reconciliation],
        evaluation_data: Dict[str, Any],
        rationale_text: str,
        evidence_gap_data: Dict[str, Any],
        report_number: str,
        audit_event_id: str,
    ) -> bytes:
        """
        Generates a PDF using ReportLab with styling and forensic sections.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        normal = styles["Normal"]

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "SubTitle",
            parent=normal,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#475569"),
            spaceAfter=8,
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "BodyDark",
            parent=normal,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=normal,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#b91c1c"),
        )

        story = []

        # 1. Header Banner
        header_data = [
            [
                Paragraph("<b>DVI-BRIDGE FORENSIC RECONCILIATION REPORT</b>", title_style),
                Paragraph(f"<b>Report Ref:</b> {report_number}<br/><b>Date:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}<br/><b>Audit Chain ID:</b> {audit_event_id}", subtitle_style),
            ]
        ]
        t_header = Table(header_data, colWidths=[340, 200])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        story.append(t_header)
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

        # 2. Case & Incident Overview Table
        score = evaluation_data.get("match_score", match.match_score if match else 0.0)
        quality = evaluation_data.get("evidence_quality", match.evidence_quality if match else "MEDIUM")
        status = reconciliation.decision if reconciliation else "PENDING_REVIEW"

        overview_data = [
            [
                Paragraph("<b>Incident Name:</b>", body_style),
                Paragraph(incident.name, body_style),
                Paragraph("<b>Match Score:</b>", body_style),
                Paragraph(f"<b>{score:.1f} / 100</b> ({quality})", body_style),
            ],
            [
                Paragraph("<b>PM Body ID:</b>", body_style),
                Paragraph(f"<b>{pm_case.body_number}</b>", body_style),
                Paragraph("<b>AM Candidate ID:</b>", body_style),
                Paragraph(f"<b>{am_case.case_number}</b> ({am_case.name})", body_style),
            ],
            [
                Paragraph("<b>Recovery Sector:</b>", body_style),
                Paragraph(pm_case.recovery_location or "N/A", body_style),
                Paragraph("<b>Reconciliation Status:</b>", body_style),
                Paragraph(f"<b>{status}</b>", body_style),
            ],
        ]
        t_overview = Table(overview_data, colWidths=[100, 170, 120, 150])
        t_overview.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_overview)
        story.append(Spacer(1, 10))

        # 3. Field-by-Field Evidence Comparison Table
        story.append(Paragraph("<b>1. Detailed Evidence Comparison Matrix</b>", h2_style))
        evidence_items = evaluation_data.get("evidence_items", [])

        matrix_rows = [[
            Paragraph("<b>Forensic Attribute</b>", body_style),
            Paragraph("<b>AM Reported (Family)</b>", body_style),
            Paragraph("<b>PM Observed (Mortuary)</b>", body_style),
            Paragraph("<b>Concordance</b>", body_style),
            Paragraph("<b>Score</b>", body_style),
        ]]

        for item in evidence_items:
            res = item.get("comparison_result", "UNKNOWN")
            score_awd = item.get("score_awarded", 0.0)
            weight = item.get("weight", 0.0)

            res_color = "#16a34a" if res == "MATCH" else ("#dc2626" if res == "MISMATCH" else "#ca8a04")
            res_p = Paragraph(f"<font color='{res_color}'><b>{res}</b></font>", body_style)

            matrix_rows.append([
                Paragraph(item.get("field_name", "").replace("_", " ").title(), body_style),
                Paragraph(str(item.get("am_value", "-"))[:40], body_style),
                Paragraph(str(item.get("pm_value", "-"))[:40], body_style),
                res_p,
                Paragraph(f"{score_awd:.1f}/{weight:.1f}", body_style),
            ])

        t_matrix = Table(matrix_rows, colWidths=[110, 150, 150, 80, 50])
        t_matrix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t_matrix)
        story.append(Spacer(1, 10))

        # 4. IBM Bob Forensic Rationale & Evidence Gap Narrative
        story.append(Paragraph("<b>2. IBM Bob Forensic Rationale & Explainability</b>", h2_style))
        story.append(Paragraph(rationale_text.replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 8))

        story.append(Paragraph("<b>3. Evidence Gaps & Recommended Verification Protocol</b>", h2_style))
        rec_list = evidence_gap_data.get("recommended_workflow", [])
        if rec_list:
            rec_text = "<br/>".join([f"• {r}" for r in rec_list])
            story.append(Paragraph(rec_text, body_style))
        else:
            story.append(Paragraph("All standard secondary identifiers examined.", body_style))
        story.append(Spacer(1, 10))

        # 5. Human Decision & Sign-Off Section
        story.append(Paragraph("<b>4. Forensic Coordinator Reconciliation Sign-Off</b>", h2_style))
        reason = reconciliation.reason if reconciliation else "Pending forensic board review."
        reviewer = reconciliation.reviewed_by if reconciliation else "Unassigned Coordinator"

        sign_data = [
            [
                Paragraph(f"<b>Final Decision:</b> {status}<br/><b>Forensic Reviewer:</b> {reviewer}<br/><b>Decision Rationale:</b> {reason}", body_style),
                Paragraph("<b>Authorized Signature:</b><br/><br/>____________________________________<br/>Chief DVI Coordinator / Pathologist", body_style),
            ]
        ]
        t_sign = Table(sign_data, colWidths=[320, 220])
        t_sign.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t_sign)
        story.append(Spacer(1, 12))

        # 6. Mandatory Disclaimer & Hash Chain Stamp
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
        story.append(Paragraph(
            "<b>LEGAL & FORENSIC MANDATE:</b> This document is an AI-assisted candidate reconciliation support record. "
            "Under Interpol Disaster Victim Identification Standards, an automated or algorithmic score does not constitute "
            "legal identification. Definitive identification requires authorized scientific verification (comparative odontological, "
            "dactyloscopic, or STR DNA profiling) approved by the designated Medical Examiner.",
            disclaimer_style,
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    @staticmethod
    def create_report_record(
        db: Session,
        incident_id: str,
        pm_id: str,
        am_id: str,
        title: Optional[str] = None,
        user_id: str = "COORDINATOR",
        user_role: str = "COORDINATOR",
    ) -> Report:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        pm_case = db.query(PMCase).filter(PMCase.id == pm_id).first()
        am_case = db.query(AMCase).filter(AMCase.id == am_id).first()
        match = db.query(Match).filter(Match.pm_id == pm_id, Match.am_id == am_id).first()
        reconciliation = db.query(Reconciliation).filter(Reconciliation.pm_id == pm_id, Reconciliation.am_id == am_id).first()

        if not incident or not pm_case or not am_case:
            raise ValueError("Incident, PM Case, or AM Case not found.")

        from app.services.matching_engine import MatchingEngine
        engine = MatchingEngine()
        eval_data = engine.evaluate_pair(pm_case, am_case)

        rationale = BobRationaleService._generate_local_rationale(eval_data)
        evidence_gaps = BobEvidenceGapService._local_evidence_gaps(eval_data)

        count = db.query(Report).count() + 1
        report_number = f"REP-DVI-{count:05d}"
        report_title = title or f"Reconciliation Report — {pm_case.body_number} ↔ {am_case.case_number}"

        # Generate Audit Log first for immutable cross-reference
        audit_event = AuditService.log_event(
            db=db,
            user_id=user_id,
            role=user_role,
            action="REPORT_GENERATED",
            entity_type="REPORT",
            entity_id=report_number,
            details={
                "pm_body_number": pm_case.body_number,
                "am_case_number": am_case.case_number,
                "match_score": eval_data["match_score"],
            },
        )

        content = {
            "incident": {"id": incident.id, "name": incident.name, "location": incident.location},
            "pm_case": {"id": pm_case.id, "body_number": pm_case.body_number, "sex": pm_case.sex, "height_cm": pm_case.height_cm},
            "am_case": {"id": am_case.id, "case_number": am_case.case_number, "name": am_case.name, "sex": am_case.sex},
            "evaluation": eval_data,
            "rationale": rationale,
            "evidence_gaps": evidence_gaps,
            "reconciliation": {
                "decision": reconciliation.decision if reconciliation else "PENDING_REVIEW",
                "reason": reconciliation.reason if reconciliation else "",
                "reviewed_by": reconciliation.reviewed_by if reconciliation else "",
            },
            "audit_event_id": audit_event.event_id,
            "audit_event_hash": audit_event.event_hash,
        }

        report = Report(
            incident_id=incident_id,
            pm_id=pm_id,
            am_id=am_id,
            report_number=report_number,
            title=report_title,
            summary=f"Score: {eval_data['match_score']}/100 | Decision: {content['reconciliation']['decision']}",
            content_json=content,
            generated_by=user_id,
            status="FINAL" if reconciliation else "DRAFT",
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
