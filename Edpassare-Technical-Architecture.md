# Edpassare WhatsApp Platform - Technical Architecture

## Overview

Edpassare WhatsApp Platform is a WhatsApp-first customer engagement system for an education company in Nigeria. Parents interact via WhatsApp to browse programmes, register students, make payments (Paystack), manage notifications, and get support. An admin dashboard (React) gives staff real-time visibility into conversations, tickets, and analytics.

**Stack:** Python 3.12 | FastAPI (async) | PostgreSQL 16 | Redis 7 | Celery | WhatsApp Cloud API | Anthropic Claude (AI Assistant) | React 18 + Vite + Tailwind CSS 3

---

## System Architecture

```
                         WhatsApp Cloud API
                               |
                          (webhook POST)
                               |
                    +----------v-----------+
                    |    FastAPI (uvicorn)  |
                    |    port 8000         |
                    |                      |
                    |  /api/v1/whatsapp    |--- signature verification
                    |  /api/v1/auth       |--- JWT (python-jose HS256)
                    |  /api/v1/admin      |--- RBAC
                    |  /api/v1/students   |
                    |  /api/v1/programmes |
                    |  /api/v1/payments   |--- Paystack webhooks
                    |  /api/v1/notifs     |
                    |  /api/v1/support    |
                    |  /api/v1/analytics  |
                    |  /api/v1/engagement |
                    +---+------+------+---+
                        |      |      |
            +-----------+      |      +-----------+
            |                  |                  |
    +-------v-------+  +------v------+   +-------v-------+
    | PostgreSQL 16 |  |  Redis 7    |   | Celery Workers|
    | (asyncpg)     |  |  (broker +  |   | + Beat        |
    | 16 models     |  |   backend)  |   | (reminders,   |
    | 7 migrations  |  |             |   |  webhooks)    |
    +---------------+  +-------------+   +---------------+

    +-------------------------------------------------------+
    |              Admin Dashboard (React 18)                |
    |  Vite + Tailwind CSS 3 | port 3000                    |
    |  Login | Inbox | ConversationView | Tickets | Analytics|
    +-------------------------------------------------------+
```

---

## Project Structure

