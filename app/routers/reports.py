"""Reporting router — JSON device report, PDF download, and aggregated dashboard."""

from collections import OrderedDict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.evaluator.engine import evaluate_device, EvaluatorError
from app.models import Device, Finding

router = APIRouter()

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _group_findings(findings: list) -> OrderedDict:
    """Group findings by category, preserving insertion order."""
    grouped: dict[str, list] = {}
    for f in findings:
        grouped.setdefault(f.category, []).append(f)
    return OrderedDict(sorted(grouped.items()))


def _get_device_or_404(db: Session, device_id: int) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found.")
    return device


def _get_findings(db: Session, device_id: int, framework: str) -> list[Finding]:
    return (
        db.query(Finding)
        .filter(Finding.device_id == device_id, Finding.framework == framework)
        .all()
    )


def _ensure_findings(db: Session, device: Device, framework: str) -> list[Finding]:
    """Return existing findings or run evaluation if none exist yet."""
    findings = _get_findings(db, device.id, framework)
    if not findings:
        try:
            findings = evaluate_device(db, device, framework=framework)
            db.commit()
        except EvaluatorError:
            findings = []
    return findings


def _render_pdf_fpdf(
    device: Device,
    framework: str,
    findings: list[Finding],
    pass_count: int,
    fail_count: int,
    manual_review_count: int = 0,
) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Banner Header
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "  Compliance Audit Report", fill=True, new_x="LMARGIN", new_y="NEXT")

    # Metadata
    pdf.ln(4)
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Device: {device.filename}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Vendor: {device.vendor.upper()}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Framework: {framework}", new_x="LMARGIN", new_y="NEXT")
    if device.uploaded_at:
        pdf.cell(0, 6, f"Uploaded: {device.uploaded_at.strftime('%Y-%m-%d %H:%M UTC')}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(
        0, 8,
        f"Summary: {len(findings)} Total Rules  |  {pass_count} Passed  |  {fail_count} Failed"
        + (f"  |  {manual_review_count} Manual Review" if manual_review_count else ""),
        new_x="LMARGIN", new_y="NEXT",
    )

    # Coverage indicator (Correction 3): how many controls this device's
    # parsed config actually gave the evaluator enough real signal to judge.
    evaluable = pass_count + fail_count
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(
        0, 6,
        f"Coverage: {evaluable} of {len(findings)} {framework} controls evaluable for this device"
        + (f"; {manual_review_count} require configuration data this adapter did not extract" if manual_review_count else ""),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_text_color(30, 41, 59)
    pdf.ln(4)

    if manual_review_count:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, "Manual Review Required (no confident data to evaluate):", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for f in findings:
            if f.status == "manual_review":
                pdf.cell(0, 5, f"  - {f.rule_id}: {f.title}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    grouped = _group_findings(findings)
    for cat, cat_findings in grouped.items():
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 8, f"  Category: {cat.replace('_', ' ').title()}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(25, 6, "Rule ID", border="B")
        pdf.cell(60, 6, "Title", border="B")
        pdf.cell(20, 6, "Status", border="B")
        pdf.cell(25, 6, "Severity", border="B")
        pdf.cell(60, 6, "Remediation", border="B", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 41, 59)
        for f in cat_findings:
            status_str = "REVIEW" if f.status == "manual_review" else f.status.upper()
            sev_str = f.severity or "-"
            remed = (
                f.remediation_text
                if (f.status == "fail" and f.remediation_text)
                else ("Compliant" if f.status == "pass" else "-")
            )
            title_short = (f.title[:35] + "...") if f.title and len(f.title) > 38 else (f.title or "")
            remed_short = (remed[:35] + "...").replace("\n", " ") if len(remed) > 38 else remed.replace("\n", " ")

            pdf.cell(25, 6, f.rule_id[:12])
            pdf.cell(60, 6, title_short)
            pdf.cell(20, 6, status_str)
            pdf.cell(25, 6, sev_str)
            pdf.cell(60, 6, remed_short, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

    return bytes(pdf.output())


@router.get("/devices/{device_id}/report.pdf")
def device_report_pdf(
    device_id: int,
    framework: str = Query("CIS"),
    db: Session = Depends(get_db),
):
    device = _get_device_or_404(db, device_id)
    findings = _ensure_findings(db, device, framework)

    pass_count = sum(1 for f in findings if f.status == "pass")
    fail_count = sum(1 for f in findings if f.status == "fail")
    manual_review_count = sum(1 for f in findings if f.status == "manual_review")

    pdf_bytes = _render_pdf_fpdf(device, framework, findings, pass_count, fail_count, manual_review_count)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{device.filename}_{framework}_report.pdf"'
        },
    )


@router.get("/devices/{device_id}/report")
@router.get("/api/devices/{device_id}/report")
def device_report_json(
    device_id: int,
    framework: str = Query("CIS"),
    db: Session = Depends(get_db),
):
    device = _get_device_or_404(db, device_id)
    findings = _ensure_findings(db, device, framework)

    pass_count = sum(1 for f in findings if f.status == "pass")
    fail_count = sum(1 for f in findings if f.status == "fail")
    manual_review_count = sum(1 for f in findings if f.status == "manual_review")
    grouped = _group_findings(findings)

    return {
        "device": {
            "id": device.id,
            "filename": device.filename,
            "vendor": device.vendor,
            "uploaded_at": device.uploaded_at.isoformat() if device.uploaded_at else None,
        },
        "framework": framework,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "manual_review_count": manual_review_count,
        # Coverage indicator (Correction 3): how many controls this specific
        # device's parsed config actually gave the evaluator enough real
        # signal to judge, versus how many need configuration data no
        # adapter extracted here.
        "coverage": {
            "evaluable_count": pass_count + fail_count,
            "total_controls": len(findings),
        },
        "total_rules": len(findings),
        "grouped_findings": {
            cat: [
                {
                    "id": f.id,
                    "rule_id": f.rule_id,
                    "title": f.title,
                    "category": f.category,
                    "status": f.status,
                    "severity": f.severity,
                    "remediation_text": f.remediation_text,
                }
                for f in cat_list
            ]
            for cat, cat_list in grouped.items()
        },
    }


@router.get("/dashboard")
@router.get("/api/dashboard/stats")
def dashboard_stats_json(db: Session = Depends(get_db)):
    total_devices = db.query(Device).count()
    total_findings = db.query(Finding).count()
    total_pass = db.query(Finding).filter(Finding.status == "pass").count()
    total_fail = db.query(Finding).filter(Finding.status == "fail").count()

    sev_rows = (
        db.query(Finding.severity, func.count(Finding.id))
        .filter(Finding.status == "fail")
        .group_by(Finding.severity)
        .all()
    )
    severity_counts = {sev: cnt for sev, cnt in sev_rows}

    device_findings = (
        db.query(
            Finding.device_id,
            Finding.framework,
            func.count(Finding.id).label("total"),
            func.sum(func.iif(Finding.status == "pass", 1, 0)).label("pass_count"),
            func.sum(func.iif(Finding.status == "fail", 1, 0)).label("fail_count"),
        )
        .group_by(Finding.device_id, Finding.framework)
        .all()
    )

    device_summaries = []
    for row in device_findings:
        device = db.query(Device).filter(Device.id == row.device_id).first()
        if not device:
            continue

        worst_finding = (
            db.query(Finding)
            .filter(
                Finding.device_id == row.device_id,
                Finding.framework == row.framework,
                Finding.status == "fail",
            )
            .all()
        )
        worst_severity = None
        if worst_finding:
            worst_severity = min(worst_finding, key=lambda f: SEVERITY_ORDER.get(f.severity, 99)).severity

        device_summaries.append(
            {
                "device_id": device.id,
                "filename": device.filename,
                "vendor": device.vendor,
                "framework": row.framework,
                "pass_count": row.pass_count or 0,
                "fail_count": row.fail_count or 0,
                "worst_severity": worst_severity,
            }
        )

    device_summaries.sort(
        key=lambda d: (-d["fail_count"], SEVERITY_ORDER.get(d["worst_severity"] or "", 99))
    )

    return {
        "total_devices": total_devices,
        "total_findings": total_findings,
        "total_pass": total_pass,
        "total_fail": total_fail,
        "severity_counts": severity_counts,
        "device_summaries": device_summaries,
    }


