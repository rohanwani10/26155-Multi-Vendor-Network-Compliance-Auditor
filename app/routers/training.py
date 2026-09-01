from fastapi import APIRouter, Depends, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LearnedRule, ParsedConfig, PendingReview
from app.pipeline import reprocess_config
from app.tier2.embeddings import learn_pattern

router = APIRouter()


class ResolveRequest(BaseModel):
    review_id: int
    category: str
    field: str
    value: str | None = None


@router.get("/training")
@router.get("/api/training/pending")
def get_pending_reviews(db: Session = Depends(get_db)):
    pending_reviews = (
        db.query(PendingReview)
        .filter(PendingReview.status == "pending")
        .order_by(PendingReview.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "parsed_config_id": r.parsed_config_id,
            "device_id": r.device_id,
            "vendor": r.vendor,
            "raw_line": r.raw_line,
            "confidence": r.confidence,
            "suggested_category": r.suggested_category,
            "suggested_field": r.suggested_field,
            "suggested_value": r.suggested_value,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in pending_reviews
    ]


def _process_resolve(db: Session, review_id: int, category: str, field: str, value: str | None):
    review = db.query(PendingReview).filter(PendingReview.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review item not found.")

    learned_rule = LearnedRule(
        vendor=review.vendor,
        raw_pattern=review.raw_line,
        category=category,
        field=field,
        value=value,
        created_by="admin",
    )
    db.add(learned_rule)
    review.status = "resolved"

    learn_pattern(
        vendor=review.vendor,
        line=review.raw_line,
        category=category,
        field=field,
        value=value or "",
    )

    parsed_config = db.query(ParsedConfig).filter(ParsedConfig.id == review.parsed_config_id).first()
    if parsed_config:
        reprocess_config(db, parsed_config)

    db.commit()

    pending_reviews = (
        db.query(PendingReview)
        .filter(PendingReview.status == "pending")
        .order_by(PendingReview.created_at.desc())
        .all()
    )

    return {
        "status": "ok",
        "message": f"Successfully resolved '{review.raw_line}' → [{category}.{field} = '{value}']. Pattern saved & learned in ChromaDB!",
        "pending_reviews": [
            {
                "id": r.id,
                "parsed_config_id": r.parsed_config_id,
                "device_id": r.device_id,
                "vendor": r.vendor,
                "raw_line": r.raw_line,
                "confidence": r.confidence,
                "suggested_category": r.suggested_category,
                "suggested_field": r.suggested_field,
                "suggested_value": r.suggested_value,
                "status": r.status,
            }
            for r in pending_reviews
        ],
    }


@router.post("/api/training/resolve")
def resolve_pending_json(payload: ResolveRequest, db: Session = Depends(get_db)):
    return _process_resolve(db, payload.review_id, payload.category, payload.field, payload.value)


@router.post("/training/resolve")
def resolve_pending_form(
    review_id: int = Form(...),
    category: str = Form(...),
    field: str = Form(...),
    value: str = Form(None),
    db: Session = Depends(get_db),
):
    return _process_resolve(db, review_id, category, field, value)

