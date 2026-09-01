"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { LayoutDashboard, ShieldAlert, CheckCircle2, XCircle, AlertTriangle, Download, Loader2 } from "lucide-react";

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

const API_BASE = "http://localhost:8000";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/dashboard/stats`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error("Failed to fetch dashboard stats:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col justify-center items-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span>Loading executive compliance stats from FastAPI...</span>
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

  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight flex items-center space-x-3">
          <LayoutDashboard className="w-8 h-8 text-cyan-400" />
          <span>Compliance Dashboard</span>
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Aggregated security compliance posture across all audited network devices.
        </p>
      </div>

      {/* Summary Metrics Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="text-xs uppercase font-medium text-slate-400 tracking-wider">Devices</div>
          <div className="text-3xl font-bold text-blue-400 mt-2">{total_devices}</div>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="text-xs uppercase font-medium text-slate-400 tracking-wider">Total Findings</div>
          <div className="text-3xl font-bold text-slate-200 mt-2">{total_findings}</div>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="text-xs uppercase font-medium text-slate-400 tracking-wider">Passed Rules</div>
          <div className="text-3xl font-bold text-emerald-400 mt-2">{total_pass}</div>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
          <div className="text-xs uppercase font-medium text-slate-400 tracking-wider">Failed Rules</div>
          <div className="text-3xl font-bold text-rose-400 mt-2">{total_fail}</div>
        </div>
        <div className="bg-slate-900/80 border border-rose-900/40 rounded-xl p-5 shadow-lg bg-gradient-to-br from-rose-950/40 to-slate-900/60">
          <div className="text-xs uppercase font-medium text-rose-400 tracking-wider flex items-center space-x-1">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Critical Fails</span>
          </div>
          <div className="text-3xl font-bold text-rose-400 mt-2">
            {severity_counts["CRITICAL"] || 0}
          </div>
        </div>
      </div>

      {/* Severity Breakdown Visualizer */}
      {total_findings > 0 && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <h2 className="text-lg font-semibold text-white">Failed Findings by Severity</h2>
          <div className="space-y-3">
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => {
              const count = severity_counts[sev] || 0;
              const pct = total_fail > 0 ? Math.round((count / total_fail) * 100) : 0;
              return (
                <div key={sev} className="flex items-center gap-4 text-xs font-medium">
                  <span className="w-20 font-bold uppercase tracking-wider text-right text-slate-400">
                    {sev}
                  </span>
                  <div className="flex-grow bg-slate-950 rounded-lg h-6 overflow-hidden border border-slate-800 flex items-center p-1">
                    <div
                      className={`h-full rounded-md flex items-center px-2 font-mono font-bold text-white transition-all duration-500 ${
                        sev === "CRITICAL"
                          ? "bg-rose-600"
                          : sev === "HIGH"
                          ? "bg-orange-600"
                          : sev === "MEDIUM"
                          ? "bg-amber-600"
                          : "bg-lime-600"
                      }`}
                      style={{ width: `${Math.max(pct, 4)}%` }}
                    >
                      {count}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Audited Devices Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl space-y-0">
        <div className="px-6 py-4 border-b border-slate-800">
          <h2 className="text-lg font-semibold text-white">Devices — Worst Compliance Offenders First</h2>
        </div>
        <div className="overflow-x-auto">
          {device_summaries.length > 0 ? (
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-950/60 text-slate-400 font-semibold border-b border-slate-800 uppercase text-xs tracking-wider">
                  <th className="px-6 py-3.5">Device</th>
                  <th className="px-6 py-3.5">Vendor</th>
                  <th className="px-6 py-3.5">Framework</th>
                  <th className="px-6 py-3.5">Passed</th>
                  <th className="px-6 py-3.5">Failed</th>
                  <th className="px-6 py-3.5">Worst Severity</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {device_summaries.map((ds) => (
                  <tr key={`${ds.device_id}-${ds.framework}`} className="hover:bg-slate-800/40 transition">
                    <td className="px-6 py-4 font-medium text-white">{ds.filename}</td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-0.5 rounded text-xs font-semibold uppercase bg-slate-800 text-slate-200 border border-slate-700">
                        {ds.vendor}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-cyan-400">{ds.framework}</td>
                    <td className="px-6 py-4 text-emerald-400 font-medium">{ds.pass_count}</td>
                    <td className="px-6 py-4 text-rose-400 font-medium">{ds.fail_count}</td>
                    <td className="px-6 py-4">
                      {ds.worst_severity ? (
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                            ds.worst_severity === "CRITICAL"
                              ? "bg-rose-950 text-rose-300 border border-rose-800"
                              : ds.worst_severity === "HIGH"
                              ? "bg-orange-950 text-orange-300 border border-orange-800"
                              : ds.worst_severity === "MEDIUM"
                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                              : "bg-lime-950 text-lime-300 border border-lime-800"
                          }`}
                        >
                          {ds.worst_severity}
                        </span>
                      ) : (
                        <span className="text-xs font-medium text-emerald-400 flex items-center space-x-1">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>All Clear</span>
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right space-x-3">
                      <Link
                        href={`/reports/${ds.device_id}?framework=${ds.framework}`}
                        className="text-cyan-400 hover:text-cyan-300 font-medium text-xs hover:underline"
                      >
                        View Report
                      </Link>
                      <a
                        href={`${API_BASE}/devices/${ds.device_id}/report.pdf?framework=${ds.framework}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center text-slate-400 hover:text-slate-200 font-medium text-xs hover:underline"
                      >
                        <Download className="w-3.5 h-3.5 mr-1" />
                        PDF
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-12 text-center text-slate-500 text-sm">
              No evaluated devices yet. Upload a config and run an evaluation to see results here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
