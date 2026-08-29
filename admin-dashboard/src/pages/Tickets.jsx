import { useEffect, useState } from "react";
import { tickets as ticketsApi } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const STATUSES = ["", "open", "in_progress", "resolved", "closed"];
const DEPARTMENTS = [
  "",
  "admissions",
  "payments",
  "technical",
  "academic",
  "general",
];
const PRIORITIES = ["", "urgent", "high", "medium", "low"];

export default function Tickets() {
  const { error: showError } = useToast();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [status, setStatus] = useState("");
  const [department, setDepartment] = useState("");
  const [priority, setPriority] = useState("");
  const [counts, setCounts] = useState(null);

  const load = () => {
    setLoading(true);
    setLoadError(false);
    const params = {
      ...(status && { status }),
      ...(department && { department }),
      ...(priority && { priority }),
      limit: 100,
    };
    ticketsApi
      .list(params)
      .then((r) => setTickets(r.data))
      .catch((err) => {
        setTickets([]);
        setLoadError(true);
        const msg = err.response?.status === 401
          ? "Session expired — please sign in again"
          : "Failed to load tickets";
        showError(msg, { label: "Retry", onClick: load });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [status, department, priority]);

  useEffect(() => {
    ticketsApi
      .stats()
      .then((r) => setCounts(r.data.counts || r.data))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">
            Support Tickets
          </h1>
          {counts && (
            <div className="mt-1.5 flex flex-wrap gap-2 text-xs">
              {Object.entries(counts).map(([k, v]) => (
                <span
                  key={k}
                  className="rounded-full bg-gray-100 px-2.5 py-0.5 font-medium text-gray-600"
                >
                  {k.replace("_", " ")}: <span className="font-semibold text-gray-900">{v}</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <button onClick={load} className="btn-secondary btn-sm">
          Refresh
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Ticket filters">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="input w-auto text-xs"
          aria-label="Filter by status"
        >
          <option value="">All Status</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </option>
          ))}
        </select>

        <select
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          className="input w-auto text-xs"
          aria-label="Filter by department"
        >
          <option value="">All Depts</option>
          {DEPARTMENTS.filter(Boolean).map((d) => (
            <option key={d} value={d}>
              {d.charAt(0).toUpperCase() + d.slice(1)}
            </option>
          ))}
        </select>

        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="input w-auto text-xs"
          aria-label="Filter by priority"
        >
          <option value="">All Priority</option>
          {PRIORITIES.filter(Boolean).map((p) => (
            <option key={p} value={p}>
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-12" role="status">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden="true" />
          <span className="sr-only">Loading tickets</span>
        </div>
      ) : loadError ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-sm text-gray-600 mb-3">Could not load tickets</p>
          <button onClick={load} className="btn-primary btn-sm">Retry</button>
        </div>
      ) : tickets.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <svg className="mx-auto h-10 w-10 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 5v2m0 4v2m0 4v2M5 5a2 2 0 00-2 2v3a2 2 0 110 4v3a2 2 0 002 2h14a2 2 0 002-2v-3a2 2 0 110-4V7a2 2 0 00-2-2H5z" />
          </svg>
          <p className="text-sm font-medium text-gray-500">No tickets found</p>
          <p className="mt-1 text-xs text-gray-400">Tickets from WhatsApp support requests appear here</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full text-sm" aria-label="Support tickets">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3" scope="col">Ticket</th>
                <th className="px-4 py-3" scope="col">Subject</th>
                <th className="px-4 py-3" scope="col">Department</th>
                <th className="px-4 py-3" scope="col">Priority</th>
                <th className="px-4 py-3" scope="col">Status</th>
                <th className="px-4 py-3" scope="col">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {tickets.map((t) => (
                <tr
                  key={t.id}
                  className="transition-colors hover:bg-gray-50"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-gray-500">
                    {t.ticket_number}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {t.subject || "—"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 capitalize text-gray-600">
                    {t.department}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <StatusBadge value={t.priority} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    <StatusBadge value={t.status} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
                    {new Date(t.created_at).toLocaleDateString("en-NG")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
