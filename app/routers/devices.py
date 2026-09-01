from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import extract_files
from app.models import Device
from app.pipeline import ingest_one

router = APIRouter()


@router.get("/devices")
@router.get("/api/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).order_by(Device.uploaded_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "vendor": d.vendor,
            "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
        }
        for d in devices
    ]


@router.post("/devices/upload")
@router.post("/api/devices/upload")
async def upload_device(file: UploadFile, db: Session = Depends(get_db)):
    content = await file.read()
    ingested = []
    for name, text in extract_files(file.filename, content):
        device = ingest_one(db, name, text)
        ingested.append(device)
    db.commit()

    devices = db.query(Device).order_by(Device.uploaded_at.desc()).all()
    return {
        "status": "ok",
        "ingested_count": len(ingested),
        "devices": [
            {
                "id": d.id,
                "filename": d.filename,
                "vendor": d.vendor,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
            }
            for d in devices
        ],
    }


