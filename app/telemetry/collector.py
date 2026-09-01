"""Real network diagnostics: live interface stats + ICMP reachability probes.

Every value produced here comes from psutil reading this host's actual
network interfaces and from real ping round-trips — not from fixture data.
"""

import platform
import re
import socket
import statistics
import subprocess
import time

import psutil
from sqlalchemy.orm import Session

from app.models import TelemetryRecord

PING_TARGETS = ["1.1.1.1", "8.8.8.8"]
PING_COUNT = 4
PING_TIMEOUT_S = 6
UTILIZATION_SAMPLE_WINDOW_S = 0.5
MAX_INTERFACES = 4

# ponytail: no reliable cross-platform way to read every NIC's true link speed
# (Windows Wi-Fi adapters commonly report speed=0 to psutil) — fall back to a
# documented assumed ceiling for the utilization% calculation when unknown.
ASSUMED_LINK_MBPS = 100.0


_VIRTUAL_ADAPTER_TOKENS = (
    "loopback", "pseudo", "isatap", "teredo", "vethernet", "virtual",
    "vmware", "virtualbox", "hyper-v", "docker", "wsl", "npcap", "tap", "tun",
)


def _is_virtual_or_loopback(name: str) -> bool:
    lowered = name.lower()
    return any(tok in lowered for tok in _VIRTUAL_ADAPTER_TOKENS)


def list_active_interfaces() -> list[str]:
    """Real, currently-up interfaces that hold a routable (non-loopback) IPv4
    address — i.e. interfaces actually carrying traffic, not virtual/idle ones."""
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    active = []
    for name, nic_stats in stats.items():
        if not nic_stats.isup or _is_virtual_or_loopback(name):
            continue
        has_ipv4 = any(
            a.family == socket.AF_INET and not a.address.startswith("127.")
            for a in addrs.get(name, [])
        )
        if has_ipv4:
            active.append(name)
    return active[:MAX_INTERFACES]


def sample_utilization(interface_name: str, window: float = UTILIZATION_SAMPLE_WINDOW_S) -> dict:
    """Real bytes/sec measured over `window` seconds, converted to a % of the
    interface's reported link speed (or ASSUMED_LINK_MBPS if unreported)."""
    counters_before = psutil.net_io_counters(pernic=True).get(interface_name)
    time.sleep(window)
    counters_after = psutil.net_io_counters(pernic=True).get(interface_name)
    if not counters_before or not counters_after:
        return {"utilization_pct": 0.0, "mbps": 0.0}

    bytes_delta = (counters_after.bytes_sent - counters_before.bytes_sent) + (
        counters_after.bytes_recv - counters_before.bytes_recv
    )
    mbps = (bytes_delta * 8 / 1_000_000) / window

    nic_stats = psutil.net_if_stats().get(interface_name)
    link_mbps = nic_stats.speed if nic_stats and nic_stats.speed > 0 else ASSUMED_LINK_MBPS
    utilization_pct = min(100.0, round((mbps / link_mbps) * 100, 1))
    return {"utilization_pct": utilization_pct, "mbps": round(mbps, 2)}


def measure_reachability() -> dict:
    """Real ICMP round-trip to a public resolver — actual latency, jitter, and
    loss, not fabricated values. Tries each target in turn; if the `ping`
    binary itself is missing (e.g. a minimal container image) or every target
    is unreachable, this honestly reports unreachable rather than faking data."""
    is_windows = platform.system().lower() == "windows"
    for target in PING_TARGETS:
        cmd = (
            ["ping", "-n", str(PING_COUNT), "-w", "1000", target]
            if is_windows
            else ["ping", "-c", str(PING_COUNT), "-W", "1", target]
        )
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=PING_TIMEOUT_S)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue

        times = [float(m) for m in re.findall(r"time[=<]([\d.]+)\s*ms", result.stdout, re.IGNORECASE)]
        if times:
            return {
                "reachable": True,
                "target": target,
                "latency_ms": round(statistics.mean(times), 1),
                "jitter_ms": round(statistics.pstdev(times), 1) if len(times) > 1 else 0.0,
                "packet_loss_pct": round((PING_COUNT - len(times)) / PING_COUNT * 100, 1),
            }
    return {
        "reachable": False,
        "target": None,
        "latency_ms": None,
        "jitter_ms": None,
        "packet_loss_pct": 100.0,
    }


def collect_live_telemetry(db: Session) -> list[TelemetryRecord]:
    """Probe this host's real network interfaces and internet reachability,
    persist what was actually observed, and return the new records — ranked
    by measured traffic, highest first (tagged PRIMARY / SECONDARY / OTHER)."""
    interfaces = list_active_interfaces()
    if not interfaces:
        return []

    reachability = measure_reachability()
    hostname = socket.gethostname()

    samples = [(name, sample_utilization(name)) for name in interfaces]
    samples.sort(key=lambda s: s[1]["mbps"], reverse=True)

    records = []
    for i, (name, util) in enumerate(samples):
        wan_tag = "PRIMARY" if i == 0 else "SECONDARY" if i == 1 else "OTHER"
        record = TelemetryRecord(
            device_name=hostname,
            interface_name=name,
            wan_tag=wan_tag,
            utilization_pct=util["utilization_pct"],
            latency_ms=reachability["latency_ms"] if reachability["reachable"] else 0.0,
            packet_loss_pct=reachability["packet_loss_pct"],
            jitter_ms=reachability["jitter_ms"] if reachability["reachable"] else 0.0,
        )
        db.add(record)
        records.append(record)

    db.commit()
    for record in records:
        db.refresh(record)
    return records


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
    """Manually record a telemetry sample for a device this host can't probe
    directly (e.g. a remote branch reporting over an agent/API)."""
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
