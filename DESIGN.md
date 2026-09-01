---
name: Edpassare Admin
description: WhatsApp-first school engagement dashboard for Nigerian education
colors:
  brand-50: "#f0f9ff"
  brand-100: "#e0f2fe"
  brand-500: "#0ea5e9"
  brand-600: "#0284c7"
  brand-700: "#0369a1"
  brand-800: "#075985"
  brand-900: "#0c4a6e"
  surface-main: "#f9fafb"
  surface-card: "#ffffff"
  surface-overlay: "rgba(0,0,0,0.3)"
  border-default: "#e5e7eb"
  border-subtle: "#f3f4f6"
  text-primary: "#111827"
  text-secondary: "#6b7280"
  text-tertiary: "#9ca3af"
  text-inverse: "#ffffff"
  status-success: "#16a34a"
  status-success-bg: "#dcfce7"
  status-warning: "#d97706"
  status-warning-bg: "#fef3c7"
  status-danger: "#dc2626"
  status-danger-bg: "#fef2f2"
  status-info: "#2563eb"
  status-info-bg: "#dbeafe"
  note-bg: "#fefce8"
  note-border: "#fde68a"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
  # Greeting voice for unauthenticated entry surfaces (the login screen).
  # A system serif, not a web font: these screens are the app's first paint
  # and must not wait on a font request. Not for use inside the dashboard,
  # which stays on the Inter steps above.
  display-accent:
    fontFamily: 'Georgia, "Times New Roman", serif'
    fontSize: "2.125rem"
    fontWeight: 600
    fontStyle: "italic"
    lineHeight: 1
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
    letterSpacing: "0.05em"
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  2xl: "32px"
  page: "16px"
  page-lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.brand-600}"
    textColor: "{colors.text-inverse}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.brand-700}"
  button-secondary:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.border-subtle}"
  button-danger:
    backgroundColor: "{colors.status-danger}"
    textColor: "{colors.text-inverse}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-danger-hover:
    backgroundColor: "#b91c1c"
  chip-active:
    backgroundColor: "{colors.brand-600}"
    textColor: "{colors.text-inverse}"
    rounded: "{rounded.full}"
    padding: "6px 12px"
  chip-inactive:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.full}"
    padding: "6px 12px"
  input-default:
    backgroundColor: "{colors.surface-card}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  card-default:
    backgroundColor: "{colors.surface-card}"
    rounded: "{rounded.lg}"
    padding: "16px"
  badge-success:
    backgroundColor: "{colors.status-success-bg}"
    textColor: "{colors.status-success}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  badge-warning:
    backgroundColor: "{colors.status-warning-bg}"
    textColor: "{colors.status-warning}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  badge-danger:
    backgroundColor: "{colors.status-danger-bg}"
    textColor: "{colors.status-danger}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
  badge-info:
    backgroundColor: "{colors.status-info-bg}"
    textColor: "{colors.status-info}"
    rounded: "{rounded.full}"
    padding: "2px 10px"
---

# Design System: Edpassare Admin

## Overview

**Creative North Star: "The WhatsApp Control Room"**

A purpose-built messaging operations center that combines the familiar comfort of a chat interface with the precision and clarity of a control panel. The dashboard is an extension of WhatsApp itself — the same conversations, the same parents, the same urgency — but elevated into a workspace where school staff have full operational visibility and control. Every pixel serves the operator: status is visible at a glance, conversations are one click away, and the system communicates its state without requiring interpretation.

The visual personality is bold and energetic with digital teal-blue as its signature, but disciplined in where that energy lives. Color is concentrated in status signals and primary actions; the surrounding workspace stays neutral and precise so the content — conversations, tickets, numbers — commands attention. The system borrows the rounded, card-based language of modern messaging apps but applies it with the rigor of an operations tool.

Interaction is tactile and responsive. Surfaces lift on hover, buttons acknowledge clicks, and state changes are animated. At rest, the interface is clean and flat; on interaction, it comes alive with subtle elevation and confident color shifts.

