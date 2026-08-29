import { useEffect, useState } from "react";
import { calendar as calendarApi } from "../api/client";
import { useToast } from "../components/Toast";

const EVENT_TYPES = [
  "term_start",
  "term_end",
  "exam_week",
  "pta",
  "holiday",
  "custom",
];

const TYPE_LABELS = {
  term_start: "Term Start",
  term_end: "Term End",
  exam_week: "Exam Week",
  pta: "PTA Meeting",
  holiday: "Holiday",
  custom: "Event",
};

const TYPE_BADGE = {
  term_start: "bg-blue-100 text-blue-700",
  term_end: "bg-blue-100 text-blue-700",
  exam_week: "bg-red-100 text-red-700",
  pta: "bg-purple-100 text-purple-700",
  holiday: "bg-green-100 text-green-700",
  custom: "bg-gray-100 text-gray-600",
};

const EMPTY_FORM = {
  title: "",
  event_type: "custom",
  start_date: "",
  end_date: "",
  school_term: "",
  description: "",
  is_published: true,
};

export default function Calendar() {
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [pendingDeactivate, setPendingDeactivate] = useState(null);

  const load = () => {
    setLoading(true);
    calendarApi
      .list()
      .then((r) => setEvents(r.data))
      .catch(() => toast.error("Failed to load events"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.start_date) return;
    setSaving(true);
    const payload = {
      title: form.title.trim(),
      event_type: form.event_type,
      start_date: form.start_date,
      end_date: form.end_date || null,
      school_term: form.school_term.trim() || null,
      description: form.description.trim() || null,
      is_published: form.is_published,
    };
    calendarApi
      .create(payload)
      .then(() => {
        toast.success(`Event "${payload.title}" created`);
        setShowForm(false);
        setForm(EMPTY_FORM);
        load();
      })
      .catch((err) =>
        toast.error(err.response?.data?.detail || "Failed to create event")
      )
      .finally(() => setSaving(false));
  };

  const handleDeactivateClick = (event) => {
    if (pendingDeactivate === event.id) {
      calendarApi
        .deactivate(event.id)
        .then(() => {
          toast.success(`"${event.title}" deactivated`);
          setPendingDeactivate(null);
          load();
        })
        .catch(() => toast.error("Failed to deactivate event"));
    } else {
      setPendingDeactivate(event.id);
    }
  };

  const published = events.filter((e) => e.is_published);
  const unpublished = events.filter((e) => !e.is_published);

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-gray-900">
            Academic Calendar
          </h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Manage term dates and school events visible to parents.
          </p>
        </div>
        <button
          onClick={() => {
            setShowForm(!showForm);
            setPendingDeactivate(null);
          }}
          className="btn btn-primary btn-sm shrink-0"
        >
          {showForm ? "Cancel" : "+ Add Event"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-gray-200 bg-white p-5 space-y-4"
        >
          <h2 className="text-sm font-semibold text-gray-900">New Event</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Title *
              </label>
              <input
                className="input w-full"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="e.g. First Term Begins"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Event Type
              </label>
              <select
                className="input w-full"
                value={form.event_type}
                onChange={(e) =>
                  setForm({ ...form, event_type: e.target.value })
                }
              >
                {EVENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                School Term
              </label>
              <input
                className="input w-full"
                value={form.school_term}
                onChange={(e) =>
                  setForm({ ...form, school_term: e.target.value })
                }
                placeholder="e.g. Term 1 2026"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Start Date *
              </label>
              <input
                type="date"
                className="input w-full"
                value={form.start_date}
                onChange={(e) =>
                  setForm({ ...form, start_date: e.target.value })
                }
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                End Date
              </label>
              <input
                type="date"
                className="input w-full"
                value={form.end_date}
                min={form.start_date || undefined}
                onChange={(e) =>
                  setForm({ ...form, end_date: e.target.value })
                }
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Description
              </label>
              <input
                className="input w-full"
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                placeholder="Optional short note for parents"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_published}
                onChange={(e) =>
                  setForm({ ...form, is_published: e.target.checked })
                }
                className="rounded border-gray-300"
              />
              Publish immediately (visible to parents)
            </label>
            <button
              type="submit"
              disabled={saving}
              className="btn btn-primary btn-sm ml-auto"
            >
              {saving ? "Saving..." : "Create Event"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <LoadingSpinner />
      ) : events.length === 0 ? (
        <EmptyState message="No events scheduled yet — add the first one above." />
      ) : (
        <>
          <EventTable
            title="Published Events"
            events={published}
            pendingDeactivate={pendingDeactivate}
            onDeactivate={handleDeactivateClick}
            onCancelPending={() => setPendingDeactivate(null)}
          />
          {unpublished.length > 0 && (
            <EventTable
              title="Unpublished Events"
              events={unpublished}
              pendingDeactivate={pendingDeactivate}
              onDeactivate={handleDeactivateClick}
              onCancelPending={() => setPendingDeactivate(null)}
              dimmed
            />
          )}
        </>
      )}
    </div>
  );
}

function EventTable({
  title,
  events,
  pendingDeactivate,
  onDeactivate,
  onCancelPending,
  dimmed = false,
}) {
  if (events.length === 0) return null;

  return (
    <div className={dimmed ? "opacity-60" : ""}>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-700">{title}</h2>
        <span className="text-xs text-gray-400">
          {events.length} event{events.length !== 1 && "s"}
        </span>
      </div>
      <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-4 py-3">Event</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Term</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {events.map((ev) => {
              const isPending = pendingDeactivate === ev.id;
              const dateDisplay = ev.end_date && ev.end_date !== ev.start_date
                ? `${ev.start_date} – ${ev.end_date}`
                : ev.start_date;
              return (
                <tr key={ev.id} className="hover:bg-gray-50/50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{ev.title}</p>
                    {ev.description && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {ev.description}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        TYPE_BADGE[ev.event_type] || TYPE_BADGE.custom
                      }`}
                    >
                      {TYPE_LABELS[ev.event_type] || ev.event_type}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-gray-600 tabular-nums">
                    {dateDisplay}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {ev.school_term || "—"}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {ev.is_published && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onDeactivate(ev)}
                          className={`btn-sm ${
                            isPending ? "btn-danger" : "btn-secondary"
                          }`}
                        >
                          {isPending ? "Confirm?" : "Deactivate"}
                        </button>
                        {isPending && (
                          <button
                            onClick={onCancelPending}
                            className="text-xs text-gray-400 hover:text-gray-600"
                          >
                            Cancel
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
    </div>
  );
}

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
          d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
        />
      </svg>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  );
}
