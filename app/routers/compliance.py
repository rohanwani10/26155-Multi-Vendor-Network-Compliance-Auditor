from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.evaluator.engine import EvaluatorError, evaluate_device
from app.models import Device, Finding

router = APIRouter()


@router.post("/evaluate/{device_id}")
def evaluate_device_endpoint(
    device_id: int,
    framework: str = Query("CIS", description="Security framework (CIS, NIST, STIG, ISO)"),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found.")

    try:
        findings = evaluate_device(db, device, framework=framework)
        db.commit()
    except EvaluatorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pass_count = sum(1 for f in findings if f.status == "pass")
    fail_count = sum(1 for f in findings if f.status == "fail")

    return {
        "device_id": device.id,
        "filename": device.filename,
        "vendor": device.vendor,
        "framework": framework,
        "summary": {
            "total_rules": len(findings),
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
        "findings": [
            {
                "id": f.id,
                "rule_id": f.rule_id,
                "title": f.title,
                "category": f.category,
                "status": f.status,
                "severity": f.severity,
                "remediation_text": f.remediation_text,
            }
            for f in findings
        ],
    }


@router.get("/devices/{device_id}/findings")
def get_device_findings(
    device_id: int,
    framework: str = Query("CIS"),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found.")

    findings = (
        db.query(Finding)
        .filter(Finding.device_id == device_id, Finding.framework == framework)
        .all()
    )

    pass_count = sum(1 for f in findings if f.status == "pass")
    fail_count = sum(1 for f in findings if f.status == "fail")

    return {
        "device_id": device.id,
        "filename": device.filename,
        "vendor": device.vendor,
        "framework": framework,
        "summary": {
            "total_rules": len(findings),
            "pass_count": pass_count,
            "fail_count": fail_count,
        },
        "findings": [
            {
                "id": f.id,
                "rule_id": f.rule_id,
                "title": f.title,
                "category": f.category,
                "status": f.status,
                "severity": f.severity,
                "remediation_text": f.remediation_text,
            }
            for f in findings
        ],
    }