```
Edpassare WhatsApp Platform/
|-- app/
|   |-- main.py                    # FastAPI app, CORS, middleware
|   |-- config.py                  # pydantic-settings (env-based)
|   |-- database.py                # SQLAlchemy 2.0 async engine + session
|   |-- models/                    # 15 SQLAlchemy models (mapped_column)
|   |   |-- conversation.py        # Conversation state machine
|   |   |-- message.py             # WhatsApp message log
|   |   |-- parent.py              # Parent (identified by whatsapp_number)
|   |   |-- student.py             # Student with registration_id
|   |   |-- programme.py           # Education programmes with fees
|   |   |-- class_schedule.py      # Per-programme class schedules
|   |   |-- enrollment.py          # Student-programme enrollment
|   |   |-- payment.py             # Paystack payment records
|   |   |-- notification.py        # Notification + NotificationPreference
|   |   |-- admin_user.py          # Staff accounts (bcrypt hashed)
|   |   |-- support_ticket.py      # SupportTicket + InternalNote
|   |   |-- referral.py            # Referral codes + commission tracking
|   |   |-- ai_interaction.py       # AI interaction log
|   |   |-- analytics_event.py     # Analytics events (WAT timezone)
|   |-- api/
|   |   |-- deps.py                # Shared dependency injection
|   |   |-- v1/
|   |       |-- whatsapp.py        # Webhook verify + inbound handler
|   |       |-- auth.py            # Login, refresh, register staff
|   |       |-- admin.py           # Conversation management, tickets, agents
|   |       |-- students.py        # Student CRUD + lookup by whatsapp
|   |       |-- programmes.py      # Programme + schedule listing
|   |       |-- payments.py        # Payment init + Paystack webhook
|   |       |-- notifications.py   # Notification CRUD
|   |       |-- support.py         # Ticket + notes endpoints
|   |       |-- analytics.py       # Volume, funnel, resolution, referrals
|   |       |-- engagement.py      # Attendance, progress, certificate notifs
|   |-- services/
|   |   |-- whatsapp_service.py    # WhatsApp Cloud API client (httpx)
|   |   |-- conversation_engine.py # Message router + flow orchestration
|   |   |-- registration_service.py# Parent/student creation + enrollment
|   |   |-- programme_service.py   # Programme queries
|   |   |-- payment_service.py     # Paystack payment lifecycle
|   |   |-- notification_service.py# Notification dispatch
|   |   |-- support_service.py     # Ticket CRUD
|   |   |-- escalation_service.py  # Bot-to-human escalation + resume
|   |   |-- referral_service.py    # Code generation + commission tracking
|   |   |-- analytics_service.py   # Event tracking + aggregations (WAT)
|   |   |-- ai_service.py          # Claude AI assistant with tool_use
|   |-- flows/
|   |   |-- __init__.py            # FlowResult dataclass
|   |   |-- main_menu.py           # 7-option WhatsApp interactive list
|   |   |-- registration_flow.py   # Multi-step student registration
|   |   |-- enquiry_flow.py        # Programme browsing flow
|   |   |-- payment_flow.py        # Payment initiation flow
|   |   |-- my_account_flow.py     # Account/enrollment lookup
|   |   |-- notification_prefs_flow.py # Preference toggle flow
|   |   |-- support_flow.py        # Support request + escalation
|   |   |-- partnership_flow.py    # School partnership lead capture
|   |-- tasks/
|   |   |-- celery_app.py          # Celery config + beat schedule
|   |   |-- webhook_tasks.py       # Async webhook processing
|   |   |-- reminder_tasks.py      # Class + payment reminders
|   |   |-- notification_tasks.py  # Notification delivery tasks
|   |   |-- payment_tasks.py       # Payment status polling
|   |-- middleware/
|   |   |-- rate_limit.py          # slowapi rate limiting
|   |   |-- audit_log.py           # Request audit logging
|   |-- utils/
|       |-- whatsapp_helpers.py    # Payload builders (text, buttons, list, template)
|       |-- signature_verify.py    # X-Hub-Signature-256 HMAC verification
|       |-- auth.py                # JWT auth dependencies + RBAC
|       |-- id_generator.py        # Registration ID generator
|       |-- rate_limiter.py        # Rate limit config
|       |-- receipt_generator.py   # PDF receipt (WeasyPrint)
|       |-- receipt.py             # Receipt template
|-- admin-dashboard/
|   |-- src/
|       |-- main.jsx               # React entry point
|       |-- App.jsx                # Route definitions
|       |-- api/client.js          # Axios + JWT interceptor
|       |-- context/AuthContext.jsx # Auth state + token storage
|       |-- components/
|       |   |-- Layout.jsx         # Sidebar + responsive shell
|       |   |-- ProtectedRoute.jsx # Auth guard
|       |   |-- StatusBadge.jsx    # Status pill component
|       |   |-- BotStatusToggle.jsx# Pause/resume bot toggle
|       |   |-- AssignDropdown.jsx # Agent assignment dropdown
|       |   |-- InternalNotes.jsx  # Ticket notes panel
|       |   |-- CustomerProfile.jsx# Parent/student info sidebar
|       |-- pages/
|           |-- Login.jsx          # Email/password login
|           |-- Inbox.jsx          # Conversation list with search
|           |-- ConversationView.jsx # Chat bubbles + agent tools
|           |-- Tickets.jsx        # Ticket list with filters
|           |-- Analytics.jsx      # KPIs, funnel, volume, leaderboard
|-- alembic/
|   |-- env.py                     # Migration environment
|   |-- versions/
|       |-- 001_initial_conversations_and_messages.py
|       |-- 002_phase2_parents_students_programmes.py
|       |-- 003_phase3_payments_billing.py
|       |-- 004_phase4_notifications_preferences.py
|       |-- 005_phase5_support_admin.py
|       |-- 006_phase6_referrals_analytics.py
|       |-- 007_phase6b_ai_interactions.py
|-- docker-compose.yml             # 5 services (api, worker, beat, db, redis)
|-- Dockerfile                     # Python 3.12-slim
|-- requirements.txt               # 16 production dependencies
|-- scripts/                       # Utility scripts
|-- tests/                         # Test suite
```

