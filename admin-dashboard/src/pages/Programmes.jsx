import { useCallback, useEffect, useState } from "react";
import { programmes } from "../api/client";

const CATEGORIES = [
  { value: "pre_primary", label: "Pre-Primary" },
  { value: "primary", label: "Primary" },
  { value: "secondary", label: "Secondary" },
];

const CATEGORY_LEVELS = {
  pre_primary: [
    { value: "nursery_1", label: "Nursery 1" },
    { value: "nursery_2", label: "Nursery 2" },
    { value: "kg_1", label: "KG 1" },
    { value: "kg_2", label: "KG 2" },
  ],
  primary: [
    { value: "primary_1", label: "Primary 1" },
    { value: "primary_2", label: "Primary 2" },
    { value: "primary_3", label: "Primary 3" },
    { value: "primary_4", label: "Primary 4" },
    { value: "primary_5", label: "Primary 5" },
    { value: "primary_6", label: "Primary 6" },
  ],
  secondary: [
    { value: "jss_1", label: "JSS 1" },
    { value: "jss_2", label: "JSS 2" },
    { value: "jss_3", label: "JSS 3" },
    { value: "sss_1", label: "SSS 1" },
    { value: "sss_2", label: "SSS 2" },
    { value: "sss_3", label: "SSS 3" },
  ],
};

const SSS_LEVELS = ["sss_1", "sss_2", "sss_3"];

const TRACKS = [
  { value: "science", label: "Science" },
  { value: "commercial", label: "Commercial" },
  { value: "arts", label: "Arts" },
];

const CATEGORY_COLORS = {
  pre_primary: "bg-pink-100 text-pink-800",
  primary: "bg-blue-100 text-blue-800",
  secondary: "bg-green-100 text-green-800",
};

const LEVEL_LABELS = Object.fromEntries(
  Object.values(CATEGORY_LEVELS)
    .flat()
    .map((l) => [l.value, l.label])
);

const TRACK_LABELS = Object.fromEntries(TRACKS.map((t) => [t.value, t.label]));

const CATEGORY_LABELS = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label])
);

const FEE_STRUCTURES = [
  { value: "annual", label: "Annual" },
  { value: "per_term", label: "Per Term" },
];

const EMPTY_FORM = {
  name: "",
  description: "",
  category: "primary",
  level: "",
  track: "",
  age_range_min: "",
  age_range_max: "",
  fee: "",
  fee_structure: "annual",
  term_1_fee: "",
  term_2_fee: "",
  term_3_fee: "",
  academic_year: "",
  currency: "NGN",
  duration: "",
  delivery_mode: "",
  available_slots: 0,
  instructor: "",
  is_active: true,
};

