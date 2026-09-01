"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { FileCheck, Download, CheckCircle2, XCircle, Shield, Copy, Check, Loader2 } from "lucide-react";

interface Finding {
  id: number;
  rule_id: string;
  title: string;
  category: string;
  status: "pass" | "fail";
  severity: string;
  remediation_text: string | null;
}

interface ReportData {
  device: {
    id: number;
    filename: string;
    vendor: string;
    uploaded_at: string | null;
  };
  framework: string;
  pass_count: number;
  fail_count: number;
  total_rules: number;
  grouped_findings: Record<string, Finding[]>;
}

const API_BASE = "http://localhost:8000";

export default function ReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const deviceId = params.id as string;
  const currentFramework = searchParams.get("framework") || "CIS";

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const fetchReport = async (fw: string) => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/devices/${deviceId}/report?framework=${fw}`
      );
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      } else {
        alert(`Device ${deviceId} not found.`);
      }
    } catch (err) {
      console.error("Failed to fetch report:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (deviceId) {
      fetchReport(currentFramework);
    }
  }, [deviceId, currentFramework]);

  const handleFrameworkChange = (fw: string) => {
    router.push(`/reports/${deviceId}?framework=${fw}`);
  };

  const handleCopyRemediation = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 flex flex-col justify-center items-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
        <span>Evaluating configuration and generating compliance report...</span>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-12 text-center text-slate-500">
        Report not found for device #{deviceId}.
      </div>
    );
  }

  const { device, framework, pass_count, fail_count, total_rules, grouped_findings } = report;

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-950 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Compliance Report
              </h1>
              <span className="px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-mono text-xs rounded-full font-bold uppercase">
                {framework}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-300">
              <span>
                <strong className="text-slate-500">Device:</strong>{" "}
                <span className="text-white font-medium">{device.filename}</span>
              </span>
              <span>
                <strong className="text-slate-500">Vendor:</strong>{" "}
                <span className="text-cyan-400 uppercase font-semibold">{device.vendor}</span>
              </span>
              {device.uploaded_at && (
                <span>
                  <strong className="text-slate-500">Uploaded:</strong>{" "}
                  {new Date(device.uploaded_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <a
              href={`${API_BASE}/devices/${device.id}/report.pdf?framework=${framework}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-xs rounded-xl shadow-lg shadow-cyan-500/20 transition active:scale-95 cursor-pointer"
            >
              <Download className="w-4 h-4 mr-2" />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Framework Selector Tabs */}
        <div className="mt-6 border-t border-slate-800 pt-4 flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-2">
            Rule Pack Framework:
          </span>
          {["CIS", "NIST", "STIG", "ISO"].map((fw) => (
            <button
              key={fw}
              onClick={() => handleFrameworkChange(fw)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition cursor-pointer ${
                framework === fw
                  ? "bg-cyan-600 text-white shadow-sm font-semibold"
                  : "bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700"
              }`}
            >
              {fw}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 text-center shadow-lg">
          <div className="text-3xl font-bold text-slate-200">{total_rules}</div>
          <div className="text-xs uppercase font-medium text-slate-400 tracking-wider mt-1">
            Total Rules
          </div>
        </div>
        <div className="bg-slate-900/80 border border-emerald-900/40 rounded-xl p-5 text-center shadow-lg bg-gradient-to-br from-emerald-950/30 to-slate-900/60">
          <div className="text-3xl font-bold text-emerald-400">{pass_count}</div>
          <div className="text-xs uppercase font-medium text-emerald-400 tracking-wider mt-1">
            Passed Rules
          </div>
        </div>
        <div className="bg-slate-900/80 border border-rose-900/40 rounded-xl p-5 text-center shadow-lg bg-gradient-to-br from-rose-950/30 to-slate-900/60">
          <div className="text-3xl font-bold text-rose-400">{fail_count}</div>
          <div className="text-xs uppercase font-medium text-rose-400 tracking-wider mt-1">
            Failed Rules
          </div>
        </div>
      </div>

      {/* Category Grouped Findings */}
      {Object.entries(grouped_findings).map(([category, findings]) => (
        <div
          key={category}
          className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl space-y-0"
        >
          <div className="px-6 py-4 border-b border-slate-800 bg-slate-950/40">
            <h2 className="text-lg font-semibold text-white capitalize">
              {category.replace("_", " ")}
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase text-xs tracking-wider">
                  <th className="px-6 py-3.5 w-32">Rule ID</th>
                  <th className="px-6 py-3.5">Title</th>
                  <th className="px-6 py-3.5 w-24">Status</th>
                  <th className="px-6 py-3.5 w-28">Severity</th>
                  <th className="px-6 py-3.5">Remediation CLI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {findings.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-6 py-4 font-mono font-bold text-cyan-400 text-xs">
                      {f.rule_id}
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-200">{f.title}</td>
                    <td className="px-6 py-4">
                      {f.status === "pass" ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-emerald-950 text-emerald-400 border border-emerald-800">
                          PASS
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-rose-950 text-rose-400 border border-rose-800">
                          FAIL
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                          f.severity === "CRITICAL"
                            ? "bg-rose-900 text-white"
                            : f.severity === "HIGH"
                            ? "bg-orange-600 text-white"
                            : f.severity === "MEDIUM"
                            ? "bg-amber-600 text-white"
                            : "bg-lime-600 text-white"
                        }`}
                      >
                        {f.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {f.status === "fail" && f.remediation_text ? (
                        <div className="relative group">
                          <code className="font-mono text-xs bg-slate-950 text-cyan-300 p-2.5 rounded-lg border border-slate-800 block whitespace-pre-wrap word-break-all pr-10">
                            {f.remediation_text}
                          </code>
                          <button
                            onClick={() =>
                              handleCopyRemediation(f.remediation_text!, f.id)
                            }
                            className="absolute right-2 top-2 p-1 text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded transition cursor-pointer"
                            title="Copy Remediation CLI"
                          >
                            {copiedId === f.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ) : f.status === "pass" ? (
                        <span className="text-xs font-semibold text-emerald-400 flex items-center space-x-1">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          <span>Compliant</span>
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