---

## Database Schema (16 Models, 17 Tables)

### Core Messaging

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `conversations` | id (UUID PK), whatsapp_id, current_flow, current_step, flow_data (JSONB), status, assigned_agent_id, last_message_at | Tracks conversation state machine per WhatsApp user |
| `messages` | id (UUID PK), conversation_id (FK), whatsapp_msg_id, direction (inbound/outbound), msg_type, content (JSONB), delivery_status | Full message log with delivery tracking |

### Registration & Education

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `parents` | id (UUID PK), whatsapp_number (unique), full_name, email, consent_given | Parent identity, shared key for cross-platform sync |
| `students` | id (UUID PK), parent_id (FK), registration_id (unique), full_name, date_of_birth, age, gender | Student records with auto-generated registration IDs |
| `programmes` | id (UUID PK), name, description, age_range_min/max, fee (Numeric 12,2), currency (NGN), available_slots, is_active | Education programme catalogue |
| `class_schedules` | id (UUID PK), programme_id (FK), day_of_week, start_time, end_time, timezone (Africa/Lagos) | Per-programme class schedules |
| `enrollments` | id (UUID PK), student_id (FK), programme_id (FK), schedule_id (FK), status (pending/active/completed) | Student-programme enrollment link |

### Payments

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `payments` | id (UUID PK), reference (unique), student_id (FK), enrollment_id (FK), programme_id (FK), amount (Numeric 12,2), currency (NGN), status, paystack_reference, paystack_authorization_url, paid_at | Paystack payment lifecycle |

### Notifications

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `notification_preferences` | id (UUID PK), parent_id (FK unique), class_reminders, payment_reminders, marketing, events, progress_reports | Per-parent notification toggles |
| `notifications` | id (UUID PK), recipient_whatsapp, notification_type, template_name, message_body, channel, status, scheduled_at, sent_at, retry_count | Notification queue with scheduling and retries |

### Support & Admin

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `admin_users` | id (UUID PK), email (unique), full_name, hashed_password, role, department, is_active | Staff accounts with role-based access |
| `support_tickets` | id (UUID PK), ticket_number (unique), conversation_id (FK), parent_id (FK), assigned_to (FK), department, priority, status, subject, escalation_reason | Support ticket management |
| `internal_notes` | id (UUID PK), ticket_id (FK), conversation_id (FK), author_id (FK), content | Private notes on tickets |

### Analytics & Referrals

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `referrals` | id (UUID PK), code (unique, "EDP-XXXXXX"), referrer_type (agent/parent/partner), total_registrations, total_revenue, commission_rate, commission_earned, commission_status | Referral code tracking with commission calculation |
| `analytics_events` | id (UUID PK), event_type, whatsapp_number, parent_id, student_id, conversation_id, referral_code, properties (JSONB), created_at (WAT) | Event sourcing for all analytics |
| `ai_interactions` | id (UUID PK), conversation_id (FK), parent_id (FK), user_query, tools_called (JSONB), ai_response, confidence_score, escalated, response_time_ms, created_at | AI assistant interaction log for analytics and review |

### Key Relationships

```
Parent (1) ----< (N) Student (1) ----< (N) Enrollment >---- (1) Programme
                                    |                              |
                                    v                              v
                                Payment                     ClassSchedule

Conversation (1) ----< (N) Message
     |
     v
SupportTicket (1) ----< (N) InternalNote
     |
     v
AdminUser (assigned_to)
```

---

## Conversation Engine

The conversation engine (`app/services/conversation_engine.py`) is the core message router. It implements a state machine using `current_flow` + `current_step` on the Conversation model.

### Flow Architecture

Each flow is a Python module exporting a `handle_step(step, user_input, flow_data, conversation, db)` function that returns a `FlowResult`:

