from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LearnedRule, ParsedConfig, PendingReview
from app.pipeline import reprocess_config
from app.tier2.embeddings import learn_pattern

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/training", response_class=HTMLResponse)
def training_page(request: Request, db: Session = Depends(get_db)):
    pending_reviews = (
        db.query(PendingReview)
        .filter(PendingReview.status == "pending")
        .order_by(PendingReview.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        request, "training.html", {"pending_reviews": pending_reviews}
    )


@router.post("/training/resolve", response_class=HTMLResponse)
def resolve_pending(
    request: Request,
    review_id: int = Form(...),
    category: str = Form(...),
    field: str = Form(...),
    value: str = Form(None),
    db: Session = Depends(get_db),
):
    review = db.query(PendingReview).filter(PendingReview.id == review_id).first()
    if not review:
        pending_reviews = (
            db.query(PendingReview)
            .filter(PendingReview.status == "pending")
            .order_by(PendingReview.created_at.desc())
            .all()
        )
        return templates.TemplateResponse(
            request,
            "_pending_reviews_table.html",
            {"pending_reviews": pending_reviews, "message": "Review item not found."},
        )

    # 1. Create LearnedRule record
    learned_rule = LearnedRule(
        vendor=review.vendor,
        raw_pattern=review.raw_line,
        category=category,
        field=field,
        value=value,
        created_by="admin",
    )
    db.add(learned_rule)

    # 2. Update PendingReview status
    review.status = "resolved"

    # 3. Learn pattern in ChromaDB vector store
    learn_pattern(
        vendor=review.vendor,
        line=review.raw_line,
        category=category,
        field=field,
        value=value or "",
    )

    # 4. Re-normalize / re-apply Tier 2 on affected ParsedConfig
    parsed_config = db.query(ParsedConfig).filter(ParsedConfig.id == review.parsed_config_id).first()
    if parsed_config:
        reprocess_config(db, parsed_config)

    db.commit()

    # 5. Fetch updated list of pending reviews
    pending_reviews = (
        db.query(PendingReview)
        .filter(PendingReview.status == "pending")
        .order_by(PendingReview.created_at.desc())
        .all()
    )
    message = f"Successfully resolved '{review.raw_line}' → [{category}.{field} = '{value}']. Pattern saved & learned in ChromaDB!"
    return templates.TemplateResponse(
        request,
        "_pending_reviews_table.html",
        {"pending_reviews": pending_reviews, "message": message},
    )
