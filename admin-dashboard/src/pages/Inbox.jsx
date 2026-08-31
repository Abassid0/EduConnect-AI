import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { admin } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const FILTERS = [
  { label: "All", params: {} },
  { label: "Needs Agent", params: { status: "paused_for_agent" } },
  { label: "Active", params: { status: "active" } },
  { label: "My Conversations", params: { assigned_to_me: true } },
];

const DEPARTMENTS = [
  "",
  "admissions",
  "payments",
  "technical",
  "academic",
  "general",
];
const PRIORITIES = ["", "high", "medium", "low"];

function formatPhone(raw) {
  if (!raw) return "Unknown";
  const digits = raw.replace(/\D/g, "");
  if (digits.startsWith("234") && digits.length >= 13) {
    return `+234 ${digits.slice(3, 6)} ${digits.slice(6, 9)} ${digits.slice(9)}`;
  }
  if (digits.length >= 10) {
    return `+${digits.slice(0, -10)} ${digits.slice(-10, -7)} ${digits.slice(-7, -4)} ${digits.slice(-4)}`;
  }
  return raw;
}

export default function Inbox() {
  const navigate = useNavigate();
  const { error: showError } = useToast();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [activeFilter, setActiveFilter] = useState(0);
  const [department, setDepartment] = useState("");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");

  const load = (filterIdx = activeFilter) => {
    setLoading(true);
    setLoadError(false);
    const params = {
      ...FILTERS[filterIdx].params,
      ...(department && { department }),
      ...(priority && { priority }),
      limit: 50,
    };
    admin
      .inbox(params)
      .then((r) => setConversations(Array.isArray(r.data) ? r.data : []))
      .catch((err) => {
        setConversations([]);
        setLoadError(true);
        const msg = err.response?.status === 401
          ? "Session expired — please sign in again"
          : "Failed to load conversations";
        showError(msg, { label: "Retry", onClick: () => load(filterIdx) });
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [activeFilter, department, priority]);

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase().replace(/\s/g, "");
    return conversations.filter((c) =>
      c.whatsapp_id?.toLowerCase().replace(/\s/g, "").includes(q)
    );
  }, [conversations, search]);

  const pausedCount = conversations.filter(
    (c) => c.status === "paused_for_agent"
  ).length;

  return (
    <div className="space-y-6 p-4 lg:p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 tracking-tight">Inbox</h1>
          <div className="mt-1 flex items-center gap-3">
            <p className="text-sm text-gray-500">
              {conversations.length} conversation{conversations.length !== 1 && "s"}
            </p>
            {pausedCount > 0 && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-700">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" aria-hidden="true" />
                {pausedCount} awaiting agent
              </span>
            )}
          </div>
        </div>
        <button onClick={() => load()} className="btn-secondary btn-sm">
          Refresh
        </button>
      </div>

      {/* Search + Filters */}
      <div className="space-y-3">
        <div className="relative">
          <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by phone number..."
            className="input pl-10"
            aria-label="Search conversations"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2" role="toolbar" aria-label="Conversation filters">
          {FILTERS.map((f, i) => (
            <button
              key={f.label}
              onClick={() => setActiveFilter(i)}
              className={`btn-sm rounded-full transition-all ${
                i === activeFilter
                  ? "bg-brand-600 text-white shadow-sm shadow-brand-600/25"
                  : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
              }`}
              aria-pressed={i === activeFilter}
            >
              {f.label}
            </button>
          ))}

          <div className="hidden sm:block h-5 w-px bg-gray-200" aria-hidden="true" />

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
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12" role="status">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden="true" />
          <span className="sr-only">Loading conversations</span>
        </div>
      ) : loadError ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <p className="text-sm text-gray-600 mb-3">Could not load conversations</p>
          <button onClick={() => load()} className="btn-primary btn-sm">Retry</button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white py-16 text-center">
          <svg className="mx-auto h-10 w-10 text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-2.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
          <p className="text-sm font-medium text-gray-500">
            {search ? "No matching conversations" : "No conversations found"}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            {search ? "Try a different search term" : "New WhatsApp messages will appear here"}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((c) => {
            const isUrgent = c.status === "paused_for_agent";
            return (
              <button
                key={c.id}
                onClick={() => navigate(`/conversations/${c.id}`)}
                className={`group flex w-full items-center gap-4 rounded-xl border bg-white p-4 text-left transition-all hover:shadow-sm ${
                  isUrgent
                    ? "border-amber-200 hover:border-amber-300 hover:bg-amber-50/30"
                    : "border-gray-200 hover:border-brand-300 hover:bg-brand-50/30"
                }`}
              >
                <div className={`relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
                  isUrgent
                    ? "bg-amber-100 text-amber-700"
                    : "bg-brand-50 text-brand-700"
                }`} aria-hidden="true">
                  {c.whatsapp_id?.slice(-2) || "?"}
                  {isUrgent && (
                    <span className="absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-white bg-amber-400" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-gray-900">
                      {formatPhone(c.whatsapp_id)}
                    </span>
                    <StatusBadge value={c.status} />
                  </div>
                  <p className="mt-0.5 truncate text-xs text-gray-500">
                    {c.current_flow
                      ? `Flow: ${c.current_flow}`
                      : "No active flow"}
                  </p>
                </div>

                <div className="text-right flex-shrink-0">
                  <p className="text-xs text-gray-500">
                    {c.last_message_at
                      ? timeAgo(c.last_message_at)
                      : "No messages"}
                  </p>
                  <svg className="mt-1 ml-auto h-4 w-4 text-gray-300 transition-colors group-hover:text-brand-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
