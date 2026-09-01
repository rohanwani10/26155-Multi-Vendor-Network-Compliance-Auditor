"""Phase 9 Tests — Network Health Monitoring & Multi-WAN Link Advisory.

These probe this host's *real* interfaces and reachability (see
app.telemetry.collector), so the exact numbers are environment-dependent —
the tests assert on response shape and internal consistency, not on fixed
canned values."""

from app.models import TelemetryRecord
from app.telemetry.collector import list_active_interfaces, measure_reachability


def test_get_telemetry_health_endpoint(client, db_session):
    """GET /api/telemetry/health returns a well-formed live diagnostic, whether
    or not this machine currently has an active network interface."""
    resp = client.get("/api/telemetry/health")
    assert resp.status_code == 200

    data = resp.json()
    assert "ai_advisory" in data
    assert len(data["ai_advisory"]) > 10

    if data["status"] == "no_connectivity":
        assert data["total_interfaces_monitored"] == 0
        assert data["multi_wan_comparison"] is None
        return

    assert data["status"] == "ok"
    assert data["total_interfaces_monitored"] >= 1

    wan_comp = data["multi_wan_comparison"]
    primary = wan_comp["primary_wan"]
    assert primary["name"] == "PRIMARY"
    assert primary["interface"]  # a real interface name, not a fixture placeholder
    assert 0 <= primary["utilization_pct"] <= 100

    # Every returned record must actually exist in the DB — collect_live_telemetry persists what it probes.
    for m in data["metrics"]:
        assert db_session.query(TelemetryRecord).filter(TelemetryRecord.id == m["id"]).first() is not None


def test_live_probe_matches_real_host_interfaces(db_session):
    """The interfaces collect_live_telemetry finds must be a subset of what
    psutil itself reports as up on this machine right now — i.e. it isn't
    inventing devices that don't exist."""
    real_interfaces = set(list_active_interfaces())
    from app.telemetry.collector import collect_live_telemetry

    records = collect_live_telemetry(db_session)
    assert {r.interface_name for r in records} <= real_interfaces


def test_measure_reachability_never_raises():
    """A real ping probe either succeeds with real numbers or degrades to an
    honest 'unreachable' result — it must never crash the request."""
    result = measure_reachability()
    assert isinstance(result["reachable"], bool)
    if result["reachable"]:
        assert result["latency_ms"] is not None and result["latency_ms"] >= 0
    else:
        assert result["packet_loss_pct"] == 100.0


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
