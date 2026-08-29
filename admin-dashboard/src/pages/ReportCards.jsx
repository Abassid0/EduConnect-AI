import { useEffect, useState } from "react";
import { reportCards as rcApi } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const EMPTY_FORM = {
  student_id: "",
  academic_term: "",
  overall_grade: "",
  overall_score: "",
  position_in_class: "",
  class_size: "",
  teacher_comment: "",
};

const EMPTY_SUBJECT = { subject_name: "", score: "", grade: "", teacher_comment: "", sort_order: 0 };

function fmt(n) {
  return Number(n || 0).toLocaleString("en-NG", { maximumFractionDigits: 0 });
}

export default function ReportCards() {
  const toast = useToast();
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  // panel: null | { type: "subjects" | "deliveries", card }
  const [panel, setPanel] = useState(null);
  const [publishConfirm, setPublishConfirm] = useState(null);

  const load = () => {
    setLoading(true);
    rcApi
      .list({ limit: 100, ...(statusFilter && { status: statusFilter }) })
      .then(setCards)
      .catch(() => toast.error("Failed to load report cards"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [statusFilter]);

  const handleCreate = (e) => {
    e.preventDefault();
    if (!form.student_id.trim() || !form.academic_term.trim()) return;
    setSaving(true);
    rcApi
      .create({
        student_id: form.student_id.trim(),
        academic_term: form.academic_term.trim(),
        overall_grade: form.overall_grade || null,
        overall_score: form.overall_score ? Number(form.overall_score) : null,
        position_in_class: form.position_in_class ? Number(form.position_in_class) : null,
        class_size: form.class_size ? Number(form.class_size) : null,
        teacher_comment: form.teacher_comment || null,
      })
      .then(() => {
        toast.success("Report card created");
        setShowCreate(false);
        setForm(EMPTY_FORM);
        load();
      })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed to create"))
      .finally(() => setSaving(false));
  };

  const handlePublish = (card) => {
    if (publishConfirm !== card.id) { setPublishConfirm(card.id); return; }
    setPublishConfirm(null);
    rcApi
      .publish(card.id)
      .then(() => { toast.success("Published — notifications queued"); load(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed to publish"));
  };

  const togglePanel = (type, card) => {
    setPanel((prev) =>
      prev && prev.type === type && prev.card.id === card.id ? null : { type, card }
    );
  };

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold tracking-tight text-gray-900">Report Cards</h1>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input max-w-[150px]"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
          </select>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="btn btn-primary btn-sm"
          >
            {showCreate ? "Cancel" : "+ New Card"}
          </button>
        </div>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-800">New Report Card</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Student ID (UUID) *</label>
              <input className="input w-full" required value={form.student_id}
                onChange={(e) => setForm({ ...form, student_id: e.target.value })}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Academic Term *</label>
              <input className="input w-full" required value={form.academic_term}
                onChange={(e) => setForm({ ...form, academic_term: e.target.value })}
                placeholder="e.g. 2025/2026 Term 1" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Overall Grade</label>
              <input className="input w-full" value={form.overall_grade}
                onChange={(e) => setForm({ ...form, overall_grade: e.target.value })}
                placeholder="A / Distinction" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Overall Score</label>
              <input type="number" min="0" max="100" step="0.01" className="input w-full" value={form.overall_score}
                onChange={(e) => setForm({ ...form, overall_score: e.target.value })} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Position in Class</label>
              <input type="number" min="1" className="input w-full" value={form.position_in_class}
                onChange={(e) => setForm({ ...form, position_in_class: e.target.value })} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Class Size</label>
              <input type="number" min="1" className="input w-full" value={form.class_size}
                onChange={(e) => setForm({ ...form, class_size: e.target.value })} />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Teacher Comment</label>
              <textarea className="input w-full" rows={2} value={form.teacher_comment}
                onChange={(e) => setForm({ ...form, teacher_comment: e.target.value })} />
            </div>
          </div>
          <div className="flex justify-end">
            <button type="submit" disabled={saving} className="btn btn-primary btn-sm">
              {saving ? "Creating…" : "Create Draft"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <LoadingSpinner />
      ) : cards.length === 0 ? (
        <EmptyState message="No report cards yet" />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Student ID</th>
                <th className="px-4 py-3">Term</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Grade</th>
                <th className="px-4 py-3">Position</th>
                <th className="px-4 py-3">Subjects</th>
                <th className="px-4 py-3">Acknowledged</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {cards.map((card) => {
                const isPanelOpen = panel?.card.id === card.id;
                return (
                  <>
                    <tr key={card.id} className={`hover:bg-gray-50/50 ${isPanelOpen ? "bg-blue-50/20" : ""}`}>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500 max-w-[120px] truncate">
                        {card.student_id}
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
                        {card.academic_term}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge value={card.status} />
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {card.overall_grade || "—"}
                        {card.overall_score != null && (
                          <span className="ml-1 text-xs text-gray-400">({card.overall_score})</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600 tabular-nums">
                        {card.position_in_class && card.class_size
                          ? `${card.position_in_class} / ${card.class_size}`
                          : card.position_in_class || "—"}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-gray-600">{card.subject_count}</td>
                      <td className="px-4 py-3 tabular-nums text-gray-600">
                        {card.acknowledged_count} / {card.total_parents}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex gap-1">
                          {card.status === "draft" && (
                            <>
                              <button
                                onClick={() => togglePanel("subjects", card)}
                                className={`btn-sm ${isPanelOpen && panel.type === "subjects" ? "btn-primary" : "btn-secondary"}`}
                              >
                                Add Subjects
                              </button>
                              <button
                                onClick={() => handlePublish(card)}
                                className={`btn-sm ${publishConfirm === card.id ? "btn-danger" : "btn-primary"}`}
                              >
                                {publishConfirm === card.id ? "Confirm?" : "Publish"}
                              </button>
                            </>
                          )}
                          {card.status === "published" && (
                            <button
                              onClick={() => togglePanel("deliveries", card)}
                              className={`btn-sm ${isPanelOpen && panel.type === "deliveries" ? "btn-primary" : "btn-secondary"}`}
                            >
                              View Deliveries
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {isPanelOpen && panel.type === "subjects" && (
                      <tr key={`${card.id}-subjects`}>
                        <td colSpan={8} className="bg-blue-50/50 px-6 py-4">
                          <SubjectEditor
                            card={card}
                            onSaved={() => { load(); setPanel(null); }}
                            onCancel={() => setPanel(null)}
                          />
                        </td>
                      </tr>
                    )}

                    {isPanelOpen && panel.type === "deliveries" && (
                      <tr key={`${card.id}-deliveries`}>
                        <td colSpan={8} className="bg-blue-50/50 px-6 py-4">
                          <DeliveryView
                            card={card}
                            onUpdate={load}
                            onClose={() => setPanel(null)}
                          />
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Subject Editor                                                     */
/* ------------------------------------------------------------------ */

function SubjectEditor({ card, onSaved, onCancel }) {
  const toast = useToast();
  const [subjects, setSubjects] = useState([{ ...EMPTY_SUBJECT }]);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    rcApi
      .get(card.id)
      .then((data) => {
        if (data.subjects && data.subjects.length > 0) {
          setSubjects(
            data.subjects.map((s) => ({
              subject_name: s.subject_name || "",
              score: s.score != null ? String(s.score) : "",
              grade: s.grade || "",
              teacher_comment: s.teacher_comment || "",
              sort_order: s.sort_order ?? 0,
            }))
          );
        }
        setLoaded(true);
      })
      .catch(() => { toast.error("Failed to load subjects"); setLoaded(true); });
  }, [card.id]);

  const setField = (idx, field, value) =>
    setSubjects((prev) => prev.map((s, i) => (i === idx ? { ...s, [field]: value } : s)));

  const addRow = () => setSubjects((prev) => [...prev, { ...EMPTY_SUBJECT, sort_order: prev.length }]);

  const removeRow = (idx) =>
    setSubjects((prev) => prev.filter((_, i) => i !== idx));

  const handleSave = () => {
    const payload = subjects
      .filter((s) => s.subject_name.trim())
      .map((s, i) => ({
        subject_name: s.subject_name.trim(),
        score: s.score !== "" ? Number(s.score) : null,
        grade: s.grade || null,
        teacher_comment: s.teacher_comment || null,
        sort_order: i,
      }));
    if (payload.length === 0) { toast.error("Add at least one subject"); return; }
    setSaving(true);
    rcApi
      .setSubjects(card.id, payload)
      .then(() => { toast.success("Subjects saved"); onSaved(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed to save"))
      .finally(() => setSaving(false));
  };

  if (!loaded) return <div className="py-4 text-center text-sm text-gray-400">Loading…</div>;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Subjects — {card.academic_term}</h3>
        <button onClick={onCancel} className="text-xs text-gray-400 hover:text-gray-600">Close ✕</button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white mb-3">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-3 py-2">Subject Name *</th>
              <th className="px-3 py-2">Score</th>
              <th className="px-3 py-2">Grade</th>
              <th className="px-3 py-2">Teacher Comment</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {subjects.map((s, idx) => (
              <tr key={idx}>
                <td className="px-3 py-2">
                  <input className="input w-full py-1 text-xs" value={s.subject_name}
                    onChange={(e) => setField(idx, "subject_name", e.target.value)}
                    placeholder="e.g. Mathematics" />
                </td>
                <td className="px-3 py-2">
                  <input type="number" min="0" max="100" step="0.5" className="input w-20 py-1 text-xs" value={s.score}
                    onChange={(e) => setField(idx, "score", e.target.value)} />
                </td>
                <td className="px-3 py-2">
                  <input className="input w-16 py-1 text-xs" value={s.grade}
                    onChange={(e) => setField(idx, "grade", e.target.value)}
                    placeholder="A / B+" />
                </td>
                <td className="px-3 py-2">
                  <input className="input w-full py-1 text-xs" value={s.teacher_comment}
                    onChange={(e) => setField(idx, "teacher_comment", e.target.value)} />
                </td>
                <td className="px-3 py-2">
                  <button onClick={() => removeRow(idx)} className="text-red-400 hover:text-red-600 text-xs">✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2">
        <button onClick={addRow} className="btn-sm btn-secondary">+ Add Row</button>
        <button onClick={handleSave} disabled={saving} className="btn-sm btn-primary ml-auto">
          {saving ? "Saving…" : "Save Subjects"}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Delivery View                                                      */
/* ------------------------------------------------------------------ */

function DeliveryView({ card, onUpdate, onClose }) {
  const toast = useToast();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = () => {
    rcApi
      .get(card.id)
      .then((data) => { setDetail(data); })
      .catch(() => toast.error("Failed to load delivery details"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [card.id]);

  const handleAdminAck = (delivery) => {
    setBusy(delivery.parent_id);
    rcApi
      .adminAcknowledge(card.id, delivery.parent_id)
      .then(() => { toast.success("Acknowledged"); load(); onUpdate(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed"))
      .finally(() => setBusy(null));
  };

  if (loading) return <div className="py-4 text-center text-sm text-gray-400">Loading…</div>;
  if (!detail) return null;

  const summary = detail.delivery_summary || {};
  const deliveries = summary.deliveries || [];

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Deliveries — {card.academic_term}</h3>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">Close ✕</button>
      </div>

      <div className="mb-4 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg bg-white border border-gray-200 p-3">
          <p className="text-xs text-gray-500">Total Parents</p>
          <p className="text-xl font-bold text-gray-900 tabular-nums">{summary.total_parents ?? 0}</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-3">
          <p className="text-xs text-gray-500">Delivered</p>
          <p className="text-xl font-bold text-blue-600 tabular-nums">{summary.delivered_count ?? 0}</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-3">
          <p className="text-xs text-gray-500">Acknowledged</p>
          <p className="text-xl font-bold text-green-600 tabular-nums">{summary.acknowledged_count ?? 0}</p>
        </div>
      </div>

      {deliveries.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-4">No delivery records yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-3 py-2">Parent ID</th>
                <th className="px-3 py-2">Delivered At</th>
                <th className="px-3 py-2">Acknowledged At</th>
                <th className="px-3 py-2">Via</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {deliveries.map((d) => (
                <tr key={d.parent_id} className="hover:bg-gray-50/50">
                  <td className="px-3 py-2 font-mono text-xs text-gray-500 max-w-[120px] truncate">{d.parent_id}</td>
                  <td className="px-3 py-2 whitespace-nowrap text-gray-600">
                    {d.delivered_at ? new Date(d.delivered_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap text-gray-600">
                    {d.acknowledged_at ? new Date(d.acknowledged_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-3 py-2 capitalize text-gray-500">{d.acknowledged_via || "—"}</td>
                  <td className="px-3 py-2">
                    {!d.acknowledged_at && (
                      <button
                        disabled={busy === d.parent_id}
                        onClick={() => handleAdminAck(d)}
                        className="btn-sm btn-secondary py-0 text-xs"
                      >
                        {busy === d.parent_id ? "…" : "Admin Ack"}
                      </button>
                    )}
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

/* ------------------------------------------------------------------ */
/*  Shared small components                                            */
/* ------------------------------------------------------------------ */

function LoadingSpinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-300 py-12 text-center">
      <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  );
}