```python
@dataclass
class FlowResult:
    next_step: str | None = None
    next_flow: str | None = None
    flow_data: dict = field(default_factory=dict)
    replies: list[dict] = field(default_factory=list)
    flow_complete: bool = False
```

### Message Processing Pipeline

```
Inbound WhatsApp Message
    |
    v
process_inbound_message()
    |
    +-- get_or_create_conversation()  --> track "conversation_start" event
    +-- log_message() (inbound)
    |
    +-- "menu" keyword? --> reset flow, show main menu
    +-- status == "paused_for_agent"? --> log only, bot stays silent
    +-- has active flow? --> route to flow handler
    |       |
    |       +-- "main_menu" --> handle_menu_selection()
    |       +-- other flow --> flow_handler.handle_step()
    |                               |
    |                               v
    |                       FlowResult
    |                           +-- replies --> send via WhatsApp API
    |                           +-- flow_complete --> clear state
    |                           +-- next_flow --> transition
    |
    +-- no active flow:
    |       +-- natural language query? --> AI assistant (Claude)
    |       |       +-- confidence >= 0.4 --> send AI response
    |       |       +-- confidence < 0.4 --> escalate to human
    |       +-- not NL query --> greeting + main menu
```

### Available Flows

| Flow | Menu Option | Steps | Purpose |
|------|-------------|-------|---------|
| `main_menu` | (entry point) | show | 7-option WhatsApp interactive list |
| `registration` | Register a Student | start, ask_referral, enter_referral, parent_name, child_name, dob, gender, programme, schedule, emergency, consent, summary | Multi-step student registration with referral code capture |
| `enquiry` | Browse Programmes | start, category, details | Programme browsing with age-filtered results |
| `payment` | Make Payment | start, select_student, select_enrollment, confirm | Payment initiation via Paystack |
| `my_account` | My Account | start, details | Account and enrollment lookup |
| `notification_prefs` | Notification Settings | start, toggle | Preference management |
| `support` | Get Help | start, describe, confirm | Support request with auto-escalation |
| `partnership` | School Partnership | start, school_name, contact_name, contact_role, contact_email, student_count, interest_area, confirm | School partnership lead capture |

---

## Authentication & Authorization

### JWT Token Flow

- **Algorithm:** HS256 (python-jose)
- **Access Token:** 60-minute expiry
- **Refresh Token:** 7-day expiry
- **Password Hashing:** bcrypt

### Admin Roles

| Role | Access |
|------|--------|
| `super_admin` | Full system access |
| `admin` | User management, all features |
| `support_agent` | Conversations, tickets |
| `finance` | Payments, financial reports |
| `academic` | Programmes, students, enrollments |

### RBAC Implementation

```python
# Dependency injection with role check
@router.get("/admin/users")
async def list_users(
    user: AdminUser = Depends(require_role("super_admin", "admin"))
):
```

---

## Payment Integration (Paystack)

### Payment Flow

```
Parent selects "Make Payment" on WhatsApp
    |
    v
Select student --> Select enrollment --> Confirm
    |
    v
Create Payment record (status: pending)
    |
    v
Initialize Paystack transaction --> Get authorization_url
    |
    v
Send payment link to parent via WhatsApp
    |
    v
Parent pays on Paystack checkout page
    |
    v
Paystack sends webhook (charge.success)
    |
    v
/api/v1/payments/webhook --> verify signature
    |
    v
Mark payment as "paid" + enrollment as "active"
    |
    v
Track "payment_complete" analytics event
    |
    v
Send payment confirmation + PDF receipt via WhatsApp
```

### Payment Model

- **Currency:** NGN (Nigerian Naira)
- **Amount precision:** Numeric(12, 2)
- **Statuses:** pending, paid, failed, refunded
- **Receipt generation:** WeasyPrint PDF, optionally stored in AWS S3

---

## Support & Escalation System

### Escalation Triggers

