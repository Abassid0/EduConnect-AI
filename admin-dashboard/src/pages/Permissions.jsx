import { useEffect, useState } from "react";
import { permissions as permissionsApi } from "../api/client";
import client from "../api/client";
import { useToast } from "../components/Toast";
import { TableSkeleton } from "../components/RouteFallback";

const SEGMENT_LABELS = {
  all: "All Parents",
  programme: "Parents in a Programme",
  has_overdue: "Parents with Overdue Balance",
  specific: "Specific Parent IDs",
};

const STATUS_BADGE = {
  draft: "bg-gray-100 text-gray-600",
  active: "bg-blue-100 text-blue-700",
  closed: "bg-gray-100 text-gray-400",
};

const RESPONSE_BADGE = {
  yes: "bg-green-100 text-green-700",
  no: "bg-red-100 text-red-700",
  pending: "bg-gray-100 text-gray-500",
};

const EMPTY_FORM = {
  title: "",
  description: "",
  event_date: "",
  deadline: "",
  segment_type: "all",
  segment_value: "",
  programme_id: "",
  specific_ids: "",
};

function fmtDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-NG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-NG", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Permissions() {
  const toast = useToast();
  const [slips, setSlips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    setLoading(true);
    permissionsApi
      .listSlips()
      .then(setSlips)
      .catch(() => toast.error("Failed to load permission slips"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreated = () => {
    setShowForm(false);
    load();
  };

  if (detail) {
    return (
      <DetailView
        slip={detail}
        onBack={() => {
          setDetail(null);
          load();
        }}
        toast={toast}
      />
    );
  }

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-gray-900">Permission Slips</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Create consent requests and track parent responses.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="btn btn-primary btn-sm self-start sm:self-auto"
        >
          {showForm ? "Hide Form" : "+ New Slip"}
        </button>
      </div>

      {showForm && (
        <CreateForm onCreated={handleCreated} toast={toast} />
      )}

      <SlipTable
        slips={slips}
        loading={loading}
        onView={setDetail}
        onRefresh={load}
        toast={toast}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Create Form                                                         */
/* ------------------------------------------------------------------ */

function CreateForm({ onCreated, toast }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [programmes, setProgrammes] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    client.get("/programmes").then((r) => setProgrammes(r.data || [])).catch(() => {});
  }, []);

  const buildSegmentValue = () => {
    if (form.segment_type === "programme") return form.programme_id || null;
    if (form.segment_type === "specific") {
      const ids = form.specific_ids.split("\n").map((s) => s.trim()).filter(Boolean);
      return ids.length ? JSON.stringify(ids) : null;
    }
    return null;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true);
    permissionsApi
      .createSlip({
        title: form.title.trim(),
        description: form.description.trim() || null,
        event_date: form.event_date || null,
        deadline: form.deadline ? new Date(form.deadline).toISOString() : null,
        segment_type: form.segment_type,
        segment_value: buildSegmentValue(),
      })
      .then(() => {
        toast.success("Draft created");
        onCreated();
      })
      .catch((err) => toast.error(err.response?.data?.detail || "Failed to create slip"))
      .finally(() => setSaving(false));
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-xl border border-gray-200 bg-white p-5 space-y-5"
    >
      <h2 className="text-sm font-semibold text-gray-800">New Permission Slip</h2>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Title *</label>
        <input
          className="input w-full"
          value={form.title}
          maxLength={200}
          required
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="e.g. End-of-Term Excursion Consent"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
        <textarea
          className="input w-full resize-none"
          rows={3}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Optional details about the event or consent request."
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Event Date</label>
          <input
            type="date"
            className="input w-full"
            value={form.event_date}
            onChange={(e) => setForm({ ...form, event_date: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Deadline</label>
          <input
            type="datetime-local"
            className="input w-full"
            value={form.deadline}
            onChange={(e) => setForm({ ...form, deadline: e.target.value })}
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Send to</label>
        <select
          className="input w-full max-w-xs"
          value={form.segment_type}
          onChange={(e) =>
            setForm({ ...form, segment_type: e.target.value, programme_id: "", specific_ids: "" })
          }
        >
          <option value="all">All Parents</option>
          <option value="programme">Parents in a Programme</option>
          <option value="has_overdue">Parents with Overdue Balance</option>
          <option value="specific">Specific Parent IDs</option>
        </select>

        {form.segment_type === "programme" && (
          <div className="mt-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">Programme</label>
            <select
              className="input w-full max-w-xs"
              value={form.programme_id}
              onChange={(e) => setForm({ ...form, programme_id: e.target.value })}
              required
            >
              <option value="">Select a programme…</option>
              {programmes.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        )}

        {form.segment_type === "specific" && (
          <div className="mt-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">Parent IDs</label>
            <textarea
              className="input w-full resize-none font-mono text-xs"
              rows={4}
              value={form.specific_ids}
              onChange={(e) => setForm({ ...form, specific_ids: e.target.value })}
              placeholder="Paste one parent UUID per line"
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button type="submit" disabled={saving} className="btn btn-primary btn-sm">
          {saving ? "Creating…" : "Create Draft"}
        </button>
      </div>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  Slip Table                                                          */
/* ------------------------------------------------------------------ */

function SlipTable({ slips, loading, onView, onRefresh, toast }) {
  const [pendingSend, setPendingSend] = useState(null);
  const [pendingClose, setPendingClose] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const handleSend = (slip) => {
    if (pendingSend === slip.id) {
      setActionLoading(slip.id);
      permissionsApi
        .sendSlip(slip.id)
        .then(() => {
          toast.success("Slip queued for delivery");
          setPendingSend(null);
          onRefresh();
        })
        .catch((err) => toast.error(err.response?.data?.detail || "Failed to send slip"))
        .finally(() => setActionLoading(null));
    } else {
      setPendingSend(slip.id);
      setPendingClose(null);
    }
  };

  const handleClose = (slip) => {
    if (pendingClose === slip.id) {
      setActionLoading(slip.id);
      permissionsApi
        .closeSlip(slip.id)
        .then(() => {
          toast.success("Slip closed");
          setPendingClose(null);
          onRefresh();
        })
        .catch(() => toast.error("Failed to close slip"))
        .finally(() => setActionLoading(null));
    } else {
      setPendingClose(slip.id);
      setPendingSend(null);
    }
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {slips.length} slip{slips.length !== 1 && "s"}
        </span>
        <button onClick={onRefresh} className="btn btn-secondary btn-sm">
          Refresh
        </button>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : slips.length === 0 ? (
        <EmptyState message="No permission slips yet — create your first consent request." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Event Date</th>
                <th className="px-4 py-3">Deadline</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-center">Yes</th>
                <th className="px-4 py-3 text-center">No</th>
                <th className="px-4 py-3 text-center">Pending</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {slips.map((slip) => {
                const isSendPending = pendingSend === slip.id;
                const isClosePending = pendingClose === slip.id;
                const isLoading = actionLoading === slip.id;
                return (
                  <tr key={slip.id} className="hover:bg-gray-50/50">
                    <td className="max-w-[200px] truncate px-4 py-3 font-medium text-gray-900">
                      {slip.title}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                      {fmtDate(slip.event_date)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                      {fmtDateTime(slip.deadline)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          STATUS_BADGE[slip.status] || STATUS_BADGE.draft
                        } ${slip.status === "closed" ? "line-through" : ""}`}
                      >
                        {slip.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700 tabular-nums">
                        {slip.yes_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700 tabular-nums">
                        {slip.no_count}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-500 tabular-nums">
                        {slip.pending_count}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="flex items-center gap-2">
                        {slip.status === "draft" && (
                          <>
                            <button
                              onClick={() => handleSend(slip)}
                              disabled={isLoading}
                              className={`btn-sm ${isSendPending ? "btn-primary" : "btn-secondary"}`}
                            >
                              {isLoading ? "…" : isSendPending ? "Confirm Send?" : "Send"}
                            </button>
                            {isSendPending && (
                              <button
                                onClick={() => setPendingSend(null)}
                                className="text-xs text-gray-400 hover:text-gray-600"
                              >
                                Cancel
                              </button>
                            )}
                          </>
                        )}
                        {slip.status === "active" && (
                          <>
                            <button
                              onClick={() => onView(slip)}
                              className="btn-sm btn-secondary"
                            >
                              View
                            </button>
                            <button
                              onClick={() => handleClose(slip)}
                              disabled={isLoading}
                              className={`btn-sm ${isClosePending ? "btn-danger" : "btn-secondary"}`}
                            >
                              {isLoading ? "…" : isClosePending ? "Confirm Close?" : "Close"}
                            </button>
                            {isClosePending && (
                              <button
                                onClick={() => setPendingClose(null)}
                                className="text-xs text-gray-400 hover:text-gray-600"
                              >
                                Keep
                              </button>
                            )}
                          </>
                        )}
                        {slip.status === "closed" && (
                          <button
                            onClick={() => onView(slip)}
                            className="btn-sm btn-secondary"
                          >
                            View
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Detail View                                                         */
/* ------------------------------------------------------------------ */

function DetailView({ slip, onBack, toast }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [overrideRow, setOverrideRow] = useState(null);
  const [overrideValue, setOverrideValue] = useState("yes");
  const [overriding, setOverriding] = useState(false);

  const loadResponses = () => {
    setLoading(true);
    permissionsApi
      .getResponses(slip.id)
      .then(setDetail)
      .catch(() => toast.error("Failed to load responses"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadResponses();
  }, [slip.id]);

  const handleOverride = (parentId) => {
    setOverriding(true);
    permissionsApi
      .overrideResponse(slip.id, parentId, overrideValue)
      .then(() => {
        toast.success("Response recorded");
        setOverrideRow(null);
        loadResponses();
      })
      .catch((err) => toast.error(err.response?.data?.detail || "Failed to record response"))
      .finally(() => setOverriding(false));
  };

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to list
      </button>

      {/* Slip info card */}
      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-gray-900">{slip.title}</h2>
            {slip.description && (
              <p className="mt-1 text-sm text-gray-600">{slip.description}</p>
            )}
            <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-500">
              {slip.event_date && <span>Event: {fmtDate(slip.event_date)}</span>}
              {slip.deadline && <span>Deadline: {fmtDateTime(slip.deadline)}</span>}
              <span>Segment: {SEGMENT_LABELS[slip.segment_type] || slip.segment_type}</span>
            </div>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
              STATUS_BADGE[slip.status] || STATUS_BADGE.draft
            } ${slip.status === "closed" ? "line-through" : ""}`}
          >
            {slip.status}
          </span>
        </div>

        {/* Response summary boxes */}
        <div className="mt-5 grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-green-50 p-4 text-center">
            <p className="text-3xl font-bold tabular-nums text-green-700">
              {detail?.yes ?? slip.yes_count}
            </p>
            <p className="mt-0.5 text-xs font-medium text-green-600">Yes</p>
          </div>
          <div className="rounded-lg bg-red-50 p-4 text-center">
            <p className="text-3xl font-bold tabular-nums text-red-700">
              {detail?.no ?? slip.no_count}
            </p>
            <p className="mt-0.5 text-xs font-medium text-red-600">No</p>
          </div>
          <div className="rounded-lg bg-gray-100 p-4 text-center">
            <p className="text-3xl font-bold tabular-nums text-gray-600">
              {detail?.pending ?? slip.pending_count}
            </p>
            <p className="mt-0.5 text-xs font-medium text-gray-500">Pending</p>
          </div>
        </div>
      </div>

      {/* Response table */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">
            {detail ? `${detail.total_responses} response${detail.total_responses !== 1 ? "s" : ""}` : "Responses"}
          </h3>
          <button onClick={loadResponses} className="btn btn-secondary btn-sm">
            Refresh
          </button>
        </div>

        {loading ? (
          <LoadingSpinner />
        ) : !detail || detail.responses.length === 0 ? (
          <EmptyState message="No responses recorded yet." />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="px-4 py-3">Parent ID</th>
                  <th className="px-4 py-3">Response</th>
                  <th className="px-4 py-3">Responded At</th>
                  <th className="px-4 py-3">Via</th>
                  <th className="px-4 py-3">Override</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {detail.responses.map((r) => {
                  const canOverride = r.response === "pending" || r.responded_via === "whatsapp";
                  const isEditing = overrideRow === r.parent_id;
                  return (
                    <tr key={r.parent_id} className="hover:bg-gray-50/50">
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">
                        {r.parent_id.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                            RESPONSE_BADGE[r.response] || RESPONSE_BADGE.pending
                          }`}
                        >
                          {r.response}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                        {fmtDateTime(r.responded_at)}
                      </td>
                      <td className="px-4 py-3 capitalize text-gray-500">
                        {r.responded_via || "—"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        {canOverride && !isEditing && (
                          <button
                            onClick={() => {
                              setOverrideRow(r.parent_id);
                              setOverrideValue("yes");
                            }}
                            className="btn-sm btn-secondary"
                          >
                            Override
                          </button>
                        )}
                        {isEditing && (
                          <div className="flex items-center gap-2">
                            <select
                              className="input py-1 text-xs"
                              value={overrideValue}
                              onChange={(e) => setOverrideValue(e.target.value)}
                            >
                              <option value="yes">Yes</option>
                              <option value="no">No</option>
                            </select>
                            <button
                              onClick={() => handleOverride(r.parent_id)}
                              disabled={overriding}
                              className="btn-sm btn-primary"
                            >
                              {overriding ? "…" : "Save"}
                            </button>
                            <button
                              onClick={() => setOverrideRow(null)}
                              className="text-xs text-gray-400 hover:text-gray-600"
                            >
                              Cancel
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared                                                              */
/* ------------------------------------------------------------------ */

// Table-shaped placeholder rather than a centred spinner: a spinner occupies
// ~128px and is then replaced by several hundred px of table, shifting
// everything below it on every load and refetch.
function LoadingSpinner() {
  return <TableSkeleton />;
}

function EmptyState({ message }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-300 py-12 text-center">
      <svg
        className="mx-auto h-10 w-10 text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  );
}
