from datetime import datetime
from typing import List, Optional, Dict, Any
from app.database import get_dvi_db
from app.matcher import get_bob_matcher
from app.schemas import BodyReconciliation, ReconciliationReport

class ReconciliationEngine:
    def __init__(self):
        self.db = get_dvi_db()
        self.matcher = get_bob_matcher()

    def generate_full_report(
        self,
        coordinator_name: str = "NDRF DVI Operational Cell - Balasore Command",
        disaster_event: str = "Odisha Balasore Train Collision DVI Operation"
    ) -> ReconciliationReport:
        all_pm = self.db.get_all_pm()
        all_am = self.db.get_all_am()

        reconciliations: List[BodyReconciliation] = []
        report_id = f"DVI-REP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        for pm in all_pm:
            # Generate or fetch top 3 candidates via Bob
            top_candidates = self.matcher.cross_reference_body(pm, all_am, top_k=3)
            
            recon_record = self.db.get_reconciliation_record(pm.id)
            status = "Pending_Review"
            confirmed_id = None
            notes = None

            if recon_record:
                status = recon_record.get("status", "Pending_Review")
                confirmed_id = recon_record.get("confirmed_am_id")
                notes = recon_record.get("forensic_notes")
            elif top_candidates and top_candidates[0].match_probability >= 80.0:
                status = "High_Priority_Review"

            recon = BodyReconciliation(
                post_mortem_id=pm.id,
                post_mortem_record=pm,
                top_candidates=top_candidates,
                generated_at=datetime.utcnow().isoformat(),
                status=status,
                confirmed_am_id=confirmed_id,
                forensic_notes=notes
            )
            reconciliations.append(recon)

        return ReconciliationReport(
            report_id=report_id,
            disaster_event=disaster_event,
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            coordinator_name=coordinator_name,
            total_unidentified_bodies=len(all_pm),
            total_missing_persons=len(all_am),
            reconciliations=reconciliations
        )

    def generate_printable_html(self, report: ReconciliationReport) -> str:
        rows_html = ""
        for item in report.reconciliations:
            top_cand = item.top_candidates[0] if item.top_candidates else None
            cand_info = "No candidates found"
            prob_badge = '<span style="color: #94a3b8;">N/A</span>'
            rationale_text = "Awaiting ante-mortem intake data"

            if top_cand:
                prob = top_cand.match_probability
                color = "#10b981" if prob >= 75 else ("#f59e0b" if prob >= 50 else "#ef4444")
                prob_badge = f'<strong style="color: {color}; font-size: 1.1em;">{prob}%</strong>'
                cand_info = f"<b>{top_cand.missing_person_name}</b> ({top_cand.ante_mortem_id})<br><small>Reported Age: {top_cand.am_profile.age or top_cand.am_profile.age_range}, Sex: {top_cand.am_profile.gender}</small>"
                rationale_text = top_cand.rationale

            rows_html += f"""
            <tr style="border-bottom: 1px solid #cbd5e1;">
                <td style="padding: 12px; vertical-align: top;">
                    <b>{item.post_mortem_id}</b><br>
                    <small style="color: #64748b;">{item.post_mortem_record.recovery_location}</small><br>
                    <span style="display:inline-block; margin-top:4px; font-size:0.8em; padding:2px 6px; background:#f1f5f9; border-radius:4px;">
                        {item.post_mortem_record.estimated_gender}, {item.post_mortem_record.estimated_age_range}
                    </span>
                </td>
                <td style="padding: 12px; vertical-align: top;">{cand_info}</td>
                <td style="padding: 12px; vertical-align: top; text-align: center;">{prob_badge}</td>
                <td style="padding: 12px; vertical-align: top; font-size: 0.88em; color: #334155;">{rationale_text}</td>
                <td style="padding: 12px; vertical-align: top; text-align: center;">
                    <span style="padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; background: {'#dcfce7; color: #166534;' if item.status == 'Confirmed' else '#fef3c7; color: #92400e;'}">
                        {item.status.replace('_', ' ')}
                    </span>
                </td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>DVI Reconciliation Report - {report.disaster_event}</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; margin: 40px; }}
                .header {{ border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px; }}
                .stats-grid {{ display: flex; gap: 20px; margin-bottom: 24px; }}
                .stat-box {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px 20px; border-radius: 6px; flex: 1; }}
                .stat-box h4 {{ margin: 0; font-size: 0.85em; color: #64748b; text-transform: uppercase; }}
                .stat-box p {{ margin: 6px 0 0; font-size: 1.6em; font-weight: bold; color: #0f172a; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
                th {{ background: #f1f5f9; padding: 10px 12px; text-align: left; font-size: 0.85em; border-bottom: 2px solid #cbd5e1; }}
                .signature-block {{ margin-top: 50px; display: flex; justify-content: space-between; page-break-inside: avoid; }}
                .sig-line {{ width: 280px; border-top: 1px solid #0f172a; text-align: center; padding-top: 8px; font-size: 0.85em; }}
                @media print {{
                    body {{ margin: 15mm; }}
                    button {{ display: none; }}
                }}
            </style>
        </head>
        <body>
            <div style="float: right;">
                <button onclick="window.print()" style="padding: 8px 16px; background: #2563eb; color: #fff; border: none; border-radius: 4px; cursor: pointer;">Print / Save PDF</button>
            </div>
            <div class="header">
                <h1 style="margin: 0 0 6px; font-size: 1.8em;">DISASTER VICTIM IDENTIFICATION (DVI) RECONCILIATION REPORT</h1>
                <p style="margin: 0; color: #475569; font-size: 1.05em;"><b>Incident:</b> {report.disaster_event} &bull; <b>Report ID:</b> {report.report_id}</p>
                <p style="margin: 4px 0 0; color: #64748b; font-size: 0.9em;">Operational Authority: {report.coordinator_name} &bull; Generated: {report.generated_at}</p>
            </div>

            <div class="stats-grid">
                <div class="stat-box">
                    <h4>Total Unidentified Bodies (PM)</h4>
                    <p>{report.total_unidentified_bodies}</p>
                </div>
                <div class="stat-box">
                    <h4>Ante-Mortem Profiles Logged (AM)</h4>
                    <p>{report.total_missing_persons}</p>
                </div>
                <div class="stat-box">
                    <h4>Cross-Referenced Pairings</h4>
                    <p>{report.total_unidentified_bodies * report.total_missing_persons}</p>
                </div>
            </div>

            <h3 style="margin-top: 24px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">Bob Cross-Reference & Priority Reconciliation Matrix</h3>
            <table>
                <thead>
                    <tr>
                        <th style="width: 20%;">Post-Mortem Body ID</th>
                        <th style="width: 25%;">Top Candidate (AM)</th>
                        <th style="width: 12%; text-align: center;">Match Probability</th>
                        <th style="width: 33%;">Bob's Forensic Cross-Reference Rationale</th>
                        <th style="width: 10%; text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <div class="signature-block">
                <div class="sig-line">
                    <b>Forensic Pathologist / Odontologist</b><br>
                    State Medical Board / AIIMS DVI Unit
                </div>
                <div class="sig-line">
                    <b>NDRF DVI Operational Coordinator</b><br>
                    Disaster Management Incident Commander
                </div>
                <div class="sig-line">
                    <b>District Executive Magistrate</b><br>
                    Legal Identification Verification & Release
                </div>
            </div>
        </body>
        </html>
        """
        return html

_recon_instance = None

def get_reconciliation_engine() -> ReconciliationEngine:
    global _recon_instance
    if _recon_instance is None:
        _recon_instance = ReconciliationEngine()
    return _recon_instance
