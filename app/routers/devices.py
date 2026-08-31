from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import extract_files
from app.models import Device
from app.pipeline import ingest_one

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request, db: Session = Depends(get_db)):
    devices = db.query(Device).order_by(Device.uploaded_at.desc()).all()
    return templates.TemplateResponse(request, "upload.html", {"devices": devices})


@router.post("/devices/upload", response_class=HTMLResponse)
async def upload_device(request: Request, file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    for name, text in extract_files(file.filename, content):
        ingest_one(db, name, text)
    db.commit()

    devices = db.query(Device).order_by(Device.uploaded_at.desc()).all()
    return templates.TemplateResponse(request, "_device_list.html", {"devices": devices})
