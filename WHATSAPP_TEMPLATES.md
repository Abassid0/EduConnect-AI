# Edpassare WhatsApp Message Templates

This document lists every WhatsApp message template needed for the Edpassare platform. Templates must be submitted and approved in the Meta Business Manager before they can be sent via the WhatsApp Business API.

> **Note:** The platform sends most messages as free-form text within 24-hour conversation windows (triggered by the user messaging first). Templates are needed for **proactive notifications** — messages sent outside the 24-hour window.

---

## Template Naming Convention

All template names use snake_case with the prefix pattern: `<category>_<timing/type>`.

---

## 1. Class Reminders

### `class_reminder_24h`

**Category:** UTILITY
**Purpose:** Remind parents of a class happening tomorrow.

```
Hi {{1}},

Reminder: {{2}} has a {{3}} class tomorrow at {{4}}.

See you there! 🎓

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Parent's full name | Amina |
| `{{2}}` | Student's full name | Ibrahim |
| `{{3}}` | Programme name | AI for Kids |
| `{{4}}` | Class start time | 10:00 AM |

---

### `class_reminder_1h`

**Category:** UTILITY
**Purpose:** Remind parents of a class starting in 1 hour.

```
Hi {{1}},

{{2}}'s {{3}} class starts in 1 hour ({{4}}).

Please ensure they are ready. See you soon!

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Parent's full name | Amina |
| `{{2}}` | Student's full name | Ibrahim |
| `{{3}}` | Programme name | AI for Kids |
| `{{4}}` | Class start time | 10:00 AM |

---

## 2. Payment Reminders

### `payment_reminder_7day`

**Category:** UTILITY
**Purpose:** Friendly reminder 7 days before payment is due.

```
Hi {{1}},

Just a friendly reminder that payment for {{2}}'s enrollment in {{3}} is due in 7 days.

Amount: {{4}}

Reply 'menu' to make a payment.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Parent's full name | Amina |
| `{{2}}` | Student's full name | Ibrahim |
| `{{3}}` | Programme name | Robotics Beginners |
| `{{4}}` | Fee amount | N50,000 |

---

### `payment_reminder_due`

**Category:** UTILITY
**Purpose:** Urgent reminder on the payment due date.

```
Hi {{1}},

Payment for {{2}}'s enrollment in {{3}} is due today.

Amount: {{4}}

Please make your payment to secure the spot. Reply 'menu' and select 'Make Payment'.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Parent's full name | Amina |
| `{{2}}` | Student's full name | Ibrahim |
| `{{3}}` | Programme name | Robotics Beginners |
| `{{4}}` | Fee amount | N50,000 |

---

### `payment_reminder_overdue`

**Category:** UTILITY
**Purpose:** Overdue payment notification (1 day past due).

```
Hi {{1}},

Payment for {{2}}'s enrollment in {{3}} is now overdue.

Amount: {{4}}

Please pay as soon as possible to avoid losing the enrollment. Reply 'menu' and select 'Make Payment'.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Parent's full name | Amina |
| `{{2}}` | Student's full name | Ibrahim |
| `{{3}}` | Programme name | Robotics Beginners |
| `{{4}}` | Fee amount | N50,000 |

---

## 3. Invoice Billing Templates

These templates are used for proactive invoice notifications and escalating payment reminders sent by Celery beat tasks.

### `invoice_notification`

**Category:** UTILITY
**Purpose:** Sent when an admin creates and sends an invoice to a parent.

```
New Invoice from Edpassare

Invoice #: {{1}}
Description: {{2}}
Amount Due: {{3}}
Due Date: {{4}}

Reply 'menu' and select 'Make Payment' to pay now, or 'Check Balance' to view all outstanding fees.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Invoice number | INV-20260814-12345 |
| `{{2}}` | Invoice title / description | School Fees - Term 1 2026 |
| `{{3}}` | Amount due | N75,000 |
| `{{4}}` | Due date | 30/08/2026 |

---

### `invoice_reminder`

**Category:** UTILITY
**Purpose:** Escalating payment reminder sent at 7 tiers: 7-day before, 3-day before, due-today, then overdue at 1/3/7/14 days. The message body is identical across all tiers — the urgency is carried in the free-form text sent alongside the template (or alternatively, submit separate template variants per tier).

