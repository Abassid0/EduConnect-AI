import { useEffect, useState } from "react";
import { broadcasts as broadcastsApi } from "../api/client";
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
  sending: "bg-blue-100 text-blue-700",
  sent: "bg-green-100 text-green-700",
  cancelled: "bg-gray-100 text-gray-400 line-through",
};

const EMPTY_FORM = {
  title: "",
  body: "",
  segment_type: "all",
  segment_value: "",
  programme_id: "",
  specific_ids: "",
};

export default function Broadcast() {
  const [tab, setTab] = useState("Compose");

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-gray-900">
            Broadcast
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Send targeted messages to parent groups.
          </p>
        </div>
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
          {["Compose", "History"].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                tab === t
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {tab === "Compose" && <ComposeTab onSent={() => setTab("History")} />}
      {tab === "History" && (
        <HistoryTab onEdit={() => setTab("Compose")} />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Compose Tab                                                         */
/* ------------------------------------------------------------------ */

function ComposeTab({ onSent }) {
  const toast = useToast();
  const [form, setForm] = useState(EMPTY_FORM);
  const [programmes, setProgrammes] = useState([]);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState(null);
  const [previewCount, setPreviewCount] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    client
      .get("/programmes")
      .then((r) => setProgrammes(r.data || []))
      .catch(() => {});
  }, []);

  const buildSegmentValue = () => {
    if (form.segment_type === "programme") return form.programme_id || null;
    if (form.segment_type === "specific") {
      const ids = form.specific_ids
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      return ids.length ? JSON.stringify(ids) : null;
    }
    return null;
  };

  const handleSaveDraft = (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.body.trim()) return;
    setSaving(true);
    broadcastsApi
      .create({
        title: form.title.trim(),
        body: form.body.trim(),
        segment_type: form.segment_type,
        segment_value: buildSegmentValue(),
      })
      .then((b) => {
        toast.success("Draft saved");
        setDraft(b);
        setPreviewCount(null);
        setShowConfirm(false);
      })
      .catch((err) =>
        toast.error(err.response?.data?.detail || "Failed to save draft")
      )
      .finally(() => setSaving(false));
  };

  const handlePreview = () => {
    if (!draft) return;
    setPreviewing(true);
    broadcastsApi
      .preview(draft.id)
      .then((r) => setPreviewCount(r.recipient_count))
      .catch(() => toast.error("Failed to preview recipients"))
      .finally(() => setPreviewing(false));
  };

  const handleSend = () => {
    if (!draft) return;
    setSending(true);
    broadcastsApi
      .send(draft.id)
      .then(() => {
        toast.success(`Broadcast queued — sending to ${previewCount} parent(s)`);
        setForm(EMPTY_FORM);
        setDraft(null);
        setPreviewCount(null);
        setShowConfirm(false);
        onSent();
      })
      .catch((err) =>
        toast.error(err.response?.data?.detail || "Failed to send broadcast")
      )
      .finally(() => setSending(false));
  };

  const hasDraft = !!draft;

  return (
    <form
      onSubmit={handleSaveDraft}
      className="rounded-xl border border-gray-200 bg-white p-5 space-y-5"
    >
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-sm font-medium text-gray-700">Title *</label>
          <span className="text-xs text-gray-400">{form.title.length}/200</span>
        </div>
        <input
          className="input w-full"
          value={form.title}
          maxLength={200}
          onChange={(e) => {
            setForm({ ...form, title: e.target.value });
            setDraft(null);
            setPreviewCount(null);
            setShowConfirm(false);
          }}
          placeholder="e.g. Term 1 Fees Reminder"
          required
          disabled={hasDraft}
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-sm font-medium text-gray-700">Message *</label>
          <span className="text-xs text-gray-400">{form.body.length} chars</span>
        </div>
        <textarea
          className="input w-full resize-none"
          rows={6}
          value={form.body}
          onChange={(e) => {
            setForm({ ...form, body: e.target.value });
            setDraft(null);
            setPreviewCount(null);
            setShowConfirm(false);
          }}
          placeholder="Type your message here. Parents will receive this exactly as written."
          required
          disabled={hasDraft}
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Send to
        </label>
        <select
          className="input w-full max-w-xs"
          value={form.segment_type}
          onChange={(e) => {
            setForm({
              ...form,
              segment_type: e.target.value,
              programme_id: "",
              specific_ids: "",
            });
            setDraft(null);
            setPreviewCount(null);
            setShowConfirm(false);
          }}
          disabled={hasDraft}
        >
          <option value="all">All Parents</option>
          <option value="programme">Parents in a Programme</option>
          <option value="has_overdue">Parents with Overdue Balance</option>
          <option value="specific">Specific Parent IDs</option>
        </select>

        {form.segment_type === "programme" && !hasDraft && (
          <div className="mt-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Programme
            </label>
            <select
              className="input w-full max-w-xs"
              value={form.programme_id}
              onChange={(e) =>
                setForm({ ...form, programme_id: e.target.value })
              }
              required
            >
              <option value="">Select a programme…</option>
              {programmes.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {form.segment_type === "specific" && !hasDraft && (
          <div className="mt-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Parent IDs
            </label>
            <textarea
              className="input w-full resize-none font-mono text-xs"
              rows={4}
              value={form.specific_ids}
              onChange={(e) =>
                setForm({ ...form, specific_ids: e.target.value })
              }
              placeholder="Paste one parent UUID per line"
            />
          </div>
        )}
      </div>

      {!hasDraft && (
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving}
            className="btn btn-primary btn-sm"
          >
            {saving ? "Saving…" : "Save Draft"}
          </button>
        </div>
      )}

      {hasDraft && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 space-y-3">
          <p className="text-sm font-medium text-blue-800">
            Draft saved: <span className="font-semibold">"{draft.title}"</span>
          </p>

          {previewCount === null ? (
            <button
              type="button"
              onClick={handlePreview}
              disabled={previewing}
              className="btn btn-secondary btn-sm"
            >
              {previewing ? "Counting…" : "Preview Recipients"}
            </button>
          ) : (
            <p className="text-sm text-blue-700">
              This message will be sent to{" "}
              <span className="font-bold">{previewCount}</span> parent
              {previewCount !== 1 ? "s" : ""}.
            </p>
          )}

          {previewCount !== null && previewCount > 0 && !showConfirm && (
            <button
              type="button"
              onClick={() => setShowConfirm(true)}
              className="btn btn-primary btn-sm"
            >
              Send Broadcast
            </button>
          )}

          {showConfirm && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-2">
              <p className="text-sm font-medium text-amber-800">
                Are you sure? This will send to{" "}
                <span className="font-bold">{previewCount}</span> parent
                {previewCount !== 1 ? "s" : ""} immediately.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={sending}
                  className="btn btn-primary btn-sm"
                >
                  {sending ? "Sending…" : "Confirm Send"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowConfirm(false)}
                  className="btn btn-secondary btn-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              setDraft(null);
              setPreviewCount(null);
              setShowConfirm(false);
            }}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Discard draft and start over
          </button>
        </div>
      )}
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  History Tab                                                         */
/* ------------------------------------------------------------------ */

function HistoryTab({ onEdit }) {
  const toast = useToast();
  const [broadcasts, setBroadcasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pendingCancel, setPendingCancel] = useState(null);

  const load = () => {
    setLoading(true);
    broadcastsApi
      .list()
      .then(setBroadcasts)
      .catch(() => toast.error("Failed to load broadcasts"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleCancelClick = (b) => {
    if (pendingCancel === b.id) {
      broadcastsApi
        .cancel(b.id)
        .then(() => {
          toast.success("Broadcast cancelled");
          setPendingCancel(null);
          load();
        })
        .catch(() => toast.error("Failed to cancel broadcast"));
    } else {
      setPendingCancel(b.id);
    }
  };

  const fmtDate = (iso) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("en-NG", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {broadcasts.length} broadcast{broadcasts.length !== 1 && "s"}
        </span>
        <button onClick={load} className="btn btn-secondary btn-sm">
          Refresh
        </button>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : broadcasts.length === 0 ? (
        <EmptyState message="No broadcasts yet — compose your first message." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Segment</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Recipients</th>
                <th className="px-4 py-3 text-right">Delivered</th>
                <th className="px-4 py-3">Sent At</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {broadcasts.map((b) => {
                const isPending = pendingCancel === b.id;
                return (
                  <tr key={b.id} className="hover:bg-gray-50/50">
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-[200px] truncate">
                      {b.title}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {SEGMENT_LABELS[b.segment_type] || b.segment_type}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          STATUS_BADGE[b.status] || STATUS_BADGE.draft
                        }`}
                      >
                        {b.status}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums text-gray-600">
                      {b.recipient_count}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums text-green-600">
                      {b.delivered_count}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                      {fmtDate(b.sent_at)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {b.status === "draft" && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              setPendingCancel(null);
                              handleCancelClick(b);
                            }}
                            className={`btn-sm ${
                              isPending ? "btn-danger" : "btn-secondary"
                            }`}
                          >
                            {isPending ? "Confirm?" : "Cancel"}
                          </button>
                          {isPending && (
                            <button
                              onClick={() => setPendingCancel(null)}
                              className="text-xs text-gray-400 hover:text-gray-600"
                            >
                              Keep
                            </button>
                          )}
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
    </>
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
          d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"
        />
      </svg>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  );
}
