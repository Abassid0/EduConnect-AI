/**
 * Shown while a lazily-loaded route chunk is being fetched.
 *
 * Deliberately shaped like the page that replaces it — a heading block, a
 * toolbar row, then table rows — so the layout does not jump when the real
 * content arrives. A centred spinner would occupy ~128px and then be replaced
 * by 600px of table, shifting everything below it.
 */
export default function RouteFallback() {
  return (
    <div className="space-y-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading page</span>

      {/* Page heading */}
      <div className="space-y-2">
        <div className="h-7 w-48 rounded-md bg-gray-200" />
        <div className="h-4 w-72 rounded bg-gray-100" />
      </div>

      {/* Toolbar / filters */}
      <div className="flex flex-wrap gap-3">
        <div className="h-9 w-40 rounded-lg bg-gray-100" />
        <div className="h-9 w-32 rounded-lg bg-gray-100" />
        <div className="ml-auto h-9 w-28 rounded-lg bg-gray-100" />
      </div>

      <TableSkeleton />
    </div>
  );
}

/**
 * Table-shaped placeholder. `rows` should roughly match a typical page of
 * results so the reserved height is close to the final height.
 */
export function TableSkeleton({ rows = 8, cols = 6 }) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      {/* Header row — same padding as a real thead */}
      <div className="flex gap-4 border-b border-gray-200 bg-gray-50 px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-3 flex-1 rounded bg-gray-200" />
        ))}
      </div>

      {Array.from({ length: rows }).map((_, r) => (
        <div
          key={r}
          className="flex gap-4 border-b border-gray-100 px-4 py-4 last:border-b-0"
        >
          {Array.from({ length: cols }).map((_, c) => (
            <div
              key={c}
              className="h-4 flex-1 rounded bg-gray-100"
              // Vary width slightly so it reads as content, not a grid
              style={{ opacity: c === 0 ? 1 : 0.75 }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
