"""Shared ingest pipeline: vendor-detect -> Tier-1 normalize -> Tier-2
fallback for whatever Tier-1 left unrecognized. Used by the upload endpoint
and (from Phase 4 on) by the training-resolve endpoint's re-normalize step,
so both paths stay in sync."""

from sqlalchemy.orm import Session

from app.models import Device, ParsedConfig, PendingReview
from app.parsers import normalize
from app.tier2.fallback import classify_line, is_applicable, is_confident
from app.vendor_detect import detect_vendor


def parse_typed_value(val: any) -> any:
    if isinstance(val, str):
        lowered = val.strip().lower()
        if lowered in ("true", "yes", "enabled", "on"):
            return True
        if lowered in ("false", "no", "disabled", "off"):
            return False
        if val.strip().isdigit():
            return int(val.strip())
    return val


def ingest_one(db: Session, filename: str, text: str) -> Device:
    vendor = detect_vendor(filename, text)
    device = Device(filename=filename, vendor=vendor)
    db.add(device)
    db.flush()

    parsed_config = ParsedConfig(device_id=device.id, raw_text=text, parse_tier=1)
    db.add(parsed_config)
    db.flush()

    apply_tier2(db, device, parsed_config, vendor, text)
    return device


def apply_tier2(db: Session, device: Device, parsed_config: ParsedConfig, vendor: str, text: str) -> None:
    """Tier-1 normalize, then Tier-2-classify every line Tier-1 couldn't
    map. Confident+applicable results are merged straight into the schema;
    everything else is queued as a PendingReview row, never silently
    dropped or silently guessed into the schema."""
    schema = normalize(vendor, text)
    tier2_invoked = bool(schema["unrecognized_lines"])

    still_unrecognized = []
    applied_confidences = []
    for line in schema["unrecognized_lines"]:
        result = classify_line(vendor, line)
        if is_confident(result) and is_applicable(result):
            schema[result["category"]][result["field"]] = parse_typed_value(result["value"])
            applied_confidences.append(result["confidence"])
        else:
            still_unrecognized.append(line)
            db.add(
                PendingReview(
                    device_id=device.id,
                    parsed_config_id=parsed_config.id,
                    vendor=vendor,
                    raw_line=line,
                    suggested_category=result.get("category"),
                    suggested_field=result.get("field"),
                    suggested_value=None if result.get("value") is None else str(result["value"]),
                    confidence=result.get("confidence"),
                )
            )
    schema["unrecognized_lines"] = still_unrecognized

    parsed_config.normalized_json = schema
    parsed_config.parse_tier = 2 if tier2_invoked else 1
    parsed_config.confidence_score = (
        sum(applied_confidences) / len(applied_confidences) if applied_confidences else None
    )
    db.flush()



def reprocess_config(db: Session, parsed_config: ParsedConfig) -> None:
    """Re-normalizes a ParsedConfig after a new rule has been learned.
    Deletes existing PendingReview rows for this config and re-runs Tier-2,
    which will now match learned Chroma patterns and update the schema."""
    db.query(PendingReview).filter(PendingReview.parsed_config_id == parsed_config.id).delete()
    db.flush()
    device = parsed_config.device
    apply_tier2(db, device, parsed_config, device.vendor, parsed_config.raw_text)