```
Hi {{1}},

Payment reminder for your invoice:

Description: {{2}}
Amount Due: {{3}}
Due Date: {{4}}

Reply 'menu' and select 'Make Payment' to settle this now.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Parent's full name | Amina |
| `{{2}}` | Invoice title | School Fees - Term 1 2026 |
| `{{3}}` | Remaining amount | N75,000 |
| `{{4}}` | Due date | 30/08/2026 |

**Reminder cadence (Celery beat, runs daily at 8:30 AM WAT):**

| Tier | Days | Urgency |
|------|------|---------|
| 1 | 7 days before due | Friendly |
| 2 | 3 days before due | Reminder |
| 3 | Due date | Urgent |
| 4 | 1 day overdue | Overdue |
| 5 | 3 days overdue | Overdue |
| 6 | 7 days overdue | Overdue |
| 7 | 14 days overdue | Final Notice |

Each tier is deduplicated via `event_key = invoice_reminder:{id}:{tier}:{date}` — parents receive at most one message per tier.

---

## 4. Payment Receipts

Sent as **free-form text** within the 24-hour window (triggered by the Paystack webhook after the parent made a payment). No template submission required.

**Message format:**
```
Payment Received!

Reference: EDP-PAY-20260814143000-12345
Student: Ibrahim
Programme: AI for Kids
Amount: N50,000 NGN
Date: 14/08/2026 14:30
Status: Confirmed

Your enrollment has been confirmed. Thank you!
```

---

## 5. Escalation Notifications

Sent as **free-form text** within the 24-hour window (the user just messaged the bot, so the window is open).

**Message format:**
```
Your request has been escalated to our support team.

Ticket: *EDP-123456*
A team member will reach out to you shortly.

Thank you for your patience.
```

---

## 6. Bot Resume Notification

Sent as **free-form text** within the 24-hour window (the agent just replied, keeping the window open).

**Message format:**
```
Your conversation with our support team has ended.
The bot is back online — reply *menu* anytime to continue.
```

---

## 7. Attendance Notifications

Sent as **free-form text** within the 24-hour window or as a proactive template if outside the window.

**Message format (present):**
```
Attendance update for *Ibrahim*

Date: 14/08/2026
Status: Present
Programme: AI for Kids
```

**Message format (absent):**
```
Attendance update for *Ibrahim*

Date: 14/08/2026
Status: Absent
Programme: AI for Kids

If this is unexpected, please contact us by replying 'menu' and selecting Get Help.
```

### Recommended template: `attendance_notification`

**Category:** UTILITY

```
Attendance update for *{{1}}*

Date: {{2}}
Status: {{3}}
Programme: {{4}}

Reply 'menu' for more options.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Student's full name | Ibrahim |
| `{{2}}` | Date | 14/08/2026 |
| `{{3}}` | Status | Present / Absent / Late |
| `{{4}}` | Programme name | AI for Kids |

---

## 8. Progress & Certificate Notifications

Sent as **free-form text** or as proactive templates.

### Recommended template: `progress_update`

**Category:** UTILITY

```
*{{1}}*

{{2}}

Student: {{3}}

Reply 'menu' for more options.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Title | Math Grade Posted |
| `{{2}}` | Message body | Your child scored 90% on the mid-term assessment |
| `{{3}}` | Student's full name | Ibrahim |

### Recommended template: `certificate_completion`

**Category:** UTILITY

```
Congratulations! *{{1}}* has completed the *{{2}}* programme!

A certificate of completion is now available.

— Edpassare
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| `{{1}}` | Student's full name | Ibrahim |
| `{{2}}` | Programme name | AI for Kids |

---

## 9. Welcome / Greeting

Sent as **free-form text** within the 24-hour window (the user just messaged first).

**Message format:**
```
Hi {name}! Welcome to Edpassare. Let me show you what I can help with.
```

Followed by an **interactive list message** (main menu) — interactive messages do not require template approval.

---

## 10. AI Assistant Responses

Sent as **free-form text** within the 24-hour window. AI responses are dynamically generated by Claude and don't use templates.