**Key Characteristics:**
- Messaging-native: card-based conversation list, chat-bubble message view, WhatsApp-style delivery indicators
- Status-driven: semantic color coding for every state (active/paused/open/closed/paid/failed) immediately visible
- Operationally flat: minimal decoration, maximum information density, no visual noise between the operator and their work
- Bold brand accent: digital teal-blue concentrated on primary actions and active states, never diluted across passive surfaces
- Responsive shell: sidebar collapses to overlay on mobile, tables scroll horizontally, chat view adapts to available width

## Colors

A digital teal-blue palette anchors the brand, supported by Tailwind's gray scale for neutrals and a semantic status palette that maps directly to conversation and ticket states.

### Primary
- **Digital Teal-Blue 600** (#0284c7): The primary action color. Buttons, active nav items, brand mark, chat bubbles from the bot. The signature of the system — tech-forward and precise.
- **Digital Teal-Blue 500** (#0ea5e9): Focus rings, progress bars, volume chart fills. The lighter working shade that supports the primary without competing.
- **Digital Teal-Blue 700** (#0369a1): Hover state for primary buttons and active nav text. Darkens on press to confirm interaction.

### Neutral
- **Surface Main** (#f9fafb / gray-50): The page background. Recedes behind card surfaces.
- **Surface Card** (#ffffff): Every card, container, sidebar, and input field surface.
- **Border Default** (#e5e7eb / gray-200): All structural borders — sidebar edges, card outlines, table dividers, input strokes.
- **Text Primary** (#111827 / gray-900): All headings, names, and primary content.
- **Text Secondary** (#6b7280 / gray-500): Supporting text, labels, metadata, timestamps.
- **Text Tertiary** (#9ca3af / gray-400): Placeholder text, disabled states, empty state messages.

### Status
- **Success** (#16a34a on #dcfce7): Active conversations, paid payments, sent notifications, bot active indicator.
- **Warning** (#d97706 on #fef3c7): Paused-for-agent, in-progress tickets, medium priority, pending states.
- **Danger** (#dc2626 on #fef2f2): Failed payments, high/urgent priority, error alerts, close/delete actions.
- **Info** (#2563eb on #dbeafe): Open tickets, read receipts, informational badges.

### Named Rules

**The Status Palette Rule.** Every operational state maps to exactly one color pair (text + background). No state exists without a color assignment in the StatusBadge component. New states get a color before they get a label.

**The Brand Concentration Rule.** Digital Teal-Blue appears only on interactive elements (buttons, active tabs, focus rings, links) and the brand mark. It never fills passive containers, backgrounds, or decorative surfaces. Its scarcity is what makes it signal "this is actionable."

## Typography

**Body Font:** Inter (with system-ui, -apple-system fallback)
**Mono Font:** ui-monospace, SFMono-Regular, Menlo

**Character:** Inter provides the clean, geometric precision the control room needs. No display font — the dashboard is a tool, not a marketing surface. The monospace face handles ticket numbers, payment references, and registration IDs where character-width consistency aids scanning.

### Hierarchy
- **Display** (700, 1.5rem/24px, 1.2 line-height): Page titles only. Analytics headline values use 2xl (1.5rem) bold.
- **Title** (600, 1.125rem/18px, 1.4 line-height): Section headings within pages ("Conversion Funnel," "Referral Leaderboard").
- **Body** (400, 0.875rem/14px, 1.5 line-height): All primary content — message text, conversation previews, form labels, table cells.
- **Label** (500, 0.75rem/12px, 0.05em tracking, uppercase): Table column headers, KPI labels, section sub-headers. Always uppercase with wide tracking.
- **Mono** (400, 0.75rem/12px): Ticket numbers, payment references, registration IDs, timestamps in technical contexts.

### Named Rules

**The 14px Floor Rule.** Body text is never smaller than 14px (0.875rem). Labels and metadata go to 12px. Nothing in the interface goes below 12px except the date labels on the volume chart (8px), which are rotated and supplementary.

## Layout

The dashboard uses a sidebar-plus-main shell with a `lg` (1024px) breakpoint as the primary responsive threshold.

**Sidebar:** Fixed 240px (`w-60`) left rail. Contains the brand mark, three-item navigation (Inbox, Tickets, Analytics), and user profile with sign-out. Collapses off-screen on mobile with a backdrop overlay (`bg-black/30`) and hamburger trigger in a 56px mobile header.

**Main area:** Flex-1, scrollable, with `bg-gray-50` surface. Pages use `p-4` on mobile, `p-6` on desktop (`lg:p-6`).

**Content containers:** Cards and tables are full-width within the page padding. No max-width constraint on content areas except the chat view, which caps at `max-w-2xl` (672px) for comfortable reading.

**Grid:** Analytics KPI cards use a responsive `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` layout. AI stats use `grid-cols-2 sm:grid-cols-4`.

**Spacing rhythm:** The spacing scale follows Tailwind's 4px base: 4/8/12/16/24/32. The dominant gap between sections is 24px (`space-y-6`). Within sections, items use 8-12px gaps.

**Conversation view:** Three-panel layout — sidebar (hidden on mobile), main chat area (flex-1), right profile sidebar (`w-80`, hidden on mobile with toggle). Chat messages capped at 75% width within a centered `max-w-2xl` container.

## Elevation & Depth

The system uses a hybrid approach: flat at rest with elevation on interaction and layered containers for dropdowns and overlays.

### Shadow Vocabulary
- **Shadow Ambient** (`shadow-sm` / `0 1px 2px rgba(0,0,0,0.05)`): Login form card, date separator pills, message bubbles. A subtle grounding shadow that adds depth without visual weight.
- **Shadow Dropdown** (`shadow-lg` / `0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)`): Agent assignment dropdown, mobile sidebar overlay. Clear elevation for overlapping UI.
- **Shadow Profile** (`shadow-xl`): Mobile profile sidebar when it slides in from the right.

### Named Rules

**The Lift-on-Hover Rule.** Cards and interactive containers are flat at rest (border only, no shadow). On hover, they gain a subtle border color shift (`hover:border-brand-300`) and optional background tint (`hover:bg-brand-50/30`). Shadows emerge only for truly elevated surfaces (dropdowns, overlays, mobile slide-ins).

## Shapes

**Primary radius:** `rounded-lg` (8px) is the workhorse — buttons, inputs, nav items, sidebar brand mark, student cards, internal note containers.

**Container radius:** `rounded-xl` (12px) for page-level containers — card wrappers, table containers, empty states, login form.

**Message bubbles:** `rounded-2xl` (16px) for chat message bubbles, following WhatsApp's generous bubble radius.

**Full radius:** `rounded-full` (9999px) for badges, filter chips, avatar circles, loading spinners, and the volume chart bars' top corners.

**Border treatment:** 1px solid `border-gray-200` is the universal container boundary. No colored borders except for active tab underlines (`border-brand-600`, 2px bottom) and the status dot on the bot toggle (which uses background color, not border).

### Named Rules

**The No Double-Border Rule.** Adjacent containers sharing an edge (e.g., table rows, sidebar sections) use `divide-y` or a single shared border. Two borders touching creates a 2px visual seam that looks accidental.

## Components

### Buttons
- **Shape:** Gently curved (8px radius, `rounded-lg`)
- **Primary:** Digital Teal-Blue 600 fill, white text, 8px 16px padding. Hover darkens to 700. Focus ring: 2px offset brand-500.
- **Secondary:** White fill, gray-700 text, 1px gray-300 border. Hover lightens to gray-50.
- **Danger:** Red-600 fill, white text. Hover darkens to red-700. Used for "Close" conversation action.
- **Small variant** (`btn-sm`): 6px 12px padding, 12px text. Applied to filter chips, inline actions.
- **States:** All buttons disable to 50% opacity with `cursor-not-allowed`. Loading states replace label text ("Signing in...", "...").

### Chips / Filter Pills
- **Style:** Full-radius pills (`rounded-full`). Active: brand-600 fill, white text. Inactive: white fill, gray-600 text, gray-300 border.
- **Usage:** Inbox filter tabs (All, Needs Agent, Active, My Conversations), Analytics time range (7d, 30d, 90d).
- **No multi-select:** One active chip per group.

### Cards / Containers
- **Corner style:** Generous curve (12px, `rounded-xl`)
- **Background:** White (`bg-white`)
- **Shadow strategy:** No shadow at rest. Border-only containment (`border border-gray-200`).
- **Hover (interactive cards):** Border shifts to `border-brand-300`, subtle background tint `bg-brand-50/30`.
- **Internal padding:** 16px default, 24px on desktop for analytics containers (`p-4 lg:p-6`).

### Inputs / Fields
- **Style:** White fill, 1px gray-300 border, 8px radius, 12px horizontal / 8px vertical padding.
- **Focus:** Border shifts to brand-500, 1px brand-500 ring. Subtle but clear.
- **Placeholder:** Gray-400. Never used as a label substitute.
- **Select dropdowns:** Same `.input` base with `w-auto` for inline filter use.

### Status Badges
- **Style:** Full-radius pill (`rounded-full`), 10px horizontal / 2px vertical padding, 12px font, medium weight.
- **Semantic mapping:** Every value in the system has exactly one color pairing (see StatusBadge component). Labels auto-capitalize with `_` replaced by spaces; three states have custom labels (paused_for_agent → "Human Active", active → "Bot Active", in_progress → "In Progress").

### Navigation
- **Sidebar nav items:** 8px radius, 12px horizontal / 8px vertical padding, 14px font, medium weight. Active: brand-50 background, brand-700 text. Inactive: gray-600 text, hover gray-100 background.
- **Tab underlines (CustomerProfile):** 2px bottom border, brand-600 when active, transparent when inactive. 12px font, no background change.

### Chat Bubbles (Signature Component)
- **Shape:** Generous curve (16px, `rounded-2xl`)
- **Inbound:** White background, gray-900 text. Left-aligned.
- **Outbound (Bot):** Brand-600 fill, white text. Right-aligned.
- **Outbound (Agent):** Blue-600 fill, white text. Right-aligned. Prefixed with "Agent reply" label at 70% opacity.
- **Metadata:** Timestamp in 10px at 60% opacity (white for outbound, gray-400 for inbound). Delivery icons (single check / double check / blue double check) inline.
- **Date separators:** Centered pill with white background, shadow-sm, rounded-full, 12px gray-500 text.

### Internal Notes
- **Style:** Yellow-50 background, yellow-200 border, 8px radius. Visually distinct from all other containers — the only warm-toned surface in the system.
- **Collapsible:** Section header toggles visibility with a rotating chevron.

### KPI Cards
- **Style:** Same as card-default (white, rounded-xl, border). No shadow, no accent color.
- **Content:** Label in uppercase 12px tracking-wider gray-500, value in 24px bold gray-900, optional sub-text in 12px gray-400.

### Loading Spinner
- **Style:** 24px circle, 2px border brand-600, top border transparent, CSS `animate-spin`. Centered within the loading area.

## Do's and Don'ts

### Do:
- **Do** use the StatusBadge component for every operational state. Never apply status colors manually with inline Tailwind classes.
- **Do** use `.input` and `.btn-*` component classes from `index.css`. These are the single source of truth for form element styling.
- **Do** use `font-mono text-xs` for any machine-generated identifier (ticket numbers, payment references, registration IDs).
- **Do** use the `timeAgo()` pattern for conversation timestamps (Just now / 5m ago / 3h ago / 2d ago). Full dates only in detail views.
- **Do** provide empty states with centered gray-400 italic text inside the same card container that would hold the data.
- **Do** use `rounded-xl` for page-level containers and `rounded-lg` for interactive elements within them.
- **Do** use the `lg:` breakpoint (1024px) as the primary responsive threshold. Sidebar, padding, and layout changes happen here.

### Don't:
- **Don't** apply brand-600 to non-interactive surfaces. If it's not clickable or focusable, it doesn't get the brand color.
- **Don't** use shadows on cards at rest. Elevation is reserved for overlapping surfaces (dropdowns, mobile slide-ins) and hover states.
- **Don't** mix badge styles — every status value maps to exactly one StatusBadge color. Adding a new status means adding it to the COLORS map.
- **Don't** create new button variants without adding them to the `.btn-*` family in `index.css`.
- **Don't** use gray-300 text. The lightest readable text is gray-400 (`text-tertiary`); anything lighter fails contrast.
- **Don't** place content in a scrollable container without visible overflow indicators. Use `overflow-x-auto` on tables.