export default function Programmes() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCategory, setFilterCategory] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await programmes.list({
        active_only: !showInactive,
        category: filterCategory || undefined,
      });
      setItems(data);
    } catch {
      setError("Failed to load programmes");
    } finally {
      setLoading(false);
    }
  }, [filterCategory, showInactive]);

  useEffect(() => {
    load();
  }, [load]);

  const flash = (msg) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(""), 3000);
  };

  const toggleActive = async (p) => {
    try {
      await programmes.update(p.id, { is_active: !p.is_active });
      flash(`Programme ${p.is_active ? "deactivated" : "activated"}`);
      load();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update programme");
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Programmes</h1>
          <p className="text-sm text-gray-500">
            {items.length} programme{items.length !== 1 ? "s" : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              className="rounded"
            />
            Show inactive
          </label>
          <button
            onClick={() => {
              setShowForm(true);
              setEditingId(null);
            }}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            + Add Programme
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
          <button
            onClick={() => setError("")}
            className="ml-2 font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}
      {success && (
        <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
          {success}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Category
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Level
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Track
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Fee
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Slots
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                Status
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium uppercase text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {items.map((p) => (
              <tr
                key={p.id}
                className={!p.is_active ? "bg-gray-50 opacity-60" : ""}
              >
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-gray-900">
                    {p.name}
                  </div>
                  {p.description && (
                    <div className="max-w-xs truncate text-xs text-gray-500">
                      {p.description}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                      CATEGORY_COLORS[p.category] ||
                      "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {CATEGORY_LABELS[p.category] || p.category}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {LEVEL_LABELS[p.level] || p.level || "—"}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {TRACK_LABELS[p.track] || p.track || "—"}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">
                  {p.fee_structure === "per_term" ? (
                    <div>
                      <span className="font-medium">Per Term</span>
                      <div className="text-xs text-gray-500 mt-0.5 space-y-0.5">
                        <div>T1: {p.currency} {Number(p.term_1_fee).toLocaleString()}</div>
                        <div>T2: {p.currency} {Number(p.term_2_fee).toLocaleString()}</div>
                        <div>T3: {p.currency} {Number(p.term_3_fee).toLocaleString()}</div>
                      </div>
                    </div>
                  ) : (
                    <span className="font-medium">{p.currency} {Number(p.fee).toLocaleString()}</span>
                  )}
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">
                  {p.available_slots}
                </td>
                <td className="px-6 py-4">
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                      p.is_active
                        ? "bg-green-100 text-green-800"
                        : "bg-red-100 text-red-800"
                    }`}
                  >
                    {p.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setEditingId(p.id);
                        setShowForm(false);
                      }}
                      className="text-sm text-brand-600 hover:text-brand-800"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => toggleActive(p)}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      {p.is_active ? "Deactivate" : "Activate"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td
                  colSpan={8}
                  className="px-6 py-12 text-center text-sm text-gray-500"
                >
                  No programmes found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <ProgrammeModal
          onClose={() => setShowForm(false)}
          onSaved={() => {
            setShowForm(false);
            flash("Programme created");
            load();
          }}
          setError={setError}
        />
      )}

      {editingId && (
        <ProgrammeModal
          programme={items.find((p) => p.id === editingId)}
          onClose={() => setEditingId(null)}
          onSaved={() => {
            setEditingId(null);
            flash("Programme updated");
            load();
          }}
          setError={setError}
        />
      )}
    </div>
  );
}

function ProgrammeModal({ programme, onClose, onSaved, setError }) {
  const isEdit = !!programme;
  const [form, setForm] = useState(
    isEdit
      ? {
          name: programme.name || "",
          description: programme.description || "",
          category: programme.category || "primary",
          level: programme.level || "",
          track: programme.track || "",
          age_range_min: programme.age_range_min ?? "",
          age_range_max: programme.age_range_max ?? "",
          fee: programme.fee || "",
          fee_structure: programme.fee_structure || "annual",
          term_1_fee: programme.term_1_fee ?? "",
          term_2_fee: programme.term_2_fee ?? "",
          term_3_fee: programme.term_3_fee ?? "",
          academic_year: programme.academic_year || "",
          currency: programme.currency || "NGN",
          duration: programme.duration || "",
          delivery_mode: programme.delivery_mode || "",
          available_slots: programme.available_slots ?? 0,
          instructor: programme.instructor || "",
          is_active: programme.is_active ?? true,
        }
      : { ...EMPTY_FORM }
  );
  const [submitting, setSubmitting] = useState(false);

  const availableLevels = CATEGORY_LEVELS[form.category] || [];
  const showTrack = SSS_LEVELS.includes(form.level);

  const handleCategoryChange = (cat) => {
    setForm({ ...form, category: cat, level: "", track: "" });
  };

  const handleLevelChange = (lvl) => {
    const updates = { level: lvl };
    if (!SSS_LEVELS.includes(lvl)) {
      updates.track = "";
    }
    setForm({ ...form, ...updates });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        name: form.name,
        description: form.description || null,
        category: form.category,
        level: form.level || null,
        track: form.track || null,
        age_range_min: form.age_range_min === "" ? null : Number(form.age_range_min),
        age_range_max: form.age_range_max === "" ? null : Number(form.age_range_max),
        fee: Number(form.fee),
        fee_structure: form.fee_structure,
        term_1_fee: form.fee_structure === "per_term" && form.term_1_fee !== "" ? Number(form.term_1_fee) : null,
        term_2_fee: form.fee_structure === "per_term" && form.term_2_fee !== "" ? Number(form.term_2_fee) : null,
        term_3_fee: form.fee_structure === "per_term" && form.term_3_fee !== "" ? Number(form.term_3_fee) : null,
        academic_year: form.academic_year || null,
        currency: form.currency,
        duration: form.duration || null,
        delivery_mode: form.delivery_mode || null,
        available_slots: Number(form.available_slots),
        instructor: form.instructor || null,
        is_active: form.is_active,
      };
      if (isEdit) {
        await programmes.update(programme.id, payload);
      } else {
        await programmes.create(payload);
      }
      onSaved();
    } catch (err) {
      setError(
        err.response?.data?.detail || `Failed to ${isEdit ? "update" : "create"} programme`
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <h2 className="mb-4 text-lg font-bold text-gray-900">
          {isEdit ? `Edit: ${programme.name}` : "Add Programme"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Name *
            </label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              placeholder="e.g. Primary 3 Programme"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              rows={2}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Category *
              </label>
              <select
                value={form.category}
                onChange={(e) => handleCategoryChange(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Level
              </label>
              <select
                value={form.level}
                onChange={(e) => handleLevelChange(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                <option value="">Select level</option>
                {availableLevels.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>
            {showTrack && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Track
                </label>
                <select
                  value={form.track}
                  onChange={(e) =>
                    setForm({ ...form, track: e.target.value })
                  }
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">None</option>
                  {TRACKS.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Age Min
              </label>
              <input
                type="number"
                min={0}
                value={form.age_range_min}
                onChange={(e) =>
                  setForm({ ...form, age_range_min: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Age Max
              </label>
              <input
                type="number"
                min={0}
                value={form.age_range_max}
                onChange={(e) =>
                  setForm({ ...form, age_range_max: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Fee Structure *
              </label>
              <select
                value={form.fee_structure}
                onChange={(e) => setForm({ ...form, fee_structure: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {FEE_STRUCTURES.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Academic Year
              </label>
              <input
                value={form.academic_year}
                onChange={(e) => setForm({ ...form, academic_year: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g. 2025/2026"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {form.fee_structure === "per_term" ? "Total Annual Fee (NGN) *" : "Fee (NGN) *"}
              </label>
              <input
                type="number"
                required
                min={0}
                step="0.01"
                value={form.fee}
                onChange={(e) => setForm({ ...form, fee: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Available Slots
              </label>
              <input
                type="number"
                min={0}
                value={form.available_slots}
                onChange={(e) =>
                  setForm({ ...form, available_slots: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>

          {form.fee_structure === "per_term" && (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  1st Term Fee *
                </label>
                <input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={form.term_1_fee}
                  onChange={(e) => setForm({ ...form, term_1_fee: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  2nd Term Fee *
                </label>
                <input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={form.term_2_fee}
                  onChange={(e) => setForm({ ...form, term_2_fee: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  3rd Term Fee *
                </label>
                <input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={form.term_3_fee}
                  onChange={(e) => setForm({ ...form, term_3_fee: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Duration
              </label>
              <input
                value={form.duration}
                onChange={(e) =>
                  setForm({ ...form, duration: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g. 1 term"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Delivery Mode
              </label>
              <input
                value={form.delivery_mode}
                onChange={(e) =>
                  setForm({ ...form, delivery_mode: e.target.value })
                }
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="e.g. in-person"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Instructor
            </label>
            <input
              value={form.instructor}
              onChange={(e) =>
                setForm({ ...form, instructor: e.target.value })
              }
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) =>
                setForm({ ...form, is_active: e.target.checked })
              }
              className="rounded"
            />
            Active
          </label>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {submitting
                ? isEdit
                  ? "Saving..."
                  : "Creating..."
                : isEdit
                  ? "Save Changes"
                  : "Create Programme"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
