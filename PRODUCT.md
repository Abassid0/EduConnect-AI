# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Parents (WhatsApp users):** Nigerian parents interacting via WhatsApp to browse educational programmes, register children, make payments, manage notification preferences, and get support. They expect the entire journey to happen inside WhatsApp without downloading an app or visiting a website.

**Admin staff (Dashboard users):** A mix of dedicated support agents and school administrative staff (receptionists, coordinators) who handle parent conversations, manage tickets, oversee enrollments, and monitor analytics. They split time between WhatsApp support and other school duties.

**Roles:** super_admin, admin, support_agent, finance, academic — enforced via JWT + RBAC on every admin endpoint.

## Product Purpose

Edpassare is a WhatsApp-first customer engagement platform for an education company in Nigeria. It enables parents to discover programmes, register students, pay fees (via Paystack), receive class reminders, and get AI-powered support — all within a single WhatsApp conversation thread. The admin dashboard gives staff real-time visibility into conversations, tickets, payments, and analytics.

Success means: parents complete registration and payment without ever leaving WhatsApp; staff spend less time on repetitive queries because the AI assistant and structured flows handle them; the school has full audit and analytics visibility.

## Positioning

Three things a generic school management system or phone-based support cannot replicate:

1. **24/7 WhatsApp convenience** — parents interact where they already are, anytime, without visiting or calling.
2. **AI-powered instant answers** — Claude-backed assistant gives real-time answers about programmes, fees, and schedules without waiting for staff.
3. **End-to-end on WhatsApp** — discovery, registration, payment, reminders, and support in one thread. No app downloads, no website accounts.

## Operating Context

- Parents send messages to a WhatsApp Business number. Inbound webhooks hit a FastAPI server.
- A conversation engine routes messages through structured flows (main menu, registration, enquiry, payment, support, account, notifications, partnership) or to the AI assistant for natural-language queries.
- Paystack handles payment processing (NGN). Webhooks confirm payment status.
- Celery workers send scheduled reminders (class, payment) and process async tasks.
- Admin staff log into a React dashboard to view conversations, reply, manage tickets, assign agents, and review analytics.
- All timestamps use Africa/Lagos (WAT) timezone.

## Capabilities and Constraints

**Capabilities:**
- 7-option WhatsApp interactive menu (browse programmes, register, pay, account, notifications, support, partnership)
- Multi-step student registration flow with auto-generated registration IDs
- Paystack payment initiation with webhook-verified completion and PDF receipts
- AI assistant with tool-use (programme lookup, support departments) and confidence-based escalation
- Bot-to-human escalation with conversation assignment and internal notes
- Referral code system with commission tracking
- Notification preferences per parent (class reminders, payment reminders, marketing, events, progress reports)
- Scheduled reminders via Celery Beat (24h and 1h before class, 7-day/due/overdue payment)
- Analytics: conversation volume, response time, resolution rate, conversion funnel, referral leaderboard, AI performance

**Constraints:**
- WhatsApp Cloud API message templates require Meta approval before use in production
- All webhook endpoints require signature verification (HMAC SHA-256 for WhatsApp, SHA-512 for Paystack)
- Currency is NGN (Nigerian Naira) only
- Registration endpoint restricted to super_admin role
- Platform does not yet have a public-facing website — WhatsApp is the only parent-facing channel

## Brand Commitments

No established visual identity. The name is **Edpassare** (sometimes written Edpassāre). No logo, color palette, or brand guide exists yet — open to defining one.

## Evidence on Hand

- Full technical architecture document (Edpassare-Technical-Architecture.md)
- 59 passing integration tests covering webhooks, auth, RBAC, AI service, and reminders
- Deployment guide (DEPLOYMENT.md) with Railway, AWS ECS, and Docker Compose options
- WhatsApp template documentation (WHATSAPP_TEMPLATES.md) with 8 templates
- No real parent testimonials, case studies, or press coverage yet

## Product Principles

1. **WhatsApp-native, not WhatsApp-adjacent** — every parent interaction must feel natural inside WhatsApp, using its native UI elements (lists, buttons, templates), never forcing parents to a browser.
2. **AI assists, humans decide** — the AI handles routine queries and structured flows; it escalates to staff when confidence is low or the parent asks, never pretending to be human.
3. **Security by default** — every webhook is signature-verified, every admin endpoint is auth-gated, credentials never touch source control.
4. **Nigerian context first** — NGN currency, Africa/Lagos timezone, local payment infrastructure (Paystack), WhatsApp as the dominant messaging channel.
5. **Operational visibility** — staff should never be surprised by what's happening; analytics, audit logs, and correlation IDs make every interaction traceable.
