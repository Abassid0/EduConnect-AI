import { useEffect, useState } from "react";
import { tickets as ticketsApi } from "../api/client";
import { useToast } from "./Toast";

export default function InternalNotes({ ticketId, conversationId }) {
  const [notes, setNotes] = useState([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const { success, error: showError } = useToast();

  useEffect(() => {
    if (ticketId) {
      ticketsApi
        .notes(ticketId)
        .then((r) => setNotes(r.data))
        .catch(() => showError("Failed to load notes"));
    }
  }, [ticketId]);

  const addNote = async () => {
    if (!text.trim() || !ticketId || loading) return;
    setLoading(true);
    try {
      const { data } = await ticketsApi.addNote(ticketId, text.trim(), conversationId);
      setNotes((prev) => [...prev, data]);
      setText("");
      success("Note added");
    } catch (err) {
      const msg = err.response?.status === 403
        ? "You don't have permission to add notes"
        : "Failed to add note";
      showError(msg, { label: "Retry", onClick: addNote });
    } finally {
      setLoading(false);
    }
  };

  if (!ticketId) return null;

  return (
    <div className="border-t border-gray-200">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
        aria-expanded={!collapsed}
        aria-controls="internal-notes-panel"
      >
        <span>Internal Notes ({notes.length})</span>
        <svg
          className={`h-4 w-4 transition-transform ${collapsed ? "" : "rotate-180"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!collapsed && (
        <div id="internal-notes-panel" className="px-4 pb-4">
          <div className="space-y-3 max-h-60 overflow-y-auto mb-3">
            {notes.length === 0 && (
              <p className="text-xs text-gray-500 italic">No notes yet</p>
            )}
            {notes.map((n) => (
              <div
                key={n.id}
                className="rounded-lg bg-yellow-50 border border-yellow-200 p-3"
              >
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{n.content}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {new Date(n.created_at).toLocaleString("en-NG")}
                </p>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && addNote()}
              placeholder="Add a note (staff only)..."
              className="input flex-1"
              aria-label="Internal note"
              maxLength={2000}
            />
            <button
              onClick={addNote}
              disabled={loading || !text.trim()}
              className="btn-secondary btn-sm"
            >
              {loading ? "Adding..." : "Add"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