| Trigger | Department | Priority | Description |
|---------|-----------|----------|-------------|
| `human_request` | general | medium | Parent explicitly requests human agent |
| `payment_dispute` | payments | high | Payment-related complaint |
| `refund_request` | payments | high | Refund request |
| `technical_issue` | technical | medium | Technical problem |
| `low_confidence` | general | low | AI confidence below threshold |
| `manual_approval` | admissions | medium | Registration requiring manual review |

### Bot-Agent Handoff

```
Escalation triggered
    |
    v
Conversation.status = "paused_for_agent"
    |
    v
SupportTicket created (auto-assigned by department)
    |
    v
Bot stops responding (messages logged but no auto-reply)
    |
    v
Agent handles via Admin Dashboard (send messages, add notes)
    |
    v
Agent clicks "Resume Bot" or closes ticket
    |
    v
Conversation.status = "active" --> bot resumes
```

---

## Analytics & Tracking

### Event Types

| Event | Triggered When | Key Properties |
|-------|---------------|----------------|
| `conversation_start` | New conversation created | whatsapp_number, conversation_id |
| `registration_start` | Registration flow begins | whatsapp_number |
| `registration_complete` | Registration confirmed | parent_id, student_id, programme_id |
| `payment_init` | Payment link generated | amount, reference, programme_name |
| `payment_complete` | Paystack webhook confirms payment | amount, reference |
| `support_escalation` | Conversation escalated to human | reason, department, ticket_number |
| `referral_used` | Referral code applied during registration | referral_code |
| `partnership_lead` | School partnership form completed | school_name, contact_name |
| `agent_response` | Agent sends reply | response_time_seconds |

### Conversion Funnel

```
conversation_start --> registration_start --> registration_complete --> payment_init --> payment_complete
```

### Analytics Endpoints

| Endpoint | Response |
|----------|----------|
| `GET /analytics/volume?days=30&period=daily` | Daily/weekly/monthly conversation counts |
| `GET /analytics/funnel?days=30` | 5-stage conversion funnel with drop-off percentages |
| `GET /analytics/resolution-rate?days=30` | Bot resolution rate (conversations minus escalations) |
| `GET /analytics/response-time?days=30` | Average agent response time in seconds |
| `GET /analytics/referrals?days=90` | Referral code performance (registrations, payments) |
| `GET /analytics/referrals/leaderboard?limit=10` | Top referral codes by registrations + revenue |

### Timezone

All analytics timestamps use **WAT (West Africa Time, UTC+1)** via `timezone(timedelta(hours=1))`.

---

## Referral System

### Code Format

Referral codes follow the pattern `EDP-XXXXXX` (6 uppercase alphanumeric characters).

### Referrer Types

| Type | Description |
|------|-------------|
| `agent` | Internal staff referral (linked to admin_users) |
| `parent` | Existing parent refers another parent |
| `partner` | School/institution partnership |

### Commission Tracking

Each referral tracks: `total_registrations`, `total_revenue`, `commission_rate`, `commission_earned`, and `commission_status` (unpaid/pending/paid).

### Integration Points

- **Registration flow:** Asks "Do you have a referral code?" after start, validates code, applies to registration
- **Payment webhook:** Records revenue against the referral that originated the registration
- **Partnership flow:** Creates a `partner` type referral with school metadata

---

## Notification System

### Scheduled Tasks (Celery Beat)

| Task | Schedule | Description |
|------|----------|-------------|
| `send_class_reminders_24h` | Daily at 07:00 WAT | Class reminders 24 hours before |
| `send_class_reminders_1h` | Every 10 minutes | Class reminders 1 hour before |
| `send_payment_reminders` | Daily at 09:00 WAT | Unpaid enrollment reminders |

### Notification Preferences

Parents can toggle per-category: `class_reminders`, `payment_reminders`, `marketing`, `events`, `progress_reports`.

### Engagement Endpoints (for Learning Service integration)

| Endpoint | Purpose |
|----------|---------|
| `POST /engagement/attendance` | Send attendance update to parent via WhatsApp |
| `POST /engagement/progress/notify` | Send assignment/grade/milestone notification |
| `POST /engagement/certificate/notify` | Send programme completion notification |

---

## AI Conversational Assistant

### Overview

