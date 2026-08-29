import { useEffect, useState } from "react";
import { analytics } from "../api/client";
import { useToast } from "../components/Toast";

export default function Analytics() {
  const { error: showError } = useToast();
  const [funnel, setFunnel] = useState(null);
  const [volume, setVolume] = useState([]);
  const [resolution, setResolution] = useState(null);
  const [responseTime, setResponseTime] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [aiStats, setAiStats] = useState(null);
  const [aiQueries, setAiQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [days, setDays] = useState(30);

  const load = async (d = days) => {
    setLoading(true);
    setLoadError(false);
    try {
      const [fRes, vRes, rRes, rtRes, lRes, aiRes, aqRes] = await Promise.all([
        analytics.funnel({ days: d }),
        analytics.volume({ days: d, period: "daily" }),
        analytics.resolutionRate({ days: d }),
        analytics.responseTime({ days: d }),
        analytics.leaderboard({ limit: 10 }),
        analytics.ai({ days: d }),
        analytics.aiTopQueries({ days: d, limit: 10 }),
      ]);
      setFunnel(fRes.data);
      setVolume(vRes.data);
      setResolution(rRes.data);
      setResponseTime(rtRes.data);
      setLeaderboard(lRes.data);
      setAiStats(aiRes.data);
      setAiQueries(aqRes.data);
    } catch (err) {
      setLoadError(true);
      const msg = err.response?.status === 401
        ? "Session expired — please sign in again"
        : "Failed to load analytics";
      showError(msg, { label: "Retry", onClick: () => load(d) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [days]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center" role="status">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden="true" />
        <span className="sr-only">Loading analytics</span>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6">
        <p className="text-sm text-gray-600">Could not load analytics</p>
        <button onClick={() => load()} className="btn-primary btn-sm">Retry</button>
      </div>
    );
  }

  const maxVol = Math.max(...volume.map((v) => v.count), 1);

  return (
    <div className="p-4 lg:p-6 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-xl font-bold text-gray-900 tracking-tight">Analytics</h1>
        <div className="flex items-center gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`btn-sm rounded-full transition-all ${
                d === days
                  ? "bg-brand-600 text-white shadow-sm shadow-brand-600/25"
                  : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
              }`}
              aria-pressed={d === days}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Conversations"
          value={resolution?.total_conversations ?? 0}
        />
        <KpiCard
          label="Bot Resolution"
          value={`${resolution?.resolution_rate_pct ?? 0}%`}
          sub={`${resolution?.bot_resolved ?? 0} of ${resolution?.total_conversations ?? 0}`}
        />
        <KpiCard
          label="Escalations"
          value={resolution?.escalated ?? 0}
        />
        <KpiCard
          label="Avg Response"
          value={
            responseTime?.avg_response_seconds
              ? `${responseTime.avg_response_seconds}s`
              : "N/A"
          }
        />
      </div>

      {/* Conversion Funnel */}
      {funnel && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 lg:p-6">
          <h2 className="mb-4 text-base font-semibold text-gray-900">
            Conversion Funnel ({days} days)
          </h2>
          <div className="space-y-3">
            {funnel.funnel.map((stage, i) => {
              const maxCount = funnel.funnel[0]?.count || 1;
              const pct = maxCount > 0 ? (stage.count / maxCount) * 100 : 0;
              return (
                <div key={stage.stage}>
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span className="capitalize">
                      {stage.stage.replace(/_/g, " ")}
                    </span>
                    <span>
                      {stage.count}
                      {i > 0 && stage.drop_off_pct > 0 && (
                        <span className="ml-2 text-red-500">
                          -{stage.drop_off_pct}%
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="h-5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand-500 transition-all"
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Conversation Volume Chart */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 lg:p-6">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Daily Conversation Volume
        </h2>
        {volume.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-8 text-center">
            No data yet
          </p>
        ) : (
          <div className="flex items-end gap-1 h-40 overflow-x-auto">
            {volume.map((v) => (
              <div
                key={v.date}
                className="flex flex-col items-center min-w-[24px]"
                title={`${v.date}: ${v.count}`}
              >
                <div
                  className="w-5 rounded-t bg-brand-500 transition-all"
                  style={{
                    height: `${Math.max((v.count / maxVol) * 120, 4)}px`,
                  }}
                />
                <span className="text-[8px] text-gray-400 mt-1 rotate-[-45deg] origin-top-left whitespace-nowrap">
                  {v.date.slice(5)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Referral Leaderboard */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 lg:p-6">
        <h2 className="mb-4 text-base font-semibold text-gray-900">
          Referral Leaderboard
        </h2>
        {leaderboard.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-8 text-center">
            No referrals yet
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" aria-label="Referral leaderboard">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3" scope="col">#</th>
                  <th className="px-4 py-3" scope="col">Code</th>
                  <th className="px-4 py-3" scope="col">Name</th>
                  <th className="px-4 py-3" scope="col">Type</th>
                  <th className="px-4 py-3 text-right" scope="col">Registrations</th>
                  <th className="px-4 py-3 text-right" scope="col">Revenue</th>
                  <th className="px-4 py-3 text-right" scope="col">Commission</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {leaderboard.map((r, i) => (
                  <tr key={r.code}>
                    <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {r.code}
                    </td>
                    <td className="px-4 py-3">{r.referrer_name || "—"}</td>
                    <td className="px-4 py-3 capitalize text-gray-500">
                      {r.referrer_type}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">
                      {r.total_registrations}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {Number(r.total_revenue).toLocaleString("en-NG", {
                        style: "currency",
                        currency: "NGN",
                      })}
                    </td>
                    <td className="px-4 py-3 text-right text-green-600">
                      {Number(r.commission_earned).toLocaleString("en-NG", {
                        style: "currency",
                        currency: "NGN",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {/* AI Assistant Analytics */}
      {aiStats && (
        <div className="rounded-xl border border-gray-200 bg-white p-4 lg:p-6">
          <h2 className="mb-4 text-base font-semibold text-gray-900">
            AI Assistant ({days} days)
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-6">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Queries</p>
              <p className="mt-1 text-xl font-bold text-gray-900">{aiStats.total_queries}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">AI Resolved</p>
              <p className="mt-1 text-xl font-bold text-green-600">{aiStats.resolution_rate_pct}%</p>
              <p className="text-xs text-gray-400">{aiStats.resolved} of {aiStats.total_queries}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Escalated</p>
              <p className="mt-1 text-xl font-bold text-amber-600">{aiStats.escalated}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">Avg Confidence</p>
              <p className="mt-1 text-xl font-bold text-gray-900">
                {aiStats.avg_confidence != null ? `${(aiStats.avg_confidence * 100).toFixed(0)}%` : "N/A"}
              </p>
              {aiStats.avg_response_ms != null && (
                <p className="text-xs text-gray-400">{aiStats.avg_response_ms}ms avg</p>
              )}
            </div>
          </div>

          {aiQueries.length > 0 && (
            <>
              <h3 className="mb-2 text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Top Queries
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm" aria-label="Top AI queries">
                  <thead>
                    <tr className="border-b border-gray-200 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                      <th className="px-4 py-3" scope="col">Query</th>
                      <th className="px-4 py-3 text-right" scope="col">Count</th>
                      <th className="px-4 py-3 text-right" scope="col">Confidence</th>
                      <th className="px-4 py-3 text-right" scope="col">Escalated</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {aiQueries.map((q, i) => (
                      <tr key={i}>
                        <td className="px-4 py-3 max-w-xs truncate text-gray-700">
                          {q.query}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold">{q.count}</td>
                        <td className="px-4 py-3 text-right">
                          <span className={q.avg_confidence >= 0.7 ? "text-green-600" : q.avg_confidence >= 0.4 ? "text-amber-600" : "text-red-500"}>
                            {(q.avg_confidence * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500">{q.escalated_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, sub }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  );
}
