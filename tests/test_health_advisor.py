"""Phase 9 Tests — Network Health Monitoring & Multi-WAN Link Advisory."""

from app.models import TelemetryRecord


def test_get_telemetry_health_endpoint(client, db_session):
    """Test GET /api/telemetry/health returns auto-seeded telemetry and AI link advisory."""
    resp = client.get("/api/telemetry/health")
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert data["total_interfaces_monitored"] >= 3
    assert len(data["congestion_spikes"]) >= 1

    wan_comp = data["multi_wan_comparison"]
    assert "primary_wan" in wan_comp
    assert "secondary_wan" in wan_comp
    assert wan_comp["recommended_path"] in ["WAN1_PRIMARY", "WAN2_SECONDARY"]

    assert "ai_advisory" in data
    assert len(data["ai_advisory"]) > 10


def test_add_telemetry_sample_endpoint(client, db_session):
    """Test POST /api/telemetry/sample creates a new TelemetryRecord."""
    payload = {
        "device_name": "Core-GW-02",
        "interface_name": "Gi0/0/2",
        "wan_tag": "WAN1_PRIMARY",
        "utilization_pct": 95.5,
        "latency_ms": 120.0,
        "packet_loss_pct": 5.2,
        "jitter_ms": 25.0,
    }
    resp = client.post("/api/telemetry/sample", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "ok"
    assert "record_id" in data

    record = db_session.query(TelemetryRecord).filter(TelemetryRecord.id == data["record_id"]).first()
    assert record is not None
    assert record.device_name == "Core-GW-02"
    assert record.utilization_pct == 95.5
    assert record.packet_loss_pct == 5.2