The AI assistant uses Claude (claude-sonnet-4-6) with tool_use (function calling) to handle natural language queries from parents on WhatsApp. It sits in the fallback chain: **menu selection -> active flow handler -> AI assistant -> human escalation**.

### Architecture

```
Parent sends free-text message
    |
    v
Conversation Engine: no active flow + natural language detected
    |
    v
AI Service (app/services/ai_service.py)
    |
    +-- Rate limit check (10 calls / 5 min per conversation)
    +-- Claude API call with system prompt + 7 tools
    |       |
    |       +-- Claude decides which tools to call
    |       +-- Tools execute against database (controlled functions)
    |       +-- Results returned to Claude for response generation
    |       +-- Loop continues if Claude needs more tool calls
    |
    +-- Confidence scoring (0.0 - 1.0)
    |       +-- >= 0.4: send AI response to parent
    |       +-- < 0.4: escalate to human (Phase 5 escalation service)
    |
    +-- Log interaction to ai_interactions table
    +-- Track "ai_query" analytics event
```

### Controlled Backend Functions (Tools)

The AI can ONLY call these 7 functions — no direct database access:

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_programmes` | age (optional), level (optional) | Matching programmes with name, fee, schedule, slots |
| `get_programme_details` | programme_id | Full programme info with schedules |
| `get_payment_status` | parent_phone | List of pending/completed payments |
| `get_student_info` | parent_phone | Parent's children with enrolment status |
| `create_registration_intent` | parent_phone, child_name, programme_id | Confirmation prompt, redirects to registration flow |
| `get_class_schedule` | student_id | Upcoming classes with day/time |
| `get_support_departments` | (none) | List of departments for routing |

### Intent Detection

The conversation engine detects natural language queries using keyword matching and message structure analysis. Indicators include question marks, phrases like "how much", "when is", "I want to", and messages with 3+ words.

### Guardrails

- **System prompt** enforces data-only responses, no fabrication
- **Rate limiting**: 10 AI calls per 5-minute window per conversation
- **Confidence scoring**: heuristic based on tool usage, error presence, uncertainty phrases
- **Escalation**: automatic at confidence < 0.4 or when AI suggests connecting to staff
- **No internal data exposure**: IDs, errors, and system details are never shown to parents
- **API errors**: graceful fallback message, no escalation (allows retry)

### AI Analytics

| Endpoint | Response |
|----------|----------|
| `GET /analytics/ai?days=30` | Total queries, resolved, escalated, resolution rate, avg confidence, avg response time |
| `GET /analytics/ai/top-queries?days=30&limit=10` | Most common queries with count, avg confidence, escalation count |

---

## Admin Dashboard (React)

### Tech Stack

- React 18 with React Router 6
- Vite (build tool)
- Tailwind CSS 3
- Axios with JWT interceptor (auto refresh on 401)

### Pages

| Page | Route | Features |
|------|-------|----------|
| Login | `/login` | Email/password auth |
| Inbox | `/inbox` | Conversation list, search, status filters, real-time polling |
| Conversation View | `/conversations/:id` | WhatsApp-style chat bubbles, message input, template toggle, bot pause/resume, agent assignment, customer profile sidebar, internal notes |
| Tickets | `/tickets` | Ticket list with status/department/priority filters, stats badges |
| Analytics | `/analytics` | KPI cards (conversations, bot resolution %, escalations, avg response time), conversion funnel visualization, daily volume bar chart, referral leaderboard table, period selector (7d/30d/90d) |

### Auth Flow

```
Login --> JWT access + refresh tokens stored in localStorage
    |
    v
ProtectedRoute wraps Layout (redirects to /login if no token)
    |
    v
Axios interceptor adds Bearer token to all API calls
    |
    v
On 401 --> attempt token refresh --> retry original request
    |
    v
Refresh fails --> logout + redirect to /login
```

---

## API Endpoints Summary (48 Routes)

### Public

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api/v1/whatsapp/webhook` | WhatsApp verification challenge |
| POST | `/api/v1/whatsapp/webhook` | Inbound message handler |
| POST | `/api/v1/payments/webhook` | Paystack payment webhook |

