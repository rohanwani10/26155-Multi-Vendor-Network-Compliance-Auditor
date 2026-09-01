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
        setUploadSuccess(`Successfully uploaded and normalized ${fileInput.name}`);
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
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="max-w-3xl space-y-3 relative z-10">
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Ingest Device Configurations
          </h1>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            Upload device config files (.cfg, .txt, .zip) from <span className="text-cyan-400 font-semibold">Cisco IOS</span>, <span className="text-emerald-400 font-semibold">Juniper</span>, <span className="text-amber-400 font-semibold">Palo Alto</span>, <span className="text-rose-400 font-semibold">Fortinet</span>, or <span className="text-purple-400 font-semibold">Arista</span>. The auditor automatically normalizes patterns into a vendor-neutral schema.
          </p>
        </div>
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Upload Form Box */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
        <form onSubmit={handleFileUpload} className="space-y-4">
          <div className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 rounded-xl p-6 transition group bg-slate-950/40">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-slate-800 rounded-xl text-cyan-400 group-hover:bg-cyan-500/10 transition">
                  <Upload className="w-6 h-6" />
                </div>
                <div>
                  <label htmlFor="file" className="block text-sm font-medium text-slate-200 cursor-pointer hover:text-cyan-400">
                    Select device config file or ZIP archive
                  </label>
                  <input
                    id="file"
                    name="file"
                    type="file"
                    required
                    className="mt-1 text-xs text-slate-400 file:mr-4 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={uploading}
                className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-cyan-500/20 transition active:scale-95 disabled:opacity-50 cursor-pointer"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    <span>Ingesting...</span>
                  </>
                ) : (
                  <>
                    <span>Upload & Ingest</span>
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {uploadSuccess && (
          <div className="mt-4 p-4 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl flex items-center space-x-3 text-sm font-medium animate-fade-in">
            <CheckCircle className="w-5 h-5 shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
        )}
      </div>

      {/* Ingested Devices Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileCode className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-semibold text-white">Ingested Devices</h2>
          </div>
          <span className="text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded-full border border-slate-700 font-mono">
            {devices.length} Total Devices
          </span>
        </div>

        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-slate-500 flex justify-center items-center space-x-2">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
              <span>Loading devices from FastAPI backend...</span>
            </div>
          ) : devices.length > 0 ? (
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-950/60 text-slate-400 font-semibold border-b border-slate-800 uppercase text-xs tracking-wider">
                  <th className="px-6 py-3.5">Filename</th>
                  <th className="px-6 py-3.5">Vendor</th>
                  <th className="px-6 py-3.5">Uploaded</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {devices.map((device) => (
                  <tr key={device.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-6 py-4 font-medium text-white flex items-center space-x-2">
                      <FileText className="w-4 h-4 text-cyan-400 shrink-0" />
                      <span>{device.filename}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                          device.vendor === "cisco"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                            : device.vendor === "juniper"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : device.vendor === "palo_alto"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                            : device.vendor === "fortinet"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            : device.vendor === "arista"
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/30"
                            : "bg-slate-800 text-slate-300 border border-slate-700"
                        }`}
                      >
                        {device.vendor}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">
                      {device.uploaded_at
                        ? new Date(device.uploaded_at).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-6 py-4 text-right space-x-3">
                      <Link
                        href={`/reports/${device.id}?framework=CIS`}
                        className="inline-flex items-center text-cyan-400 hover:text-cyan-300 font-medium text-xs hover:underline"
                      >
                        <span>View Report</span>
                      </Link>
                      <a
                        href={`${API_BASE}/devices/${device.id}/report.pdf?framework=CIS`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center text-slate-400 hover:text-slate-200 font-medium text-xs hover:underline"
                      >
                        <Download className="w-3.5 h-3.5 mr-1" />
                        <span>PDF</span>
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-12 text-center text-slate-500 text-sm">
              No devices uploaded yet. Choose a config file above to begin auditing.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
