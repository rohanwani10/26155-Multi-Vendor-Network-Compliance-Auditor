"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Download,
  Loader2,
  Activity,
  Radio,
  Cpu,
  RefreshCw,
} from "lucide-react";

interface DeviceSummary {
  device_id: number;
  filename: string;
  vendor: string;
  framework: string;
  pass_count: number;
  fail_count: number;
  worst_severity: string | null;
}

interface DashboardStats {
  total_devices: number;
  total_findings: number;
  total_pass: number;
  total_fail: number;
  severity_counts: Record<string, number>;
  device_summaries: DeviceSummary[];
}

interface WanStatus {
  name: string;
  interface: string;
  utilization_pct: number;
  latency_ms: number;
  loss_pct: number;
  status: string;
}

interface TelemetryHealthData {
  status: string;
  total_interfaces_monitored: number;
  congestion_spikes: {
    interface: string;
    wan_tag: string;
    severity: string;
    utilization_pct: number;
    latency_ms: number;
    packet_loss_pct: number;
    message: string;
  }[];
  multi_wan_comparison: {
    primary_wan: WanStatus;
    secondary_wan: WanStatus | null;
    recommended_path: string;
  } | null;
  ai_advisory: string;
  metrics: { device_name: string }[];
}

const API_BASE = "http://localhost:8000";

const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: "bg-ember text-paper",
  HIGH: "bg-ember/10 text-ember",
  MEDIUM: "bg-canvas text-ink-soft border border-hairline",
  LOW: "border border-hairline text-mid-gray",
};

