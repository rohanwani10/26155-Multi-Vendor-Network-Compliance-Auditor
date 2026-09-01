"""Congestion & Multi-WAN Link Advisory Engine using Local Ollama LLM.

Reasons over telemetry collected in app.telemetry.collector — real, live
interface/reachability probes of this host, not fixture data."""

import os
import requests
from sqlalchemy.orm import Session
from app.telemetry.collector import collect_live_telemetry

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def _prompt_llm_advisory(prompt: str, fallback: str) -> str:
    """Send the health advisory prompt to local Ollama; fall back to a
    template built from the same real numbers if it's offline or un-pulled."""
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            if text:
                return text
    except Exception:
        pass
    return fallback


def generate_network_health_analysis(db: Session) -> dict:
    """Probe this host's real network interfaces and reachability, detect
    congestion, and build a Multi-WAN advisory from what was actually observed."""
    records = collect_live_telemetry(db)

    if not records:
        return {
            "status": "no_connectivity",
            "total_interfaces_monitored": 0,
            "congestion_spikes": [],
            "multi_wan_comparison": None,
            "ai_advisory": "No active network interface with a routable address was detected on this host.",
            "metrics": [],
        }

    # Detect congestion spikes (> 80% utilization or > 1% packet loss)
    spikes = []
    for link in records:
        if link.utilization_pct >= 80.0 or link.packet_loss_pct >= 1.0:
            spikes.append(
                {
                    "interface": link.interface_name,
                    "wan_tag": link.wan_tag,
                    "severity": "CRITICAL" if link.utilization_pct >= 85.0 else "WARNING",
                    "utilization_pct": link.utilization_pct,
                    "latency_ms": link.latency_ms,
                    "packet_loss_pct": link.packet_loss_pct,
                    "message": f"High congestion on {link.interface_name} ({link.wan_tag}): {link.utilization_pct}% utilization, {link.packet_loss_pct}% loss.",
                }
            )

    primary = records[0]
    secondary = records[1] if len(records) > 1 else None

    def _wan_status(link):
        return {
            "name": link.wan_tag,
            "interface": link.interface_name,
            "utilization_pct": link.utilization_pct,
            "latency_ms": link.latency_ms,
            "loss_pct": link.packet_loss_pct,
            "status": "Congested" if link.utilization_pct > 80 else "Optimal",
        }

    comparison = {
        "primary_wan": _wan_status(primary),
        "secondary_wan": _wan_status(secondary) if secondary else None,
        "recommended_path": (
            secondary.wan_tag
            if secondary and primary.utilization_pct > 80 and secondary.utilization_pct <= 80
            else primary.wan_tag
        ),
    }

    # Deterministic fallback (used verbatim if Ollama is offline): built from
    # this run's real numbers, not a canned scenario.
    if secondary:
        fallback = (
            f"Live diagnostics: {primary.interface_name} ({primary.wan_tag}) at "
            f"{primary.utilization_pct}% utilization, {primary.packet_loss_pct}% loss, "
            f"{primary.latency_ms}ms latency; {secondary.interface_name} ({secondary.wan_tag}) at "
            f"{secondary.utilization_pct}% utilization. "
            f"{'Recommend shifting traffic to ' + secondary.interface_name + '.' if comparison['recommended_path'] == secondary.wan_tag else 'Primary link is within normal range.'}"
        )
    else:
        fallback = (
            f"Live diagnostics: {primary.interface_name} is the only active interface detected, at "
            f"{primary.utilization_pct}% utilization, {primary.packet_loss_pct}% loss, "
            f"{primary.latency_ms}ms latency. No secondary link is available for failover."
        )

    prompt = (
        f"Real-time network telemetry for host interface {primary.interface_name} ({primary.wan_tag}): "
        f"utilization {primary.utilization_pct}%, loss {primary.packet_loss_pct}%, latency {primary.latency_ms}ms.\n"
        + (
            f"Secondary interface {secondary.interface_name} ({secondary.wan_tag}): "
            f"utilization {secondary.utilization_pct}%, loss {secondary.packet_loss_pct}%, latency {secondary.latency_ms}ms.\n"
            if secondary
            else "No secondary interface is active.\n"
        )
        + "Provide a 2-sentence executive network link advisory for routing optimization based on these actual readings."
    )

    ai_advisory = _prompt_llm_advisory(prompt, fallback)

    return {
        "status": "ok",
        "total_interfaces_monitored": len(records),
        "congestion_spikes": spikes,
        "multi_wan_comparison": comparison,
        "ai_advisory": ai_advisory,
        "metrics": [
            {
                "id": r.id,
                "device_name": r.device_name,
                "interface_name": r.interface_name,
                "wan_tag": r.wan_tag,
                "utilization_pct": r.utilization_pct,
                "latency_ms": r.latency_ms,
                "packet_loss_pct": r.packet_loss_pct,
                "jitter_ms": r.jitter_ms,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in records
        ],
    }
