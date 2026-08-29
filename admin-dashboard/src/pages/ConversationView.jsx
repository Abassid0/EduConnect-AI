import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { admin, tickets as ticketsApi } from "../api/client";
import AssignDropdown from "../components/AssignDropdown";
import BotStatusToggle from "../components/BotStatusToggle";
import ConfirmModal from "../components/ConfirmModal";
import CustomerProfile from "../components/CustomerProfile";
import InternalNotes from "../components/InternalNotes";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

export default function ConversationView() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const messagesEndRef = useRef(null);

  const [messages, setMessages] = useState([]);
  const [convMeta, setConvMeta] = useState(null);
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [useTemplate, setUseTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [closeModal, setCloseModal] = useState(false);
  const [closing, setClosing] = useState(false);
  const profileRef = useRef(null);

  const loadConversation = async () => {
    try {
      setLoadError(null);
      const [msgsRes, inboxRes] = await Promise.all([
        admin.messages(conversationId),
        admin.inbox({ limit: 200 }),
      ]);
      setMessages(msgsRes.data);
      const conv = inboxRes.data.find((c) => c.id === conversationId);
      setConvMeta(conv || null);

      const ticketsRes = await ticketsApi.list({ limit: 100 });
      const related = ticketsRes.data.find(
        (t) => t.conversation_id === conversationId
      );
      if (related) setTicket(related);
    } catch (err) {
      const msg = err.response?.status === 404
        ? "Conversation not found"
        : "Failed to load conversation";
      setLoadError(msg);
      showError(msg, { label: "Retry", onClick: () => loadConversation() });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConversation();
    const interval = setInterval(() => {
      admin.messages(conversationId).then((r) => setMessages(r.data)).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [conversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!showProfile || !profileRef.current) return;
    const handleKey = (e) => {
      if (e.key === "Escape") {
        setShowProfile(false);
      }
    };
    const el = profileRef.current;
    el.addEventListener("keydown", handleKey);
    return () => el.removeEventListener("keydown", handleKey);
  }, [showProfile]);

  const whatsappNumber = convMeta?.whatsapp_id || messages[0]?.sender || "";

  const sendReply = async () => {
    if (!replyText.trim() || sending) return;
    setSending(true);
    try {
      const payload = {
        whatsapp_number: whatsappNumber,
        message: replyText.trim(),
        msg_type: useTemplate ? "template" : "text",
      };
      if (useTemplate && templateName) {
        payload.template_name = templateName;
      }
      await admin.reply(payload);
      setReplyText("");
      setUseTemplate(false);
      setTemplateName("");
      success("Message sent");
      setTimeout(() => {
        admin.messages(conversationId).then((r) => setMessages(r.data)).catch(() => {});
      }, 500);
    } catch (err) {
      const msg = err.response?.status === 429
        ? "Too many messages — wait a moment and try again"
        : "Message failed to send";
      showError(msg, { label: "Retry", onClick: sendReply });
    } finally {
      setSending(false);
    }
  };

  const handleClose = async () => {
    setClosing(true);
    try {
      await admin.close(conversationId);
      success("Conversation closed");
      navigate("/inbox");
    } catch (err) {
      const msg = err.response?.status === 404
        ? "Conversation was already closed"
        : "Failed to close conversation";
      showError(msg);
      setCloseModal(false);
    } finally {
      setClosing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center" role="status">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden="true" />
        <span className="sr-only">Loading conversation</span>
      </div>
    );
  }

  if (loadError && !convMeta) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6">
        <p className="text-sm text-gray-600">{loadError}</p>
        <button onClick={() => { setLoading(true); loadConversation(); }} className="btn-primary btn-sm">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3">
          <button
            onClick={() => navigate("/inbox")}
            className="rounded-lg p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700 lg:hidden"
            aria-label="Back to inbox"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="truncate text-sm font-semibold text-gray-900">
                {whatsappNumber}
              </h2>
              {convMeta && <StatusBadge value={convMeta.status} />}
            </div>
          </div>

          <div className="flex flex-shrink-0 items-center gap-2">
            {convMeta && (
              <BotStatusToggle
                conversationId={conversationId}
                status={convMeta.status}
                onUpdate={(s) => setConvMeta({ ...convMeta, status: s })}
              />
            )}

            <AssignDropdown
              conversationId={conversationId}
              currentAgentId={convMeta?.assigned_agent_id}
              onAssign={() => loadConversation()}
            />

            <button
              onClick={() => setCloseModal(true)}
              className="btn-danger btn-sm"
            >
              Close
            </button>

            <button
              onClick={() => setShowProfile(!showProfile)}
              className="btn-secondary btn-sm lg:hidden"
              aria-label={showProfile ? "Hide customer profile" : "Show customer profile"}
            >
              Profile
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-brand-50/40 px-4 py-4" role="log" aria-label="Conversation messages">
          {messages.length === 0 ? (
            <p className="text-center text-sm text-gray-500 py-12">
              No messages yet
            </p>
          ) : (
            <div className="mx-auto max-w-2xl space-y-2">
              {messages.map((m, i) => {
                const isOutbound = m.direction === "outbound";
                const isAgent = m.sender?.startsWith("agent:");
                const showDate =
                  i === 0 ||
                  new Date(m.created_at).toDateString() !==
                    new Date(messages[i - 1].created_at).toDateString();

                return (
                  <div key={m.id}>
                    {showDate && (
                      <div className="my-3 text-center">
                        <span className="rounded-full bg-white px-3 py-1 text-xs text-gray-500 shadow-sm">
                          {new Date(m.created_at).toLocaleDateString("en-NG", {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      </div>
                    )}

                    <div
                      className={`flex ${isOutbound ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-2xl px-4 py-2.5 shadow-sm ${
                          isOutbound
                            ? isAgent
                              ? "bg-blue-600 text-white"
                              : "bg-brand-600 text-white"
                            : "bg-white text-gray-900"
                        }`}
                      >
                        {isAgent && (
                          <p className="mb-1 text-xs text-blue-200">Agent reply</p>
                        )}
                        {!isAgent && isOutbound && (
                          <p className="mb-1 text-xs text-brand-200">Bot</p>
                        )}
                        <p className="text-sm whitespace-pre-wrap break-words">
                          {extractBody(m.content)}
                        </p>
                        <div
                          className={`mt-1 flex items-center gap-1.5 text-[10px] ${
                            isOutbound ? "text-white/80 justify-end" : "text-gray-500"
                          }`}
                        >
                          <span>
                            {new Date(m.created_at).toLocaleTimeString("en-NG", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          {isOutbound && (
                            <DeliveryIcon status={m.delivery_status} />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Reply input */}
        <div className="border-t border-gray-200 bg-white p-3">
          <div className="mx-auto flex max-w-2xl gap-2">
            <div className="relative flex-1">
              <input
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" && !e.shiftKey && sendReply()
                }
                placeholder={
                  useTemplate
                    ? "Template parameters (comma-separated)..."
                    : "Type a message..."
                }
                className="input pr-20"
                disabled={sending}
                aria-label={useTemplate ? "Template parameters" : "Reply message"}
                maxLength={4096}
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                <button
                  onClick={() => setUseTemplate(!useTemplate)}
                  className={`rounded px-1.5 py-0.5 text-xs font-medium transition-colors ${
                    useTemplate
                      ? "bg-brand-100 text-brand-700"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                  aria-label={useTemplate ? "Switch to text mode" : "Switch to template mode"}
                  aria-pressed={useTemplate}
                >
                  Template
                </button>
              </div>
            </div>

            {useTemplate && (
              <input
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="Template name"
                className="input w-40"
                aria-label="Template name"
              />
            )}

            <button
              onClick={sendReply}
              disabled={sending || !replyText.trim()}
              className="btn-primary"
            >
              {sending ? "Sending..." : "Send"}
            </button>
          </div>
        </div>
      </div>

      {/* Right sidebar — profile + notes */}
      {showProfile && (
        <div
          className="fixed inset-0 z-30 bg-black/30 lg:hidden"
          aria-hidden="true"
          onClick={() => setShowProfile(false)}
        />
      )}
      <aside
        ref={profileRef}
        className={`w-80 flex-shrink-0 overflow-y-auto border-l border-gray-200 bg-white ${
          showProfile ? "fixed inset-y-0 right-0 z-40 shadow-xl" : "hidden lg:block"
        }`}
        aria-label="Customer profile"
      >
        {showProfile && (
          <button
            onClick={() => setShowProfile(false)}
            className="absolute right-2 top-2 rounded p-1 text-gray-500 hover:bg-gray-100 lg:hidden"
            aria-label="Close profile panel"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        <CustomerProfile whatsappNumber={whatsappNumber} />

        {ticket && (
          <InternalNotes
            ticketId={ticket.id}
            conversationId={conversationId}
          />
        )}
      </aside>

      <ConfirmModal
        open={closeModal}
        title="Close this conversation?"
        message="The parent will need to start a new chat to reach support again. This action cannot be undone."
        confirmLabel="Close conversation"
        danger
        loading={closing}
        onConfirm={handleClose}
        onCancel={() => setCloseModal(false)}
      />
    </div>
  );
}

function extractBody(content) {
  if (!content) return "";
  if (typeof content === "string") return content;
  if (content.body) return content.body;
  if (content.text?.body) return content.text.body;
  if (content.interactive?.body?.text) return content.interactive.body.text;
  if (content.template?.name) return `[Template: ${content.template.name}]`;
  return JSON.stringify(content);
}

function DeliveryIcon({ status }) {
  const label =
    status === "read" ? "Read" : status === "delivered" ? "Delivered" : "Sent";

  if (status === "read") {
    return (
      <svg className="h-3 w-3 text-blue-300" viewBox="0 0 16 16" fill="currentColor" aria-label={label} role="img">
        <path d="M12.354 4.354a.5.5 0 00-.708-.708L5.5 9.793 3.354 7.646a.5.5 0 10-.708.708l2.5 2.5a.5.5 0 00.708 0l6.5-6.5z" />
        <path d="M10.354 4.354a.5.5 0 00-.708-.708L3.5 9.793 1.354 7.646a.5.5 0 10-.708.708l2.5 2.5a.5.5 0 00.708 0l6.5-6.5z" />
      </svg>
    );
  }
  if (status === "delivered") {
    return (
      <svg className="h-3 w-3" viewBox="0 0 16 16" fill="currentColor" aria-label={label} role="img">
        <path d="M12.354 4.354a.5.5 0 00-.708-.708L5.5 9.793 3.354 7.646a.5.5 0 10-.708.708l2.5 2.5a.5.5 0 00.708 0l6.5-6.5z" />
        <path d="M10.354 4.354a.5.5 0 00-.708-.708L3.5 9.793 1.354 7.646a.5.5 0 10-.708.708l2.5 2.5a.5.5 0 00.708 0l6.5-6.5z" />
      </svg>
    );
  }
  return (
    <svg className="h-3 w-3" viewBox="0 0 16 16" fill="currentColor" aria-label={label} role="img">
      <path d="M12.354 4.354a.5.5 0 00-.708-.708L5.5 9.793 3.354 7.646a.5.5 0 10-.708.708l2.5 2.5a.5.5 0 00.708 0l6.5-6.5z" />
    </svg>
  );
}