### Authentication

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/auth/login` | Staff login (returns JWT) |
| POST | `/api/v1/auth/refresh` | Token refresh |
| POST | `/api/v1/auth/register` | Register new staff (super_admin only) |

### Admin (JWT required)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/admin/conversations` | List conversations (filterable) |
| GET | `/api/v1/admin/conversations/{id}` | Get conversation with messages |
| POST | `/api/v1/admin/conversations/{id}/reply` | Agent sends reply |
| POST | `/api/v1/admin/conversations/{id}/assign` | Assign agent |
| POST | `/api/v1/admin/conversations/{id}/pause` | Pause bot (agent takeover) |
| POST | `/api/v1/admin/conversations/{id}/resume` | Resume bot |
| POST | `/api/v1/admin/conversations/{id}/close` | Close conversation |
| GET | `/api/v1/admin/tickets` | List support tickets |
| GET | `/api/v1/admin/tickets/stats` | Ticket counts by status |
| GET | `/api/v1/admin/tickets/{id}` | Get ticket with notes |
| PUT | `/api/v1/admin/tickets/{id}` | Update ticket |
| POST | `/api/v1/admin/tickets/{id}/notes` | Add internal note |
| GET | `/api/v1/admin/agents` | List admin users |
| GET | `/api/v1/admin/agents/{id}` | Get agent details |

### Data APIs (JWT required)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/programmes` | List programmes |
| GET | `/api/v1/programmes/{id}` | Get programme with schedules |
| GET | `/api/v1/students` | List/search students |
| GET | `/api/v1/students/{id}` | Get student with enrollments |
| GET | `/api/v1/payments` | List payments |
| POST | `/api/v1/payments` | Initiate payment |
| GET | `/api/v1/notifications` | List notifications |

### Analytics (JWT required)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/analytics/volume` | Conversation volume over time |
| GET | `/api/v1/analytics/funnel` | Conversion funnel |
| GET | `/api/v1/analytics/resolution-rate` | Bot resolution rate |
| GET | `/api/v1/analytics/response-time` | Average agent response time |
| GET | `/api/v1/analytics/referrals` | Referral performance |
| GET | `/api/v1/analytics/referrals/leaderboard` | Top referral codes |
| GET | `/api/v1/analytics/ai` | AI assistant analytics (resolution rate, confidence) |
| GET | `/api/v1/analytics/ai/top-queries` | Most common AI queries |

### Engagement (no auth, called by Learning Service)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/engagement/attendance` | Attendance notification |
| POST | `/api/v1/engagement/progress/notify` | Progress notification |
| POST | `/api/v1/engagement/certificate/notify` | Certificate notification |

---

## Cross-Platform Sync

The platform uses `parent.whatsapp_number` as the shared identity key across all channels. A registration started on WhatsApp can be continued on web/mobile:

1. `GET /api/v1/students?whatsapp={phone}` -- look up parent + students
2. `POST /api/v1/payments` -- initiate payment for an existing enrollment
3. `GET /api/v1/programmes` -- browse programmes (same catalogue)

No duplicate APIs exist. WhatsApp, mobile, and web all hit the same FastAPI backend. CORS is configured via the `CORS_ORIGINS` environment variable (comma-separated origins in production, allow-all in development).

---

## Infrastructure & Deployment

### Docker Compose (5 Services)

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | Dockerfile (Python 3.12-slim) | 8000 | FastAPI + auto-migrations on startup |
| `worker` | Same image | - | Celery worker (concurrency=2) |
| `beat` | Same image | - | Celery beat scheduler |
| `db` | postgres:16 | 5432 | PostgreSQL with health check |
| `redis` | redis:7-alpine | 6379 | Message broker + result backend |

### Database Connection Pool

- **Driver:** asyncpg
- **Pool size:** 20
- **Max overflow:** 10
- **Pre-ping:** enabled

### Migrations

