import { useState } from "react";
import { admin } from "../api/client";
import { useToast } from "./Toast";

export default function BotStatusToggle({ conversationId, status, onUpdate }) {
  const [loading, setLoading] = useState(false);
  const { success, error: showError } = useToast();
  const isPaused = status === "paused_for_agent";

  const toggle = async () => {
    if (loading) return;
    setLoading(true);
    const previousStatus = status;
    const newStatus = isPaused ? "active" : "paused_for_agent";
    onUpdate?.(newStatus);

    try {
      if (isPaused) {
        await admin.resume(conversationId);
        success("Bot resumed");
      } else {
        await admin.pause(conversationId);
        success("You've taken over — bot is paused");
      }
    } catch (err) {
      onUpdate?.(previousStatus);
      const msg = err.response?.status === 403
        ? "You don't have permission to change bot status"
        : "Failed to toggle bot status";
      showError(msg, { label: "Retry", onClick: toggle });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-3" role="status" aria-label={`Bot is ${isPaused ? "paused" : "active"}`}>
      <div className="flex items-center gap-2">
        <div
          className={`h-2.5 w-2.5 rounded-full ${
            isPaused ? "bg-amber-400" : "bg-green-400"
          }`}
          aria-hidden="true"
        />
        <span className="text-sm font-medium text-gray-700">
          {isPaused ? "Human Agent" : "Bot Active"}
        </span>
      </div>
      <button
        onClick={toggle}
        disabled={loading}
        className={`btn-sm ${isPaused ? "btn-primary" : "btn-secondary"}`}
        aria-label={isPaused ? "Resume bot for this conversation" : "Take over from bot"}
      >
        {loading
          ? "Switching..."
          : isPaused
            ? "Resume Bot"
            : "Take Over"}
      </button>
    </div>
  );
}