---

## Template Submission Checklist

Templates must be submitted via Meta Business Manager → WhatsApp Manager → Message Templates.

| Template Name | Category | Status |
|---------------|----------|--------|
| `class_reminder_24h` | UTILITY | Submit |
| `class_reminder_1h` | UTILITY | Submit |
| `payment_reminder_7day` | UTILITY | Submit |
| `payment_reminder_due` | UTILITY | Submit |
| `payment_reminder_overdue` | UTILITY | Submit |
| `invoice_notification` | UTILITY | Submit |
| `invoice_reminder` | UTILITY | Submit |
| `attendance_notification` | UTILITY | Recommended |
| `progress_update` | UTILITY | Recommended |
| `certificate_completion` | UTILITY | Recommended |

**Required** templates (7): Class reminders, enrollment payment reminders, and invoice billing templates are all used by Celery beat scheduled tasks and must be approved before going live.

**Recommended** templates (3): Attendance, progress, and certificate templates are currently sent as free-form text but should be submitted as templates for proactive sending outside the 24-hour window.

---

## Meta Template Approval Tips

1. Use the `UTILITY` category for transactional messages (reminders, receipts, status updates)
2. Include `— Edpassare` at the end of each template for brand identification
3. Do not include URLs in templates unless they are approved domains
4. Keep templates under 1024 characters
5. Avoid promotional language in UTILITY templates — save that for `MARKETING` category
6. Templates typically take 24-48 hours to approve
7. Test with the WhatsApp test number before switching to production

---

## Testing Templates with Telegram (Pre-Launch QA)

WhatsApp Business API charges per conversation. Use the Telegram bot as a free, zero-approval test channel to verify every template renders correctly before submitting to Meta.

### Why this works

All WhatsApp-format payloads are routed through a channel-aware messaging layer. The Telegram bot receives the same rendered message that a parent would see on WhatsApp, because `telegram_service._send_template()` calls `template_registry.render()` — the same function used by the Celery reminder tasks.

### QA workflow

**Step 1 — List all registered templates**

```http
GET /api/v1/telegram/templates
Authorization: Bearer <admin_token>
```

Returns all template names, parameter counts, and a preview of the first 80 characters.

**Step 2 — Send a template to your Telegram chat**

Find your Telegram chat ID by messaging your bot and reading the update, then:

```http
POST /api/v1/telegram/test-template
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "template_name": "invoice_reminder",
  "params": ["Amina", "School Fees - Term 1 2026", "N75,000", "30/08/2026"]
}
```

The response includes `rendered_preview` — the exact string sent to Telegram — so you can confirm the substitution without opening the app.

**Step 3 — Verify the rendering in Telegram**

Check that:
- All `{{N}}` placeholders were substituted (none remain literal)
- The line breaks, spacing, and formatting match the template body in this document
- The call-to-action instructions at the end make sense in context

**Step 4 — Repeat for every template before submission**

Go through all 7 required templates with realistic sample data. Use values that mirror a real school's invoice (multi-word programme names, amounts with commas, Nigerian date format `DD/MM/YYYY`).

**Step 5 — Submit to Meta**

Once Telegram rendering passes, copy the template body from this document verbatim into Meta Business Manager and submit for approval.

### Template parameter reference

| Template | `{{1}}` | `{{2}}` | `{{3}}` | `{{4}}` |
|----------|---------|---------|---------|---------|
| `class_reminder_24h` | Parent name | Student name | Programme | Time |
| `class_reminder_1h` | Parent name | Student name | Programme | Time |
| `payment_reminder_7day` | Parent name | Student name | Programme | Fee amount |
| `payment_reminder_due` | Parent name | Student name | Programme | Fee amount |
| `payment_reminder_overdue` | Parent name | Student name | Programme | Fee amount |
| `invoice_notification` | Invoice # | Description | Amount due | Due date |
| `invoice_reminder` | Parent name | Description | Amount remaining | Due date |

### Finding your Telegram chat ID

1. Start a conversation with your bot (search for it by username in Telegram)
2. Send any message
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. The `chat.id` field in the response is your chat ID (it may be a negative number for groups)
