"""Router for Phase 9 — Network Health & Multi-WAN Link Advisory."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.telemetry.advisor import generate_network_health_analysis
from app.telemetry.collector import ingest_telemetry_sample

router = APIRouter()


class TelemetrySampleRequest(BaseModel):
    device_name: str = "Border-GW-01"
    interface_name: str
    wan_tag: str = "WAN1_PRIMARY"
    utilization_pct: float
    latency_ms: float = 10.0
    packet_loss_pct: float = 0.0
    jitter_ms: float = 1.0


@router.get("/api/telemetry/health")
def get_telemetry_health(db: Session = Depends(get_db)):
    return generate_network_health_analysis(db)


@router.post("/api/telemetry/sample")
def add_telemetry_sample(payload: TelemetrySampleRequest, db: Session = Depends(get_db)):
    record = ingest_telemetry_sample(
        db,
        device_name=payload.device_name,
        interface_name=payload.interface_name,
        wan_tag=payload.wan_tag,
        utilization_pct=payload.utilization_pct,
        latency_ms=payload.latency_ms,
        packet_loss_pct=payload.packet_loss_pct,
        jitter_ms=payload.jitter_ms,
    )
    return {
        "status": "ok",
        "record_id": record.id,
        "health": generate_network_health_analysis(db),
    }
