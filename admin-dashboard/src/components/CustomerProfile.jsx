import { useEffect, useState } from "react";
import { admin } from "../api/client";
import { useAuth } from "../context/AuthContext";
import StatusBadge from "./StatusBadge";

export default function CustomerProfile({ whatsappNumber }) {
  const { hasRole } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("details");

  useEffect(() => {
    if (!whatsappNumber) return;
    setLoading(true);
    admin
      .customer(whatsappNumber)
      .then((r) => setProfile(r.data))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, [whatsappNumber]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8" role="status">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" aria-hidden="true" />
        <span className="sr-only">Loading customer profile</span>
      </div>
    );
  }

  if (!profile) {
    return (
      <p className="px-4 py-6 text-sm text-gray-500 italic text-center">
        No customer profile found
      </p>
    );
  }

  const { parent, students, payments, tickets, preferences } = profile;

  const tabs = [
    { id: "details", label: "Details" },
    { id: "students", label: `Children (${students.length})` },
  ];
  if (hasRole("super_admin", "admin", "finance")) {
    tabs.push({ id: "payments", label: `Payments (${payments.length})` });
  }
  tabs.push({ id: "tickets", label: `Tickets (${tickets.length})` });
  if (preferences) {
    tabs.push({ id: "prefs", label: "Prefs" });
  }

  return (
    <div>
      <div className="border-b border-gray-200 px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-900">
          {parent.full_name || "Unknown"}
        </h3>
        <p className="text-xs text-gray-500">{parent.whatsapp_number}</p>
        {parent.email && (
          <p className="text-xs text-gray-500">{parent.email}</p>
        )}
      </div>

      <div className="flex border-b border-gray-200 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`whitespace-nowrap px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === t.id
                ? "border-brand-600 text-brand-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="p-4 max-h-80 overflow-y-auto">
        {activeTab === "details" && (
          <dl className="space-y-2 text-sm">
            <Row label="WhatsApp" value={parent.whatsapp_number} />
            <Row label="Email" value={parent.email || "—"} />
            <Row
              label="Since"
              value={new Date(parent.created_at).toLocaleDateString("en-NG")}
            />
          </dl>
        )}

        {activeTab === "students" && (
          <div className="space-y-3">
            {students.length === 0 && (
              <p className="text-xs text-gray-500 italic">No children registered</p>
            )}
            {students.map((s) => (
              <div key={s.id} className="rounded-lg border border-gray-200 p-3">
                <p className="text-sm font-medium">{s.full_name}</p>
                <p className="text-xs text-gray-500">
                  ID: {s.registration_id} &middot; Age: {s.age || "—"}
                </p>
                {s.enrollments?.map((e) => (
                  <div key={e.id} className="mt-1 flex items-center gap-2">
                    <StatusBadge value={e.status} />
                    <span className="text-xs text-gray-500">
                      {e.enrolled_at
                        ? new Date(e.enrolled_at).toLocaleDateString("en-NG")
                        : ""}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {activeTab === "payments" && (
          <div className="space-y-2">
            {payments.length === 0 && (
              <p className="text-xs text-gray-500 italic">No payments</p>
            )}
            {payments.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
              >
                <div>
                  <p className="text-sm font-mono">{p.reference}</p>
                  <p className="text-xs text-gray-500">
                    {p.paid_at
                      ? new Date(p.paid_at).toLocaleDateString("en-NG")
                      : "Pending"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold">
                    {Number(p.amount).toLocaleString("en-NG", {
                      style: "currency",
                      currency: "NGN",
                    })}
                  </p>
                  <StatusBadge value={p.status} />
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "tickets" && (
          <div className="space-y-2">
            {tickets.length === 0 && (
              <p className="text-xs text-gray-500 italic">No tickets</p>
            )}
            {tickets.map((t) => (
              <div
                key={t.id}
                className="rounded-lg border border-gray-200 p-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono text-gray-500">
                    {t.ticket_number}
                  </span>
                  <StatusBadge value={t.status} />
                </div>
                <p className="mt-1 text-sm">{t.subject}</p>
                <div className="mt-1 flex gap-2">
                  <StatusBadge value={t.priority} />
                  <span className="text-xs text-gray-400">
                    {t.department}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "prefs" && preferences && (
          <dl className="space-y-2 text-sm">
            {Object.entries(preferences).map(([key, val]) => (
              <Row
                key={key}
                label={key.replace(/_/g, " ")}
                value={
                  <span
                    className={val ? "text-green-600" : "text-gray-400"}
                  >
                    {val ? "ON" : "OFF"}
                  </span>
                }
              />
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-500 capitalize">{label}</dt>
      <dd className="font-medium text-gray-900">{value}</dd>
    </div>
  );
}
