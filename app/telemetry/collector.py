"""Telemetry Collector Stub (SNMP/NetFlow metric ingestion)."""

from sqlalchemy.orm import Session
from app.models import TelemetryRecord


def ingest_telemetry_sample(
    db: Session,
    device_name: str,
    interface_name: str,
    wan_tag: str,
    utilization_pct: float,
    latency_ms: float = 10.0,
    packet_loss_pct: float = 0.0,
    jitter_ms: float = 1.0,
) -> TelemetryRecord:
    record = TelemetryRecord(
        device_name=device_name,
        interface_name=interface_name,
        wan_tag=wan_tag,
        utilization_pct=utilization_pct,
        latency_ms=latency_ms,
        packet_loss_pct=packet_loss_pct,
        jitter_ms=jitter_ms,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def seed_demo_telemetry_if_empty(db: Session):
    """Seed baseline Multi-WAN telemetry data if none exist."""
    count = db.query(TelemetryRecord).count()
    if count == 0:
        samples = [
            {
                "device_name": "Border-GW-01",
                "interface_name": "Gi0/0/0",
                "wan_tag": "WAN1_PRIMARY",
                "utilization_pct": 89.4,
                "latency_ms": 78.2,
                "packet_loss_pct": 2.8,
                "jitter_ms": 14.5,
            },
            {
                "device_name": "Border-GW-01",
                "interface_name": "Gi0/0/1",
                "wan_tag": "WAN2_SECONDARY",
                "utilization_pct": 24.1,
                "latency_ms": 18.5,
                "packet_loss_pct": 0.0,
                "jitter_ms": 2.1,
            },
            {
                "device_name": "Border-GW-01",
                "interface_name": "Gi0/1/0",
                "wan_tag": "LAN_INTERNAL",
                "utilization_pct": 14.8,
                "latency_ms": 1.2,
                "packet_loss_pct": 0.0,
                "jitter_ms": 0.3,
            },
        ]
        for s in samples:
            ingest_telemetry_sample(db, **s)
