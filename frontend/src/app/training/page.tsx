"use client";

import { useState, useEffect } from "react";
import { BookOpen, CheckCircle, Zap, Loader2, Sparkles } from "lucide-react";

interface PendingReview {
  id: number;
  parsed_config_id: number;
  device_id: number;
  vendor: string;
  raw_line: string;
  confidence: number | null;
  suggested_category: string | null;
  suggested_field: string | null;
  suggested_value: string | null;
  status: string;
}

const API_BASE = "http://localhost:8000";

export default function TrainingPage() {
  const [pendingReviews, setPendingReviews] = useState<PendingReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<number | null>(null);

  const fetchPendingReviews = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/training/pending`);
      if (res.ok) {
        const data = await res.json();
        setPendingReviews(data);
      }
    } catch (err) {
      console.error("Failed to fetch pending reviews:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingReviews();
  }, []);

  const handleResolve = async (
    e: React.FormEvent<HTMLFormElement>,
    reviewId: number
  ) => {
    e.preventDefault();
    setResolvingId(reviewId);
    setToastMessage(null);

    const formData = new FormData(e.currentTarget);
    const category = formData.get("category") as string;
    const field = formData.get("field") as string;
    const value = formData.get("value") as string;

    try {
      const res = await fetch(`${API_BASE}/api/training/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          review_id: reviewId,
          category,
          field,
          value: value || null,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setToastMessage(data.message);
        setPendingReviews(data.pending_reviews || []);
      } else {
        alert("Failed to resolve pending item.");
      }
    } catch (err) {
      console.error("Error resolving item:", err);
      alert("Error connecting to backend server at http://localhost:8000");
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="flex items-start space-x-4 relative z-10">
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 shrink-0">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              Human-in-the-Loop Training Queue
            </h1>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Review unrecognized lines detected during config ingestion. Resolving an entry automatically trains ChromaDB vector storage — enabling zero-shot vector matching for all subsequent identical or similar vendor configurations.
            </p>
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl flex items-center space-x-3 text-sm font-medium animate-fade-in shadow-lg">
          <CheckCircle className="w-5 h-5 shrink-0 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Table Container */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white">Unrecognized Config Line Queue</h2>
          </div>
          <span className="text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded-full border border-slate-700 font-mono">
            {pendingReviews.length} Queue Items
          </span>
        </div>

        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-slate-500 flex justify-center items-center space-x-2">
              <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
              <span>Loading pending training queue...</span>
            </div>
          ) : pendingReviews.length > 0 ? (
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-950/60 text-slate-400 font-semibold border-b border-slate-800 uppercase text-xs tracking-wider">
                  <th className="px-4 py-3.5">ID</th>
                  <th className="px-4 py-3.5">Vendor</th>
                  <th className="px-4 py-3.5">Unrecognized Line</th>
                  <th className="px-4 py-3.5">Confidence</th>
                  <th className="px-4 py-3.5">Category</th>
                  <th className="px-4 py-3.5">Field</th>
                  <th className="px-4 py-3.5">Value</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {pendingReviews.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/40 transition">
                    <td className="px-4 py-4 text-xs font-mono text-slate-500">
                      #{item.id}
                    </td>
                    <td className="px-4 py-4">
                      <span className="px-2.5 py-0.5 rounded text-xs font-semibold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                        {item.vendor}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <code className="px-2.5 py-1 bg-slate-950 text-cyan-300 rounded border border-slate-800 text-xs font-mono break-all block max-w-md">
                        {item.raw_line}
                      </code>
                    </td>
                    <td className="px-4 py-4 text-xs">
                      <span className="px-2 py-0.5 rounded-full font-mono text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                        {item.confidence !== null ? item.confidence.toFixed(2) : "N/A"}
                      </span>
                    </td>
                    <td colSpan={4} className="px-4 py-4">
                      <form
                        onSubmit={(e) => handleResolve(e, item.id)}
                        className="flex items-center gap-2"
                      >
                        <select
                          name="category"
                          required
                          defaultValue={item.suggested_category || ""}
                          className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none"
                        >
                          <option value="">-- Category --</option>
                          <option value="management_plane">management_plane</option>
                          <option value="auth">auth</option>
                          <option value="logging">logging</option>
                          <option value="crypto">crypto</option>
                        </select>

                        <input
                          type="text"
                          name="field"
                          required
                          defaultValue={item.suggested_field || ""}
                          placeholder="field_name"
                          className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none w-32"
                        />

                        <input
                          type="text"
                          name="value"
                          defaultValue={item.suggested_value || ""}
                          placeholder="value"
                          className="bg-slate-950 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 text-xs focus:ring-2 focus:ring-cyan-500 focus:outline-none w-28"
                        />

                        <button
                          type="submit"
                          disabled={resolvingId === item.id}
                          className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs rounded-lg transition active:scale-95 whitespace-nowrap shadow-sm disabled:opacity-50 flex items-center space-x-1 cursor-pointer"
                        >
                          {resolvingId === item.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Zap className="w-3.5 h-3.5" />
                          )}
                          <span>Resolve & Learn</span>
                        </button>
                      </form>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-12 text-center text-slate-500 text-sm">
              <CheckCircle className="w-10 h-10 mx-auto mb-3 text-emerald-500/60" />
              <span>No pending lines queued for training. All uploaded lines are recognized!</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