const SEVERITY_BAR: Record<string, string> = {
  CRITICAL: "bg-ember text-paper",
  HIGH: "bg-ember/25 text-ember",
  MEDIUM: "bg-ink-soft text-paper",
  LOW: "bg-hairline text-ink-soft",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryHealthData | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [telemetryLoading, setTelemetryLoading] = useState(true);

  const fetchTelemetry = () => {
    setTelemetryLoading(true);
    return fetch(`${API_BASE}/api/telemetry/health`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => data && setTelemetry(data))
      .catch((err) => console.error("Failed to fetch telemetry health:", err))
      .finally(() => setTelemetryLoading(false));
  };

  useEffect(() => {
    // Independent requests: compliance stats resolve in well under a second,
    // while telemetry/health calls the local Ollama model synchronously and
    // can take several seconds. Fetching them in parallel — instead of
    // awaiting one after the other — means the page never waits on the slow
    // one to show the fast one.
    fetch(`${API_BASE}/api/dashboard/stats`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => data && setStats(data))
      .catch((err) => console.error("Failed to fetch dashboard stats:", err))
      .finally(() => setStatsLoading(false));

    fetchTelemetry();
  }, []);

  if (statsLoading) {
    return (
      <div className="p-12 text-center text-mid-gray flex flex-col justify-center items-center gap-3 text-sm">
        <Loader2 className="w-6 h-6 animate-spin" />
        <span>Loading compliance data…</span>
      </div>
    );
  }

  const {
    total_devices = 0,
    total_findings = 0,
    total_pass = 0,
    total_fail = 0,
    severity_counts = {},
    device_summaries = [],
  } = stats || {};

  const { congestion_spikes = [], multi_wan_comparison, ai_advisory } = telemetry || {};

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-heading font-semibold text-ink">Dashboard</h1>
        <p className="mt-1.5 text-sm text-mid-gray">
          Aggregated compliance posture and network health across all audited devices.
        </p>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
          <div className="text-caption uppercase font-medium text-mid-gray">Devices</div>
          <div className="text-heading font-semibold text-ink mt-1">{total_devices}</div>
        </div>
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
          <div className="text-caption uppercase font-medium text-mid-gray">Findings</div>
          <div className="text-heading font-semibold text-ink mt-1">{total_findings}</div>
        </div>
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
          <div className="text-caption uppercase font-medium text-mid-gray">Passed</div>
          <div className="text-heading font-semibold text-ink mt-1">{total_pass}</div>
        </div>
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
          <div className="text-caption uppercase font-medium text-mid-gray">Failed</div>
          <div className="text-heading font-semibold text-ink mt-1">{total_fail}</div>
        </div>
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
          <div className="text-caption uppercase font-medium text-mid-gray flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" strokeWidth={2} />
            Critical
          </div>
          <div className="text-heading font-semibold text-ember mt-1">
            {severity_counts["CRITICAL"] || 0}
          </div>
        </div>
      </div>

      {/* Network health advisory (Phase 9) — loads independently of the stats
          above since it waits on a local Ollama generation call (several
          seconds); it never blocks the rest of the dashboard from showing. */}
      {(telemetryLoading || telemetry) && (
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5 space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-hairline pb-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-nested bg-canvas border border-hairline flex items-center justify-center shrink-0">
                <Activity className="w-4 h-4 text-ink" strokeWidth={2} />
              </div>
              <div>
                <h2 className="text-body-lg font-medium text-ink">Network health &amp; multi-WAN advisory</h2>
                <p className="text-xs text-mid-gray">
                  Live probe of this host&apos;s real network interfaces — psutil counters + ICMP round-trips,
                  reasoned over by an air-gapped LLM
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <span className="px-2.5 py-1 bg-canvas border border-hairline text-ink-soft text-xs font-mono rounded-pill font-medium">
                Air-gapped module
              </span>
              <button
                onClick={fetchTelemetry}
                disabled={telemetryLoading}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-pill border border-hairline text-xs font-medium text-ink hover:bg-canvas transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${telemetryLoading ? "animate-spin" : ""}`} strokeWidth={2} />
                Rescan
              </button>
            </div>
          </div>

          {telemetryLoading && (
            <div className="py-8 text-center text-mid-gray flex flex-col items-center gap-2 text-sm">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Sampling real interface counters and pinging a public resolver…</span>
            </div>
          )}

          {!telemetryLoading && telemetry?.status === "no_connectivity" && (
            <div className="py-8 text-center text-mid-gray text-sm">
              No active network interface with a routable address was detected on this host.
            </div>
          )}

          {!telemetryLoading && telemetry && (
            <p className="text-xs text-mid-gray -mt-1">
              Probed <span className="text-ink font-medium">{telemetry.metrics[0]?.device_name}</span> just now —{" "}
              {telemetry.total_interfaces_monitored} active interface
              {telemetry.total_interfaces_monitored === 1 ? "" : "s"} detected.
            </p>
          )}

          {multi_wan_comparison && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[multi_wan_comparison.primary_wan, multi_wan_comparison.secondary_wan].map((wan, i) =>
                wan ? (
                <div key={i} className="p-4 rounded-nested border border-hairline bg-canvas">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Radio className="w-3.5 h-3.5 text-ink-soft" strokeWidth={2} />
                      <span className="text-xs font-semibold uppercase tracking-wide text-ink">
                        {wan.name} ({wan.interface})
                      </span>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded-pill text-xs font-medium ${
                        wan.status === "Congested"
                          ? "bg-ember/10 text-ember"
                          : "border border-hairline text-mid-gray"
                      }`}
                    >
                      {wan.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-3.5 text-center">
                    <div className="bg-paper p-2 rounded-[6px] border border-hairline">
                      <div className="text-caption text-mid-gray uppercase font-medium">Util</div>
                      <div className="text-sm font-mono font-semibold text-ink">{wan.utilization_pct}%</div>
                    </div>
                    <div className="bg-paper p-2 rounded-[6px] border border-hairline">
                      <div className="text-caption text-mid-gray uppercase font-medium">Latency</div>
                      <div className="text-sm font-mono font-semibold text-ink">{wan.latency_ms}ms</div>
                    </div>
                    <div className="bg-paper p-2 rounded-[6px] border border-hairline">
                      <div className="text-caption text-mid-gray uppercase font-medium">Loss</div>
                      <div className="text-sm font-mono font-semibold text-ink">{wan.loss_pct}%</div>
                    </div>
                  </div>
                </div>
                ) : (
                  <div
                    key={i}
                    className="p-4 rounded-nested border border-dashed border-hairline bg-canvas flex items-center justify-center text-xs text-mid-gray"
                  >
                    No secondary link detected on this host
                  </div>
                )
              )}
            </div>
          )}

          {congestion_spikes.length > 0 && (
            <div className="space-y-2">
              <div className="text-caption uppercase font-medium text-mid-gray flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5" strokeWidth={2} />
                Active congestion alerts
              </div>
              {congestion_spikes.map((spike, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-ember/5 border border-ember/20 text-ink rounded-nested text-xs flex items-center justify-between gap-3"
                >
                  <span>{spike.message}</span>
                  <span className={`px-2 py-0.5 rounded-pill font-medium shrink-0 ${SEVERITY_BADGE[spike.severity] || "bg-canvas text-mid-gray border border-hairline"}`}>
                    {spike.severity}
                  </span>
                </div>
              ))}
            </div>
          )}

          {ai_advisory && (
            <div className="p-4 bg-canvas border border-hairline rounded-nested space-y-2">
              <div className="text-caption uppercase font-medium text-mid-gray flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" strokeWidth={2} />
                Advisory
              </div>
              <p className="text-xs text-ink-soft leading-relaxed font-mono">{ai_advisory}</p>
            </div>
          )}
        </div>
      )}

      {/* Severity breakdown */}
      {total_findings > 0 && (
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5 space-y-4">
          <div>
            <h2 className="text-body-lg font-medium text-ink">Failed findings by severity</h2>
            <p className="text-xs text-mid-gray mt-0.5">
              <span className="text-ink font-medium">{total_pass}</span> of{" "}
              <span className="text-ink font-medium">{total_findings}</span> evaluated rules passed —{" "}
              <span className="text-ink font-medium">
                {total_findings > 0 ? Math.round((total_pass / total_findings) * 100) : 0}%
              </span>{" "}
              compliant across all audited devices.
            </p>
          </div>
          <div className="space-y-2.5">
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => {
              const count = severity_counts[sev] || 0;
              const pct = total_fail > 0 ? Math.round((count / total_fail) * 100) : 0;
              const isEmpty = count === 0;
              return (
                <div key={sev} className="flex items-center gap-4 text-xs">
                  <span
                    className={`w-20 font-medium uppercase tracking-wide text-right shrink-0 ${
                      isEmpty ? "text-hairline" : "text-mid-gray"
                    }`}
                  >
                    {sev}
                  </span>
                  <div className="flex-grow bg-canvas rounded-pill h-3 overflow-hidden border border-hairline">
                    <div
                      className={`h-full rounded-pill transition-all duration-500 ${
                        isEmpty ? "" : SEVERITY_BAR[sev].split(" ")[0]
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span
                    className={`w-16 shrink-0 font-mono text-right ${
                      isEmpty ? "text-hairline" : "text-ink font-medium"
                    }`}
                  >
                    {count}
                    {!isEmpty && <span className="text-mid-gray font-normal"> · {pct}%</span>}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Devices table */}
      <div className="bg-paper border border-hairline rounded-card shadow-subtle overflow-hidden">
        <div className="px-5 py-4 border-b border-hairline">
          <h2 className="text-body-lg font-medium text-ink">Devices — worst offenders first</h2>
        </div>
        <div className="overflow-x-auto">
          {device_summaries.length > 0 ? (
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="text-mid-gray font-medium border-b border-hairline uppercase text-caption">
                  <th className="px-5 py-3">Device</th>
                  <th className="px-5 py-3">Vendor</th>
                  <th className="px-5 py-3">Framework</th>
                  <th className="px-5 py-3">Passed</th>
                  <th className="px-5 py-3">Failed</th>
                  <th className="px-5 py-3">Worst severity</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline text-ink">
                {device_summaries.map((ds) => (
                  <tr key={`${ds.device_id}-${ds.framework}`} className="hover:bg-canvas/60 transition-colors">
                    <td className="px-5 py-3.5 font-medium">{ds.filename}</td>
                    <td className="px-5 py-3.5">
                      <span className="px-2 py-0.5 rounded-pill text-xs font-medium bg-canvas text-ink-soft border border-hairline">
                        {ds.vendor}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs text-mid-gray">{ds.framework}</td>
                    <td className="px-5 py-3.5 text-ink-soft font-medium">{ds.pass_count}</td>
                    <td className="px-5 py-3.5 text-ember font-medium">{ds.fail_count}</td>
                    <td className="px-5 py-3.5">
                      {ds.worst_severity ? (
                        <span className={`px-2 py-0.5 rounded-pill text-xs font-medium ${SEVERITY_BADGE[ds.worst_severity] || "bg-canvas text-mid-gray border border-hairline"}`}>
                          {ds.worst_severity}
                        </span>
                      ) : (
                        <span className="text-xs text-mid-gray flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={2} />
                          Clear
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-4">
                      <Link
                        href={`/reports/${ds.device_id}?framework=${ds.framework}`}
                        className="text-ink hover:text-mid-gray font-medium text-xs"
                      >
                        View report
                      </Link>
                      <a
                        href={`${API_BASE}/devices/${ds.device_id}/report.pdf?framework=${ds.framework}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center text-mid-gray hover:text-ink font-medium text-xs"
                      >
                        <Download className="w-3 h-3 mr-1" strokeWidth={2} />
                        PDF
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-14 text-center text-mid-gray text-sm">
              No evaluated devices yet. Upload a config and run an evaluation to see results here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