Alembic runs automatically on API container startup (`alembic upgrade head`). 6 migration files cover the full schema across all phases.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `APP_ENV` | development / production |
| `SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | PostgreSQL connection (asyncpg) |
| `REDIS_URL` | Redis connection |
| `WA_PHONE_NUMBER_ID` | WhatsApp Business phone number ID |
| `WA_BUSINESS_ACCOUNT_ID` | WhatsApp Business account ID |
| `WA_ACCESS_TOKEN` | WhatsApp Cloud API bearer token |
| `WA_VERIFY_TOKEN` | Webhook verification token |
| `WA_APP_SECRET` | HMAC signature verification secret |
| `WA_API_VERSION` | Graph API version (default: v21.0) |
| `PAYSTACK_SECRET_KEY` | Paystack secret key |
| `PAYSTACK_PUBLIC_KEY` | Paystack public key |
| `PAYSTACK_CALLBACK_URL` | Payment callback URL |
| `AWS_ACCESS_KEY_ID` | S3 access for receipt storage |
| `AWS_SECRET_ACCESS_KEY` | S3 secret |
| `AWS_S3_BUCKET` | Receipt bucket (edpassare-receipts) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL (default: 60) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL (default: 7) |
| `CORS_ORIGINS` | Allowed origins (comma-separated) |
| `ANTHROPIC_API_KEY` | Claude AI API key (claude-sonnet-4-6) |

### Security

- **Webhook verification:** X-Hub-Signature-256 HMAC-SHA256
- **Rate limiting:** slowapi with configurable limits
- **Audit logging:** Custom middleware logs all requests
- **Password hashing:** bcrypt
- **CORS:** Restrictive in production, permissive in development
- **Docs:** Swagger/ReDoc disabled in production

---

## Dependencies (requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| anthropic | 0.42.0 | Claude AI SDK for conversational assistant |
| fastapi | 0.115.6 | Web framework |
| uvicorn[standard] | 0.34.0 | ASGI server |
| sqlalchemy[asyncio] | 2.0.36 | Async ORM |
| asyncpg | 0.30.0 | PostgreSQL async driver |
| alembic | 1.14.0 | Database migrations |
| redis | 5.2.1 | Redis client |
| celery | 5.4.0 | Task queue |
| httpx | 0.28.1 | Async HTTP client (WhatsApp + Paystack APIs) |
| python-jose[cryptography] | 3.3.0 | JWT encoding/decoding |
| bcrypt | 4.2.1 | Password hashing |
| pydantic[email] | 2.10.4 | Validation + email support |
| pydantic-settings | 2.7.0 | Environment-based settings |
| python-multipart | 0.0.20 | Form data parsing |
| slowapi | 0.1.9 | Rate limiting |
| weasyprint | 63.1 | PDF receipt generation |
| python-dotenv | 1.0.1 | .env file loading |

**Total: 17 production dependencies**

---

## Development Phases

| Phase | Status | Scope |
|-------|--------|-------|
| **Phase 1** | Complete | Core messaging: webhook, conversation engine, WhatsApp Cloud API integration |
| **Phase 2** | Complete | Registration: parents, students, programmes, enrollments, multi-step registration flow |
| **Phase 3** | Complete | Payments: Paystack integration, payment flow, webhook handling, PDF receipts |
| **Phase 4** | Complete | Notifications: preferences, scheduled reminders (Celery Beat), notification service |
| **Phase 5** | Complete | Support & Admin: escalation system, support tickets, admin dashboard (React), RBAC |
| **Phase 6A** | Complete | Analytics & Referrals: event tracking, conversion funnel, referral system, partnership flow, engagement endpoints, analytics dashboard |
| **Phase 6B** | Complete | AI Conversational Assistant: Claude tool_use integration, 7 controlled backend functions, intent detection, confidence scoring, rate limiting, interaction logging, AI analytics dashboard |
| **Hardening** | Complete | 59 integration tests, webhook signature enforcement (no bypass), JWT/RBAC on all endpoints, enhanced health check (db/Redis/WhatsApp), correlation ID middleware, structured logging, DEPLOYMENT.md, WHATSAPP_TEMPLATES.md |
