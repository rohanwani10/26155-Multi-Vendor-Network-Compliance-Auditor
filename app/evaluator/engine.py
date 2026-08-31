"""Compliance Evaluation Engine.
Loads YAML rule packs (CIS / NIST / STIG / ISO), evaluates normalized schema
fields against expected conditions, and generates Finding records with pass/fail
status, severity, and vendor-specific CLI remediation commands."""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.models import Device, Finding, ParsedConfig

RULES_DIR = Path(__file__).parent.parent / "rules"


class EvaluatorError(RuntimeError):
    """Raised when a rule pack cannot be found or parsed."""


def load_rule_pack(framework: str = "CIS") -> dict:
    rule_file = RULES_DIR / f"{framework.lower()}.yaml"
    if not rule_file.exists():
        raise EvaluatorError(f"Rule pack for framework '{framework}' not found at {rule_file}")

    with rule_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _eval_condition(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "==" or operator == "equals":
        return actual == expected
    if operator == "!=":
        return actual != expected
    if operator == ">=":
        try:
            return float(actual or 0) >= float(expected)
        except (ValueError, TypeError):
            return False
    if operator == "<=":
        try:
            return float(actual or 0) <= float(expected)
        except (ValueError, TypeError):
            return False
    if operator == "contains":
        if isinstance(actual, (list, tuple, str)):
            return expected in actual
        return False
    # Default equality check
    return actual == expected


def evaluate_rule(rule: dict, schema: dict, vendor: str, framework_name: str = "CIS") -> dict:
    category = rule.get("category", "")
    field = rule.get("field", "")
    operator = rule.get("operator", "==")
    expected = rule.get("expected")

    cat_data = schema.get(category, {}) if isinstance(schema, dict) else {}
    actual_val = cat_data.get(field) if isinstance(cat_data, dict) else None

    passed = _eval_condition(actual_val, operator, expected)
    status = "pass" if passed else "fail"

    remediations = rule.get("remediation", {})
    remediation_text = remediations.get(vendor.lower(), remediations.get("default", ""))

    return {
        "rule_id": rule.get("id"),
        "framework": framework_name,
        "title": rule.get("title"),
        "category": category,
        "status": status,
        "severity": rule.get("severity", "MEDIUM"),
        "remediation_text": remediation_text,
    }


def evaluate_device(db: Session, device: Device, framework: str = "CIS") -> list[Finding]:
    parsed_config = (
        db.query(ParsedConfig)
        .filter(ParsedConfig.device_id == device.id)
        .order_by(ParsedConfig.id.desc())
        .first()
    )
    schema = parsed_config.normalized_json if parsed_config and parsed_config.normalized_json else {}

    rule_pack = load_rule_pack(framework)
    framework_name = rule_pack.get("framework", framework)

    # Clear existing findings for this device and framework before re-evaluating
    db.query(Finding).filter(
        Finding.device_id == device.id, Finding.framework == framework_name
    ).delete()
    db.flush()

    new_findings = []
    for rule in rule_pack.get("rules", []):
        eval_result = evaluate_rule(rule, schema, device.vendor, framework_name)
        finding = Finding(
            device_id=device.id,
            rule_id=eval_result["rule_id"],
            framework=eval_result["framework"],
            title=eval_result["title"],
            category=eval_result["category"],
            status=eval_result["status"],
            severity=eval_result["severity"],
            remediation_text=eval_result["remediation_text"],
        )
        db.add(finding)
        new_findings.append(finding)

    db.flush()
    return new_findings
