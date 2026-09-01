"use client";

import { useState, useEffect } from "react";
import { BookOpen, CheckCircle, Zap, Loader2 } from "lucide-react";

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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-heading font-semibold text-ink">
          Training queue
        </h1>
        <p className="mt-1.5 text-sm text-mid-gray max-w-2xl leading-relaxed">
          Lines the parser didn&apos;t recognize during ingestion. Map each one to a
          schema field once — the pattern is embedded and matched automatically on
          every config after this, with no repeat model call.
        </p>
      </div>

      {toastMessage && (
        <div className="px-4 py-3 bg-paper border border-hairline text-ink rounded-nested flex items-center gap-2.5 text-sm shadow-subtle">
          <CheckCircle className="w-4 h-4 shrink-0 text-mid-gray" strokeWidth={2} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Table card */}
      <div className="bg-paper border border-hairline rounded-card shadow-subtle overflow-hidden">
        <div className="px-5 py-4 border-b border-hairline flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-mid-gray" strokeWidth={2} />
            <h2 className="text-body-lg font-medium text-ink">Unrecognized lines</h2>
          </div>
          <span className="text-xs text-mid-gray bg-canvas px-2.5 py-1 rounded-pill border border-hairline font-mono">
            {pendingReviews.length}
          </span>
        </div>

        <div className="overflow-x-auto">
          {loading ? (
            <div className="p-8 text-center text-mid-gray flex justify-center items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading training queue…</span>
            </div>
          ) : pendingReviews.length > 0 ? (
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="text-mid-gray font-medium border-b border-hairline uppercase text-caption">
                  <th className="px-5 py-3">ID</th>
                  <th className="px-5 py-3">Vendor</th>
                  <th className="px-5 py-3">Line</th>
                  <th className="px-5 py-3">Confidence</th>
                  <th className="px-5 py-3" colSpan={4}>
                    Resolve
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline text-ink">
                {pendingReviews.map((item) => (
                  <tr key={item.id} className="hover:bg-canvas/60 transition-colors">
                    <td className="px-5 py-3.5 text-xs font-mono text-mid-gray">
                      #{item.id}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex px-2 py-0.5 rounded-pill text-xs font-medium bg-canvas text-ink-soft border border-hairline">
                        {item.vendor}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <code className="px-2 py-1 bg-canvas text-ink-soft rounded-[6px] border border-hairline text-xs font-mono break-all block max-w-md">
                        {item.raw_line}
                      </code>
                    </td>
                    <td className="px-5 py-3.5 text-xs">
                      <span className="px-2 py-0.5 rounded-pill font-mono text-xs font-medium bg-canvas text-mid-gray border border-hairline">
                        {item.confidence !== null ? item.confidence.toFixed(2) : "N/A"}
                      </span>
                    </td>
                    <td colSpan={4} className="px-5 py-3.5">
                      <form
                        onSubmit={(e) => handleResolve(e, item.id)}
                        className="flex items-center gap-2"
                      >
                        <select
                          name="category"
                          required
                          defaultValue={item.suggested_category || ""}
                          className="bg-canvas border border-hairline text-ink rounded-pill px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-hairline"
                        >
                          <option value="">Category</option>
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
                          className="bg-canvas border border-hairline text-ink rounded-pill px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-hairline w-32"
                        />

                        <input
                          type="text"
                          name="value"
                          defaultValue={item.suggested_value || ""}
                          placeholder="value"
                          className="bg-canvas border border-hairline text-ink rounded-pill px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-hairline w-28"
                        />

                        <button
                          type="submit"
                          disabled={resolvingId === item.id}
                          className="px-3.5 py-1.5 bg-ink hover:bg-ink-soft text-paper font-medium text-xs rounded-pill transition-colors disabled:opacity-50 flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
                        >
                          {resolvingId === item.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Zap className="w-3.5 h-3.5" strokeWidth={2} />
                          )}
                          <span>Resolve &amp; learn</span>
                        </button>
                      </form>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-6 py-14 text-center text-mid-gray text-sm">
              <CheckCircle className="w-8 h-8 mx-auto mb-3 text-hairline" strokeWidth={1.5} />
              Nothing queued — every uploaded line is recognized.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
