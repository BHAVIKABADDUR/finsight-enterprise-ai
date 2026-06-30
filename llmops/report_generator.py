# llmops/report_generator.py
# Generates professional PDF reports from agent analysis results
# Used for the "Export Report" feature in Streamlit

import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from loguru import logger

def generate_analysis_report(
    decision: dict,
    analysis: dict,
    extracted: dict,
    query: str,
    run_id: str,
    output_dir: str = "data/reports"
) -> str:
    """
    Generate a professional PDF report from agent analysis results.
    
    Args:
        decision: Final decision dict from Decision Agent
        analysis: Analysis results from Analysis Agent
        extracted: Extracted data from Extraction Agent
        query: Original user query
        run_id: Unique run identifier
        output_dir: Where to save the PDF
        
    Returns:
        Path to the generated PDF file
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"finsight_report_{timestamp}.pdf"
    filepath = Path(output_dir) / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=22, textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle", parent=styles["Normal"],
        fontSize=11, textColor=colors.grey, spaceAfter=20
    )
    section_style = ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontSize=14, textColor=colors.HexColor("#1a1a2e"),
        spaceBefore=16, spaceAfter=8
    )
    body_style = ParagraphStyle(
        "CustomBody", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=10
    )

    elements = []

    # ── Cover header ──────────────────────────────────────────────────────────
    elements.append(Paragraph("FinSight Enterprise AI", title_style))
    elements.append(Paragraph(
        "Financial Document Intelligence Report",
        subtitle_style
    ))

    report_info = [
        ["Report Generated:", datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")],
        ["Run ID:", run_id],
        ["Query:", query[:80] + ("..." if len(query) > 80 else "")],
    ]
    info_table = Table(report_info, colWidths=[4*cm, 12*cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Risk Rating Banner ────────────────────────────────────────────────────
    risk = decision.get("overall_risk_rating", "UNKNOWN")
    risk_colors = {
        "HIGH": colors.HexColor("#dc2626"),
        "MEDIUM": colors.HexColor("#ea580c"),
        "LOW": colors.HexColor("#16a34a")
    }
    risk_color = risk_colors.get(risk, colors.grey)

    risk_table = Table([[f"OVERALL RISK RATING: {risk}"]], colWidths=[16*cm])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), risk_color),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 13),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(risk_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Executive Summary ─────────────────────────────────────────────────────
    elements.append(Paragraph("Executive Summary", section_style))
    elements.append(Paragraph(
        decision.get("executive_summary", "No summary available"),
        body_style
    ))

    # ── Key Metrics ────────────────────────────────────────────────────────────
    elements.append(Paragraph("Key Metrics", section_style))
    txn_summary = extracted.get("transactions", {}).get("summary", {})

    metrics_data = [
        ["Metric", "Value"],
        ["Total Transactions", str(txn_summary.get("total_transactions", txn_summary.get("total_count", "N/A")))],
        ["Total Credit (AED)", f"{txn_summary.get('total_credit_aed', 0):,.2f}"],
        ["Total Debit (AED)", f"{txn_summary.get('total_debit_aed', 0):,.2f}"],
        ["Flagged Transactions", str(txn_summary.get("flagged_count", 0))],
    ]
    metrics_table = Table(metrics_data, colWidths=[8*cm, 8*cm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── Recommended Actions ───────────────────────────────────────────────────
    elements.append(Paragraph("Recommended Actions", section_style))
    actions = decision.get("recommended_actions", [])

    if actions:
        action_data = [["Priority", "Action", "Reason"]]
        for action in actions:
            action_data.append([
                action.get("priority", "").upper(),
                action.get("action", "")[:60],
                action.get("reason", "")[:60]
            ])

        action_table = Table(action_data, colWidths=[2.5*cm, 7*cm, 6.5*cm])
        action_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(action_table)
    else:
        elements.append(Paragraph("No specific actions recommended.", body_style))

    elements.append(Spacer(1, 0.5*cm))

    # ── Primary Concerns ──────────────────────────────────────────────────────
    elements.append(Paragraph("Primary Concerns", section_style))
    concerns = decision.get("primary_concerns", [])
    if concerns:
        for concern in concerns:
            elements.append(Paragraph(f"• {concern}", body_style))
    else:
        elements.append(Paragraph("No specific concerns identified.", body_style))

    # ── Page break for second page ────────────────────────────────────────────
    elements.append(PageBreak())

    # ── Flagged Transactions Detail ───────────────────────────────────────────
    elements.append(Paragraph("Flagged Transactions — Detailed View", section_style))
    flagged = extracted.get("transactions", {}).get("flagged_transactions", [])

    if flagged:
        flag_data = [["Date", "Description", "Amount (AED)", "Flag Reason"]]
        for txn in flagged[:15]:
            amount = txn.get("amount", 0)
            if isinstance(amount, str):
                amount = amount.replace("AED", "").replace(",", "").strip()
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0.0

            flag_data.append([
                str(txn.get("date", txn.get("transaction_date", ""))),
                str(txn.get("description", ""))[:30],
                f"{amount:,.2f}",
                str(txn.get("flag_reason", ""))[:40]
            ])

        flag_table = Table(flag_data, colWidths=[2.5*cm, 5*cm, 3*cm, 5.5*cm])
        flag_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dc2626")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef2f2")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(flag_table)
    else:
        elements.append(Paragraph("No flagged transactions in this analysis.", body_style))

    elements.append(Spacer(1, 1*cm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, alignment=TA_CENTER
    )
    elements.append(Paragraph(
        "This report was generated automatically by FinSight Enterprise AI — "
        "a multi-agent financial intelligence system built with LangGraph, MCP, "
        "Supabase and Groq. All data shown is synthetic and used for demonstration purposes.",
        footer_style
    ))

    doc.build(elements)
    logger.success(f"PDF report generated: {filepath}")

    return str(filepath)

if __name__ == "__main__":
    # Test with sample data
    mock_decision = {
        "overall_risk_rating": "HIGH",
        "executive_summary": "Test executive summary for report generation testing purposes.",
        "recommended_actions": [
            {"priority": "immediate", "action": "Review flagged transaction", "reason": "Large amount detected"}
        ],
        "primary_concerns": ["Test concern 1", "Test concern 2"]
    }
    mock_analysis = {}
    mock_extracted = {
        "transactions": {
            "summary": {
                "total_transactions": 33,
                "total_credit_aed": 100000,
                "total_debit_aed": 150000,
                "flagged_count": 4
            },
            "flagged_transactions": [
                {
                    "date": "2026-06-19",
                    "description": "TEST TRANSACTION",
                    "amount": 127356.98,
                    "flag_reason": "Unusually large transaction"
                }
            ]
        }
    }

    path = generate_analysis_report(
        decision=mock_decision,
        analysis=mock_analysis,
        extracted=mock_extracted,
        query="Test query for report generation",
        run_id="test-run-12345"
    )
    print(f"\n✅ Report generated at: {path}")