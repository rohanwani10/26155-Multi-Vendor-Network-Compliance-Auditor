"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Upload, FileCode, CheckCircle, ArrowRight, FileText, Download, Loader2 } from "lucide-react";

interface Device {
  id: number;
  filename: string;
  vendor: string;
  uploaded_at: string | null;
}

const API_BASE = "http://localhost:8000";

export default function UploadPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  const fetchDevices = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/devices`);
      if (res.ok) {
        const data = await res.json();
        setDevices(data);
      }
    } catch (err) {
      console.error("Failed to fetch devices:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleFileUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const fileInput = formData.get("file") as File;
    if (!fileInput || fileInput.size === 0) return;

    setUploading(true);
    setUploadSuccess(null);

    try {
      const res = await fetch(`${API_BASE}/api/devices/upload`, {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setDevices(data.devices || []);
        setUploadSuccess(`Uploaded and normalized ${fileInput.name}`);
        (e.target as HTMLFormElement).reset();
      } else {
        alert("Failed to upload file to backend server.");
      }
    } catch (err) {
      console.error("Upload error:", err);
      alert("Error connecting to backend server at http://localhost:8000");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-heading font-semibold text-ink">
          Device configurations
        </h1>
        <p className="mt-1.5 text-sm text-mid-gray max-w-2xl leading-relaxed">
          Upload a config file or ZIP from Cisco IOS, Juniper, Palo Alto, Fortinet, or
          Arista. Unrecognized formats route to the training queue instead of being
          dropped.
        </p>
      </div>

      {/* Upload card */}
      <div className="bg-paper border border-hairline rounded-card shadow-subtle p-5">
        <form onSubmit={handleFileUpload}>
          <div className="border border-dashed border-hairline rounded-nested p-4 bg-canvas/60">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-9 h-9 rounded-nested bg-paper border border-hairline flex items-center justify-center shrink-0">
                  <Upload className="w-4 h-4 text-ink" strokeWidth={2} />
                </div>
                <div>
                  <label htmlFor="file" className="block text-sm font-medium text-ink cursor-pointer">
                    Select a config file or ZIP archive
                  </label>
                  <input
                    id="file"
                    name="file"
                    type="file"
                    required
                    className="mt-1.5 text-xs text-mid-gray file:mr-3 file:py-1.5 file:px-3 file:rounded-pill file:border file:border-hairline file:text-xs file:font-medium file:bg-paper file:text-ink hover:file:bg-canvas cursor-pointer"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={uploading}
                className="w-full sm:w-auto inline-flex items-center justify-center px-4 py-2 bg-ink hover:bg-ink-soft text-paper font-medium text-[13px] rounded-pill transition-colors disabled:opacity-50 cursor-pointer"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" />
                    <span>Ingesting…</span>
                  </>
                ) : (
                  <>
                    <span>Upload &amp; ingest</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {uploadSuccess && (
          <div className="mt-4 px-4 py-3 bg-canvas border border-hairline text-ink rounded-nested flex items-center gap-2.5 text-sm">
            <CheckCircle className="w-4 h-4 shrink-0 text-mid-gray" strokeWidth={2} />
            <span>{uploadSuccess}</span>
          </div>
        )}
      </div>

      {/* Devices table */}
      <div className="bg-paper border border-hairline rounded-card shadow-subtle overflow-hidden">
        <div className="px-5 py-4 border-b border-hairline flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileCode className="w-4 h-4 text-mid-gray" strokeWidth={2} />
            <h2 className="text-body-lg font-medium text-ink">Ingested devices</h2>
          </div>
          <span className="text-xs text-mid-gray bg-canvas px-2.5 py-1 rounded-pill border border-hairline font-mono">
            {devices.length}
          </span>
        </div>

        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-mid-gray flex justify-center items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading devices…</span>
            </div>
          ) : devices.length > 0 ? (
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="text-mid-gray font-medium border-b border-hairline uppercase text-caption">
                  <th className="px-5 py-3">Filename</th>
                  <th className="px-5 py-3">Vendor</th>
                  <th className="px-5 py-3">Uploaded</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline text-ink">
                {devices.map((device) => (
                  <tr key={device.id} className="hover:bg-canvas/60 transition-colors">
                    <td className="px-5 py-3.5 font-medium flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-mid-gray shrink-0" strokeWidth={2} />
                      <span>{device.filename}</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-pill text-xs font-medium bg-canvas text-ink-soft border border-hairline">
                        {device.vendor}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-mid-gray">
                      {device.uploaded_at
                        ? new Date(device.uploaded_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-5 py-3.5 text-right space-x-4">
                      <Link
                        href={`/reports/${device.id}?framework=CIS`}
                        className="text-ink hover:text-mid-gray font-medium text-xs"
                      >
                        View report
                      </Link>
                      <a
                        href={`${API_BASE}/devices/${device.id}/report.pdf?framework=CIS`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center text-mid-gray hover:text-ink font-medium text-xs"
                      >
                        <Download className="w-3 h-3 mr-1" strokeWidth={2} />
                        <span>PDF</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-14 text-center text-mid-gray text-sm">
              No devices uploaded yet. Choose a config file above to begin.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
