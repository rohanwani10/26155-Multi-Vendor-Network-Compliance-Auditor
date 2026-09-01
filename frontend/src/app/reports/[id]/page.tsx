"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { Download, CheckCircle2, XCircle, Copy, Check, Loader2, RefreshCw } from "lucide-react";

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

const SEVERITY_STYLE: Record<string, string> = {
  CRITICAL: "bg-ember text-paper",
  HIGH: "bg-ember/10 text-ember",
  MEDIUM: "bg-canvas text-ink-soft border border-hairline",
  LOW: "border border-hairline text-mid-gray",
};

export default function ReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const deviceId = params.id as string;
  const currentFramework = searchParams.get("framework") || "CIS";

  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [reevaluating, setReevaluating] = useState(false);

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

  const handleReevaluate = async () => {
    setReevaluating(true);
    try {
      const res = await fetch(
        `${API_BASE}/evaluate/${deviceId}?framework=${currentFramework}`,
        { method: "POST" }
      );
      if (res.ok) {
        await fetchReport(currentFramework);
      } else {
        alert("Failed to re-evaluate device.");
      }
    } catch (err) {
      console.error("Failed to re-evaluate:", err);
      alert("Error connecting to backend server at http://localhost:8000");
    } finally {
      setReevaluating(false);
    }
  };

  const handleCopyRemediation = (text: string, id: number) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-mid-gray flex flex-col justify-center items-center gap-3 text-sm">
        <Loader2 className="w-6 h-6 animate-spin" />
        <span>Evaluating configuration…</span>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-12 text-center text-mid-gray text-sm">
        Report not found for device #{deviceId}.
      </div>
    );
  }

  const { device, framework, pass_count, fail_count, total_rules, grouped_findings } = report;

  return (
    <div className="space-y-6">
      {/* Header card */}
      <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-heading-sm font-semibold text-ink">
                Compliance report
              </h1>
              <span className="px-2 py-0.5 bg-canvas border border-hairline text-ink-soft font-mono text-xs rounded-pill font-medium">
                {framework}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-mid-gray">
              <span>
                <span className="text-ink font-medium">{device.filename}</span>
              </span>
              <span className="uppercase text-xs tracking-wide">{device.vendor}</span>
              {device.uploaded_at && (
                <span className="text-xs">{new Date(device.uploaded_at).toLocaleString()}</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleReevaluate}
              disabled={reevaluating}
              title="Re-run compliance evaluation against the device's current config"
              className="inline-flex items-center px-4 py-2 bg-transparent border border-hairline text-ink hover:bg-canvas font-medium text-[13px] rounded-pill transition-colors cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-2 ${reevaluating ? "animate-spin" : ""}`} strokeWidth={2} />
              <span>Re-evaluate</span>
            </button>
            <a
              href={`${API_BASE}/devices/${device.id}/report.pdf?framework=${framework}`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center px-4 py-2 bg-ink hover:bg-ink-soft text-paper font-medium text-[13px] rounded-pill transition-colors cursor-pointer"
            >
              <Download className="w-3.5 h-3.5 mr-2" strokeWidth={2} />
              <span>Download PDF</span>
            </a>
          </div>
        </div>

        {/* Framework tabs */}
        <div className="mt-5 border-t border-hairline pt-4 flex items-center gap-1.5">
          <span className="text-xs font-medium text-mid-gray uppercase tracking-wide mr-1.5">
            Framework
          </span>
          {["CIS", "NIST", "STIG", "ISO"].map((fw) => (
            <button
              key={fw}
              onClick={() => handleFrameworkChange(fw)}
              className={`px-3 py-1.5 rounded-pill text-xs font-medium transition-colors cursor-pointer ${
                framework === fw
                  ? "bg-ink text-paper"
                  : "bg-canvas text-mid-gray hover:text-ink border border-hairline"
              }`}
            >
              {fw}
            </button>
          ))}
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5 text-center">
          <div className="text-heading font-semibold text-ink">{total_rules}</div>
          <div className="text-xs uppercase font-medium text-mid-gray tracking-wide mt-1">
            Total rules
          </div>
        </div>
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5 text-center">
          <div className="text-heading font-semibold text-ink">{pass_count}</div>
          <div className="text-xs uppercase font-medium text-mid-gray tracking-wide mt-1">
            Passed
          </div>
        </div>
        <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5 text-center">
          <div className="text-heading font-semibold text-ember">{fail_count}</div>
          <div className="text-xs uppercase font-medium text-mid-gray tracking-wide mt-1">
            Failed
          </div>
        </div>
      </div>

      {/* Findings by category */}
      {Object.entries(grouped_findings).map(([category, findings]) => (
        <div
          key={category}
          className="bg-paper border border-hairline rounded-card shadow-subtle overflow-hidden"
        >
          <div className="px-5 py-4 border-b border-hairline">
            <h2 className="text-body-lg font-medium text-ink capitalize">
              {category.replace(/_/g, " ")}
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="text-mid-gray font-medium border-b border-hairline uppercase text-caption">
                  <th className="px-5 py-3 w-32">Rule ID</th>
                  <th className="px-5 py-3">Title</th>
                  <th className="px-5 py-3 w-24">Status</th>
                  <th className="px-5 py-3 w-28">Severity</th>
                  <th className="px-5 py-3">Remediation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline text-ink">
                {findings.map((f) => (
                  <tr key={f.id} className="hover:bg-canvas/60 transition-colors">
                    <td className="px-5 py-3.5 font-mono text-xs text-mid-gray">
                      {f.rule_id}
                    </td>
                    <td className="px-5 py-3.5 font-medium">{f.title}</td>
                    <td className="px-5 py-3.5">
                      {f.status === "pass" ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-pill text-xs font-medium border border-hairline text-mid-gray">
                          <CheckCircle2 className="w-3 h-3" strokeWidth={2} />
                          Pass
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-pill text-xs font-medium bg-ember/10 text-ember">
                          <XCircle className="w-3 h-3" strokeWidth={2} />
                          Fail
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-pill text-xs font-medium ${
                          SEVERITY_STYLE[f.severity] || "bg-canvas text-mid-gray border border-hairline"
                        }`}
                      >
                        {f.severity}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      {f.status === "fail" && f.remediation_text ? (
                        <div className="relative group">
                          <code className="font-mono text-xs bg-canvas text-ink-soft p-2.5 rounded-[6px] border border-hairline block whitespace-pre-wrap break-all pr-10">
                            {f.remediation_text}
                          </code>
                          <button
                            onClick={() => handleCopyRemediation(f.remediation_text!, f.id)}
                            className="absolute right-2 top-2 p-1 text-mid-gray hover:text-ink bg-paper border border-hairline rounded-[6px] transition-colors cursor-pointer"
                            title="Copy remediation command"
                          >
                            {copiedId === f.id ? (
                              <Check className="w-3.5 h-3.5" strokeWidth={2} />
                            ) : (
                              <Copy className="w-3.5 h-3.5" strokeWidth={2} />
                            )}
                          </button>
                        </div>
                      ) : f.status === "pass" ? (
                        <span className="text-xs text-mid-gray">Compliant</span>
                      ) : (
                        <span className="text-mid-gray">—</span>
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
