import { useCallback, useEffect, useRef, useState } from "react";
import { admin } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "./Toast";

export default function AssignDropdown({ conversationId, currentAgentId, onAssign }) {
  const { hasRole } = useAuth();
  const { success, error: showError } = useToast();
  const [agents, setAgents] = useState([]);
  const [open, setOpen] = useState(false);
  const [assigning, setAssigning] = useState(null);
  const dropdownRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (open && agents.length === 0) {
      admin
        .agents()
        .then((res) => setAgents(res.data))
        .catch(() => showError("Failed to load agents"));
    }
  }, [open]);

  const close = useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!open || !dropdownRef.current) return;

    const el = dropdownRef.current;
    const focusable = el.querySelectorAll('button');
    if (focusable.length > 0) focusable[0].focus();

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
        return;
      }
      if (e.key === "Tab") {
        const nodes = el.querySelectorAll('button');
        if (nodes.length === 0) return;
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    el.addEventListener("keydown", handleKeyDown);
    return () => el.removeEventListener("keydown", handleKeyDown);
  }, [open, close]);

  if (!hasRole("super_admin", "admin", "support_agent")) return null;

  const handleAssign = async (agentId, agentName) => {
    if (assigning) return;
    setAssigning(agentId);
    try {
      await admin.assign(conversationId, agentId);
      onAssign?.(agentId);
      success(`Assigned to ${agentName}`);
      close();
    } catch (err) {
      const msg = err.response?.status === 403
        ? "You don't have permission to assign agents"
        : "Failed to assign agent";
      showError(msg);
    } finally {
      setAssigning(null);
    }
  };

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        className="btn-secondary btn-sm"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {currentAgentId ? "Reassign" : "Assign"}
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-10"
            aria-hidden="true"
            onClick={close}
          />
          <div
            ref={dropdownRef}
            role="listbox"
            aria-label="Select agent"
            className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg"
          >
            {agents.length === 0 ? (
              <p className="px-3 py-2 text-sm text-gray-500" role="status">Loading agents...</p>
            ) : (
              agents.map((a) => (
                <button
                  key={a.id}
                  role="option"
                  aria-selected={a.id === currentAgentId}
                  onClick={() => handleAssign(a.id, a.full_name)}
                  disabled={assigning === a.id}
                  className={`flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 ${
                    a.id === currentAgentId ? "bg-brand-50 text-brand-700" : "text-gray-700"
                  }`}
                >
                  <span className="flex-1 text-left truncate">{a.full_name}</span>
                  <span className="text-xs text-gray-500">{a.role}</span>
                  {assigning === a.id && (
                    <div className="h-3 w-3 animate-spin rounded-full border border-brand-600 border-t-transparent" aria-hidden="true" />
                  )}
                </button>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
