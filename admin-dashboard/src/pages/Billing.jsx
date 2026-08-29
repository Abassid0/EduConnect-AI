import { useEffect, useState } from "react";
import { billing as billingApi, paymentPlans as plansApi } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useToast } from "../components/Toast";

const TABS = ["Invoices", "Fee Types", "Revenue"];
const INVOICE_STATUSES = ["", "unpaid", "partial", "paid", "overdue", "on_plan", "cancelled"];
const FEE_CATEGORIES = ["tuition", "material", "service", "contribution", "custom"];

function fmt(n) {
  return Number(n || 0).toLocaleString("en-NG", { maximumFractionDigits: 0 });
}

export default function Billing() {
  const [tab, setTab] = useState("Invoices");

  return (
    <div className="space-y-6 p-4 lg:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-xl font-bold tracking-tight text-gray-900">
          Billing
        </h1>
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
          {TABS.map((t) => (
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

      {tab === "Invoices" && <InvoicesTab />}
      {tab === "Fee Types" && <FeeTypesTab />}
      {tab === "Revenue" && <RevenueTab />}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Invoices Tab                                                       */
/* ------------------------------------------------------------------ */

const PLAN_ELIGIBLE = ["unpaid", "partial", "overdue"];

function InvoicesTab() {
  const toast = useToast();
  const [invoices, setInvoices] = useState([]);
  const [plansMap, setPlansMap] = useState({});
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(null);
  const [planPanel, setPlanPanel] = useState(null);

  const load = () => {
    setLoading(true);
    const params = { limit: 100, ...(status && { status }) };
    Promise.all([billingApi.invoices(params), plansApi.listPlans()])
      .then(([invRes, planRes]) => {
        setInvoices(invRes.data);
        const map = {};
        for (const p of planRes.data) {
          if (p.invoice_id) map[p.invoice_id] = p;
        }
        setPlansMap(map);
      })
      .catch(() => toast.error("Failed to load invoices"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [status]);

  const handleSend = (inv) => {
    setSending(inv.id);
    billingApi
      .sendInvoice(inv.id)
      .then(() => toast.success(`Invoice ${inv.invoice_number} sent`))
      .catch(() => toast.error("Failed to send invoice"))
      .finally(() => setSending(null));
  };

  const handleRemind = (inv) => {
    setSending(inv.id);
    billingApi
      .remindInvoice(inv.id)
      .then(() => toast.success(`Reminder sent for ${inv.invoice_number}`))
      .catch(() => toast.error("Failed to send reminder"))
      .finally(() => setSending(null));
  };

  const [cancelConfirm, setCancelConfirm] = useState(null);
  const handleCancel = (inv) => {
    if (cancelConfirm !== inv.id) { setCancelConfirm(inv.id); return; }
    setCancelConfirm(null);
    billingApi
      .cancelInvoice(inv.id)
      .then(() => { toast.success("Invoice cancelled"); load(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed to cancel"));
  };

  const togglePanel = (invoiceId, mode) => {
    setPlanPanel((prev) =>
      prev && prev.invoiceId === invoiceId && prev.mode === mode
        ? null
        : { invoiceId, mode }
    );
  };

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="input max-w-[160px]"
        >
          {INVOICE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? s.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "All Statuses"}
            </option>
          ))}
        </select>
        <span className="ml-auto text-sm text-gray-500">
          {invoices.length} invoice{invoices.length !== 1 && "s"}
        </span>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : invoices.length === 0 ? (
        <EmptyState message="No invoices found" />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Invoice #</th>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-right">Paid</th>
                <th className="px-4 py-3 text-right">Remaining</th>
                <th className="px-4 py-3">Due Date</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {invoices.map((inv) => {
                const remaining = Number(inv.total_amount) - Number(inv.amount_paid);
                const existingPlan = plansMap[inv.id];
                const canCreatePlan = PLAN_ELIGIBLE.includes(inv.status) && !existingPlan;
                const isPanelOpen = planPanel?.invoiceId === inv.id;

                return (
                  <>
                    <tr key={inv.id} className={`hover:bg-gray-50/50 ${isPanelOpen ? "bg-blue-50/30" : ""}`}>
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-gray-600">
                        {inv.invoice_number}
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {inv.title}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">
                        N{fmt(inv.total_amount)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums text-green-600">
                        N{fmt(inv.amount_paid)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums font-medium">
                        N{fmt(remaining)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-gray-500">
                        {inv.due_date || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge value={inv.status} />
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {inv.status !== "paid" && inv.status !== "cancelled" && inv.status !== "on_plan" && (
                            <>
                              <button onClick={() => handleSend(inv)} disabled={sending === inv.id} className="btn-sm btn-secondary">Send</button>
                              <button onClick={() => handleRemind(inv)} disabled={sending === inv.id} className="btn-sm btn-secondary">Remind</button>
                              {canCreatePlan && (
                                <button
                                  onClick={() => togglePanel(inv.id, "create")}
                                  className={`btn-sm ${isPanelOpen && planPanel.mode === "create" ? "btn-primary" : "btn-secondary"}`}
                                >
                                  Set Up Plan
                                </button>
                              )}
                              <button
                                onClick={() => handleCancel(inv)}
                                className={`btn-sm ${cancelConfirm === inv.id ? "btn-danger" : "btn-secondary"}`}
                              >
                                {cancelConfirm === inv.id ? "Confirm?" : "Cancel"}
                              </button>
                            </>
                          )}
                          {(inv.status === "on_plan" || existingPlan) && (
                            <button
                              onClick={() => togglePanel(inv.id, "view")}
                              className={`btn-sm ${isPanelOpen && planPanel.mode === "view" ? "btn-primary" : "btn-secondary"}`}
                            >
                              View Plan
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {isPanelOpen && planPanel.mode === "create" && (
                      <tr key={`${inv.id}-create`}>
                        <td colSpan={8} className="bg-blue-50/50 px-6 py-4">
                          <SetUpPlanPanel
                            invoice={inv}
                            onSuccess={(plan) => {
                              setPlansMap((m) => ({ ...m, [inv.id]: plan }));
                              setPlanPanel(null);
                              load();
                            }}
                            onCancel={() => setPlanPanel(null)}
                          />
                        </td>
                      </tr>
                    )}

                    {isPanelOpen && planPanel.mode === "view" && existingPlan && (
                      <tr key={`${inv.id}-view`}>
                        <td colSpan={8} className="bg-blue-50/50 px-6 py-4">
                          <PlanDetailPanel
                            plan={existingPlan}
                            onUpdate={() => {
                              plansApi.listPlans().then((r) => {
                                const map = {};
                                for (const p of r.data) {
                                  if (p.invoice_id) map[p.invoice_id] = p;
                                }
                                setPlansMap(map);
                              });
                              load();
                            }}
                            onClose={() => setPlanPanel(null)}
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
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Set Up Plan Panel                                                  */
/* ------------------------------------------------------------------ */

function SetUpPlanPanel({ invoice, onSuccess, onCancel }) {
  const toast = useToast();
  const [form, setForm] = useState({ installment_count: 3, frequency: "monthly", start_date: "" });
  const [saving, setSaving] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.start_date) return;
    setSaving(true);
    plansApi
      .createPlan(invoice.id, {
        parent_id: invoice.parent_id,
        installment_count: Number(form.installment_count),
        frequency: form.frequency,
        start_date: form.start_date,
      })
      .then((r) => {
        toast.success("Payment plan created");
        onSuccess(r.data);
      })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed to create plan"))
      .finally(() => setSaving(false));
  };

  const unit = form.installment_count > 0
    ? (Number(invoice.total_amount) / Number(form.installment_count)).toLocaleString("en-NG", { maximumFractionDigits: 0 })
    : "—";

  return (
    <div className="max-w-xl">
      <h3 className="mb-3 font-semibold text-gray-900 text-sm">Set Up Payment Plan — {invoice.invoice_number}</h3>
      <form onSubmit={handleSubmit} className="grid gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Installments (2–24)</label>
          <input
            type="number" min="2" max="24" required
            className="input w-full"
            value={form.installment_count}
            onChange={(e) => setForm({ ...form, installment_count: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">Frequency</label>
          <select className="input w-full" value={form.frequency} onChange={(e) => setForm({ ...form, frequency: e.target.value })}>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Bi-weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600">First Payment Date</label>
          <input type="date" required className="input w-full" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        </div>
        <div className="sm:col-span-3 flex items-center gap-3">
          <span className="text-xs text-gray-500">≈ N{unit} per installment · Total N{fmt(invoice.total_amount)}</span>
          <div className="ml-auto flex gap-2">
            <button type="button" onClick={onCancel} className="btn-sm btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-sm btn-primary">{saving ? "Creating…" : "Create Plan"}</button>
          </div>
        </div>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Plan Detail Panel                                                  */
/* ------------------------------------------------------------------ */

function PlanDetailPanel({ plan, onUpdate, onClose }) {
  const toast = useToast();
  const [busy, setBusy] = useState(null);
  const [cancelConfirm, setCancelConfirm] = useState(false);

  const paid = plan.installments.filter((i) => ["paid", "waived"].includes(i.status)).length;
  const total = plan.installments.length;
  const paidAmt = plan.installments
    .filter((i) => ["paid", "waived"].includes(i.status))
    .reduce((s, i) => s + Number(i.amount), 0);
  const pct = total > 0 ? Math.round((paid / total) * 100) : 0;

  const handleMarkPaid = (inst) => {
    setBusy(inst.id);
    plansApi
      .markPaid(plan.id, inst.id)
      .then(() => { toast.success(`Installment #${inst.installment_number} marked paid`); onUpdate(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed"))
      .finally(() => setBusy(null));
  };

  const handleWaive = (inst) => {
    setBusy(inst.id);
    plansApi
      .waive(plan.id, inst.id)
      .then(() => { toast.success(`Installment #${inst.installment_number} waived`); onUpdate(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed"))
      .finally(() => setBusy(null));
  };

  const handleCancel = () => {
    if (!cancelConfirm) { setCancelConfirm(true); return; }
    setBusy("cancel");
    plansApi
      .cancelPlan(plan.id)
      .then(() => { toast.success("Plan cancelled"); onClose(); onUpdate(); })
      .catch((e) => toast.error(e.response?.data?.detail || "Failed to cancel plan"))
      .finally(() => setBusy(null));
  };

  const statusColor = (s) => {
    if (s === "paid") return "text-green-600 bg-green-50";
    if (s === "waived") return "text-blue-600 bg-blue-50";
    if (s === "overdue") return "text-red-600 bg-red-50";
    return "text-gray-600 bg-gray-50";
  };

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-gray-900 text-sm">
          Payment Plan · {plan.frequency.charAt(0).toUpperCase() + plan.frequency.slice(1)} · {plan.status}
        </h3>
        <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">Close ✕</button>
      </div>

      <div className="mb-4 grid grid-cols-3 gap-3 text-center">
        <div className="rounded-lg bg-white border border-gray-200 p-3">
          <p className="text-xs text-gray-500">Total</p>
          <p className="font-bold tabular-nums text-gray-900">N{fmt(plan.total_amount)}</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-3">
          <p className="text-xs text-gray-500">Paid</p>
          <p className="font-bold tabular-nums text-green-600">N{fmt(paidAmt)}</p>
        </div>
        <div className="rounded-lg bg-white border border-gray-200 p-3">
          <p className="text-xs text-gray-500">Remaining</p>
          <p className="font-bold tabular-nums text-amber-600">N{fmt(Number(plan.total_amount) - paidAmt)}</p>
        </div>
      </div>

      <div className="mb-4">
        <div className="mb-1 flex justify-between text-xs text-gray-500">
          <span>{paid} of {total} installments complete</span>
          <span>{pct}%</span>
        </div>
        <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
          <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: `${pct}%` }} />
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white mb-3">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">Due Date</th>
              <th className="px-3 py-2 text-right">Amount</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {plan.installments.map((inst) => (
              <tr key={inst.id} className="hover:bg-gray-50/50">
                <td className="px-3 py-2 font-medium">{inst.installment_number}</td>
                <td className="px-3 py-2 whitespace-nowrap">{inst.due_date}</td>
                <td className="px-3 py-2 text-right tabular-nums">N{fmt(inst.amount)}</td>
                <td className="px-3 py-2">
                  <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${statusColor(inst.status)}`}>
                    {inst.status}
                  </span>
                </td>
                <td className="px-3 py-2">
                  {inst.status === "pending" || inst.status === "overdue" ? (
                    <div className="flex gap-1">
                      <button
                        disabled={busy === inst.id}
                        onClick={() => handleMarkPaid(inst)}
                        className="btn-sm btn-secondary py-0 text-xs"
                      >
                        Mark Paid
                      </button>
                      <button
                        disabled={busy === inst.id}
                        onClick={() => handleWaive(inst)}
                        className="btn-sm btn-secondary py-0 text-xs"
                      >
                        Waive
                      </button>
                    </div>
                  ) : (
                    <span className="text-gray-300">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {plan.status === "active" && (
        <button
          onClick={handleCancel}
          disabled={busy === "cancel"}
          className={`btn-sm ${cancelConfirm ? "btn-danger" : "btn-secondary"}`}
        >
          {busy === "cancel" ? "Cancelling…" : cancelConfirm ? "Confirm Cancel Plan?" : "Cancel Plan"}
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Fee Types Tab                                                      */
/* ------------------------------------------------------------------ */

function FeeTypesTab() {
  const toast = useToast();
  const [feeTypes, setFeeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    category: "tuition",
    description: "",
    default_amount: "",
    is_recurring: false,
  });
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    billingApi
      .feeTypes({ include_inactive: true })
      .then((r) => setFeeTypes(r.data))
      .catch(() => toast.error("Failed to load fee types"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    const payload = {
      name: form.name.trim(),
      category: form.category,
      description: form.description.trim() || null,
      default_amount: form.default_amount ? Number(form.default_amount) : null,
      is_recurring: form.is_recurring,
    };
    billingApi
      .createFeeType(payload)
      .then(() => {
        toast.success(`Fee type "${form.name}" created`);
        setShowForm(false);
        setForm({
          name: "",
          category: "tuition",
          description: "",
          default_amount: "",
          is_recurring: false,
        });
        load();
      })
      .catch((err) =>
        toast.error(err.response?.data?.detail || "Failed to create fee type")
      )
      .finally(() => setSaving(false));
  };

  const handleDelete = (ft) => {
    if (!confirm(`Deactivate "${ft.name}"?`)) return;
    billingApi
      .deleteFeeType(ft.id)
      .then(() => {
        toast.success("Fee type deactivated");
        load();
      })
      .catch(() => toast.error("Failed to deactivate"));
  };

  return (
    <>
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-500">
          {feeTypes.length} fee type{feeTypes.length !== 1 && "s"}
        </span>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn btn-primary btn-sm"
        >
          {showForm ? "Cancel" : "+ Add Fee Type"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-gray-200 bg-white p-4 space-y-4"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Name *
              </label>
              <input
                className="input w-full"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. School Fees"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Category
              </label>
              <select
                className="input w-full"
                value={form.category}
                onChange={(e) =>
                  setForm({ ...form, category: e.target.value })
                }
              >
                {FEE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Default Amount (NGN)
              </label>
              <input
                className="input w-full"
                type="number"
                min="0"
                step="100"
                value={form.default_amount}
                onChange={(e) =>
                  setForm({ ...form, default_amount: e.target.value })
                }
                placeholder="Optional"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Description
              </label>
              <input
                className="input w-full"
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
                placeholder="Optional"
              />
            </div>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.is_recurring}
                onChange={(e) =>
                  setForm({ ...form, is_recurring: e.target.checked })
                }
                className="rounded border-gray-300"
              />
              Recurring fee
            </label>
            <button
              type="submit"
              disabled={saving}
              className="btn btn-primary btn-sm ml-auto"
            >
              {saving ? "Saving..." : "Create Fee Type"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <LoadingSpinner />
      ) : feeTypes.length === 0 ? (
        <EmptyState message="No fee types defined yet" />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Slug</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3 text-right">Default Amount</th>
                <th className="px-4 py-3">Recurring</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {feeTypes.map((ft) => (
                <tr key={ft.id} className="hover:bg-gray-50/50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {ft.name}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {ft.slug}
                  </td>
                  <td className="px-4 py-3 capitalize text-gray-600">
                    {ft.category}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right tabular-nums">
                    {ft.default_amount ? `N${fmt(ft.default_amount)}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {ft.is_recurring ? (
                      <span className="badge bg-blue-100 text-blue-700">
                        Yes
                      </span>
                    ) : (
                      <span className="text-gray-400">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {ft.is_active ? (
                      <span className="badge bg-green-100 text-green-700">
                        Active
                      </span>
                    ) : (
                      <span className="badge bg-gray-100 text-gray-500">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {ft.is_active && (
                      <button
                        onClick={() => handleDelete(ft)}
                        className="btn-sm btn-danger"
                      >
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Revenue Tab                                                        */
/* ------------------------------------------------------------------ */

function RevenueTab() {
  const toast = useToast();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    billingApi
      .stats()
      .then((r) => setStats(r.data))
      .catch(() => toast.error("Failed to load billing stats"))
      .finally(() => setLoading(false));
  }, []);

  const handleTriggerReminders = () => {
    setTriggering(true);
    billingApi
      .triggerReminders()
      .then(() => toast.success("Invoice reminders queued"))
      .catch(() => toast.error("Failed to trigger reminders"))
      .finally(() => setTriggering(false));
  };

  const handleTriggerOverdue = () => {
    setTriggering(true);
    billingApi
      .triggerOverdueCheck()
      .then(() => toast.success("Overdue check queued"))
      .catch(() => toast.error("Failed to trigger overdue check"))
      .finally(() => setTriggering(false));
  };

  if (loading) return <LoadingSpinner />;
  if (!stats) return <EmptyState message="No billing data available" />;

  const collectionRate =
    stats.total_invoiced > 0
      ? ((stats.total_collected / stats.total_invoiced) * 100).toFixed(1)
      : "0.0";

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Invoiced"
          value={`N${fmt(stats.total_invoiced)}`}
          color="text-gray-900"
        />
        <KpiCard
          label="Total Collected"
          value={`N${fmt(stats.total_collected)}`}
          color="text-green-600"
        />
        <KpiCard
          label="Outstanding"
          value={`N${fmt(stats.outstanding)}`}
          color="text-amber-600"
        />
        <KpiCard
          label="Overdue"
          value={`N${fmt(stats.overdue)}`}
          color="text-red-600"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total Invoices" value={stats.invoice_count} />
        <StatCard label="Fully Paid" value={stats.paid_count} />
        <StatCard label="Overdue" value={stats.overdue_count} />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">
          Collection Rate
        </h3>
        <div className="mb-2 flex items-end justify-between">
          <span className="text-2xl font-bold text-brand-600 tabular-nums">
            {collectionRate}%
          </span>
          <span className="text-xs text-gray-500">
            {stats.paid_count} of {stats.invoice_count} invoices paid
          </span>
        </div>
        <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-brand-500 transition-all"
            style={{ width: `${Math.min(collectionRate, 100)}%` }}
          />
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5">
        <h3 className="mb-3 text-sm font-semibold text-gray-900">
          Manual Actions
        </h3>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleTriggerReminders}
            disabled={triggering}
            className="btn btn-secondary btn-sm"
          >
            {triggering ? "Queuing..." : "Send Invoice Reminders"}
          </button>
          <button
            onClick={handleTriggerOverdue}
            disabled={triggering}
            className="btn btn-secondary btn-sm"
          >
            {triggering ? "Queuing..." : "Check Overdue Invoices"}
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-400">
          Reminders run automatically daily at 8:30 AM. Overdue check runs at
          midnight.
        </p>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Shared small components                                            */
/* ------------------------------------------------------------------ */

function KpiCard({ label, value, color = "text-gray-900" }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>
        {value}
      </p>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 text-center">
      <p className="text-2xl font-bold text-gray-900 tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{label}</p>
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
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <p className="mt-2 text-sm text-gray-500">{message}</p>
    </div>
  );
}
