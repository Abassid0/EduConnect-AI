const COLORS = {
  active: "bg-green-100 text-green-700",
  paused_for_agent: "bg-amber-100 text-amber-700",
  closed: "bg-gray-100 text-gray-600",
  open: "bg-blue-100 text-blue-700",
  resolved: "bg-green-100 text-green-700",
  in_progress: "bg-amber-100 text-amber-700",
  pending: "bg-yellow-100 text-yellow-700",
  paid: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  sent: "bg-green-100 text-green-700",
  urgent: "bg-red-100 text-red-700",
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-gray-100 text-gray-600",
  unpaid: "bg-yellow-100 text-yellow-700",
  partial: "bg-amber-100 text-amber-700",
  overdue: "bg-red-100 text-red-700",
  cancelled: "bg-gray-100 text-gray-600",
};

const LABELS = {
  paused_for_agent: "Human Active",
  active: "Bot Active",
  in_progress: "In Progress",
};

export default function StatusBadge({ value, className = "" }) {
  const color = COLORS[value] || "bg-gray-100 text-gray-600";
  const label = LABELS[value] || value?.replace(/_/g, " ");
  return (
    <span
      className={`badge capitalize ${color} ${className}`}
    >
      {label}
    </span>
  );
}
