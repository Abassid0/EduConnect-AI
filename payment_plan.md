\# Phase D Implementation Prompt — Payment Plans



\## Context



Edpassare WhatsApp Platform — FastAPI + PostgreSQL + Redis + Celery backend,

React 18 + Vite + Tailwind CSS admin dashboard.

Project root: `C:\\Users\\HP\\OneDrive - gdl.com.ng\\Desktop\\AI-CustomerSupport\\Edpassāre WhatsApp Platform`



\*\*Docker cp workflow is mandatory.\*\* The `ā` in the project path breaks volume mounts.

Every new or changed Python file must be `docker cp`'d into `edpassare-build-api-1` and the

container restarted before testing. Use `alembic/env\_migrate.py` (target\_metadata=None) as

`env.py` when running migrations, then restore the real `env.py` after.



Phases A, B, C must be complete. This phase extends the billing system from Phase 2.



\## Existing patterns to read before writing any code



| What you need | File |

|---|---|

| Existing Invoice / InvoiceItem models | `app/models/invoice.py`, `app/models/invoice\_item.py` |

| Billing service — invoice creation | `app/services/billing\_service.py` |

| Billing API router | `app/api/v1/billing.py` |

| Celery task pattern | `app/tasks/broadcast\_tasks.py` |

| Invoice reminder task | `app/tasks/billing\_tasks.py` |

| FlowResult dataclass | `app/flows/\_\_init\_\_.py` |

| billing\_flow.py — YES/NO pattern | `app/flows/billing\_flow.py` |

| Model registration | `app/models/\_\_init\_\_.py` |

| API router registration | `app/api/v1/\_\_init\_\_.py` |

| Admin page pattern | `admin-dashboard/src/pages/Billing.jsx` |

| API client | `admin-dashboard/src/api/client.js` |



\## Goal



A school admin creates a payment plan for an existing unpaid invoice — splitting the total

into N installments (weekly / biweekly / monthly). Each installment gets its own due date.

Celery sends a reminder the day before each installment is due. Parents see their plan

status via the bot. Overdue installments are flagged daily.



\## Data model



\### `payment\_plans`



| Column | Type | Notes |

|---|---|---|

| id | UUID PK | |

| invoice\_id | UUID FK → invoices.id SET NULL | the original full invoice |

| parent\_id | UUID FK → parents.id CASCADE | |

| student\_id | UUID FK → students.id SET NULL | nullable |

| total\_amount | Numeric(12,2) | copied from invoice at plan creation |

| installment\_count | Integer | 2–24 |

| frequency | String(20) | weekly / biweekly / monthly |

| start\_date | Date | date of first installment |

| status | String(20) | active / completed / cancelled / defaulted |

| created\_by | UUID FK → admin\_users.id SET NULL | |

| created\_at | DateTime TZ | server\_default now() |

| updated\_at | DateTime TZ | server\_default now(), onupdate now() |



\### `payment\_plan\_installments`



| Column | Type | Notes |

|---|---|---|

| id | UUID PK | |

| plan\_id | UUID FK → payment\_plans.id CASCADE | |

| installment\_number | Integer | 1-based sequence |

| due\_date | Date | computed from start\_date + frequency |

| amount | Numeric(12,2) | total\_amount / installment\_count (last installment absorbs rounding) |

| status | String(20) | pending / paid / overdue / waived |

| paid\_at | DateTime TZ | nullable |

| created\_at | DateTime TZ | server\_default now() |



UNIQUE constraint on `(plan\_id, installment\_number)`.



\## Tasks — complete in this order



\### Task 1 — Models



Create `app/models/payment\_plan.py` with `PaymentPlan` and `PaymentPlanInstallment`.



Add to `app/models/\_\_init\_\_.py`:

```python

from app.models.payment\_plan import PaymentPlan, PaymentPlanInstallment

```

Add both to `\_\_all\_\_`.



Write migration `alembic/versions/012\_payment\_plans.py` (down\_revision = "011").

Verify: CASCADE on installments.plan\_id, SET NULL on invoice\_id / student\_id / created\_by.

Apply via env\_migrate.py.



\### Task 2 — Service layer (`app/services/payment\_plan\_service.py`)



```python

async def create\_plan(

&#x20;   invoice\_id, parent\_id, installment\_count, frequency, start\_date, db,

&#x20;   student\_id=None, created\_by=None

) -> PaymentPlan

```

\- Validates: invoice must exist and status must be "sent" or "overdue". installment\_count 2–24.

\- Computes due dates: weekly = +7 days, biweekly = +14 days, monthly = +1 calendar month.

\- Last installment absorbs rounding (total - sum of others).

\- Sets invoice.status = "on\_plan" after creation.

\- Returns the plan with installments eager-loaded.



```python

async def get\_plan(plan\_id, db) -> PaymentPlan | None

async def list\_plans(db, parent\_id=None, status=None, limit=50, offset=0) -> list\[PaymentPlan]

async def get\_plan\_for\_invoice(invoice\_id, db) -> PaymentPlan | None

async def get\_active\_plan\_for\_parent(parent\_id, db) -> PaymentPlan | None

async def mark\_installment\_paid(installment\_id, db) -> PaymentPlanInstallment

&#x20; # sets status=paid, paid\_at=now(); if all installments paid → plan.status=completed

async def waive\_installment(installment\_id, db) -> PaymentPlanInstallment

&#x20; # sets status=waived; rechecks completion

async def cancel\_plan(plan\_id, db) -> PaymentPlan

&#x20; # sets status=cancelled; sets invoice.status back to "overdue"

async def check\_and\_mark\_overdue(db) -> int

&#x20; # marks all pending installments where due\_date < today as overdue; returns count

async def get\_parent\_plan\_summary(parent\_id, db) -> dict

&#x20; # returns: plan\_id, total\_amount, paid\_amount, remaining\_amount,

&#x20; #          next\_installment (number, due\_date, amount), overdue\_count

```



\### Task 3 — WhatsApp flow integration



In `app/flows/billing\_flow.py` (or a new `app/flows/payment\_plan\_flow.py`), add a step

that the parent can reach from the "Check Balance" option. When the parent has an active

payment plan, show a summary message:



```

\*Your Payment Plan\*

Total: ₦120,000

Paid: ₦40,000 (2 of 6 installments)

Next due: ₦20,000 on 15/09/2026



Reply 'menu' to return.

```



Add a `"payment\_plan"` handler to `\_get\_flow\_handler()` in `conversation\_engine.py`.



Do NOT add a pending-plan interrupt (unlike permission slips). The plan summary is

pull-based — parent requests it — not push.



\### Task 4 — Celery tasks (`app/tasks/billing\_tasks.py` or new file)



Add two tasks:



```python

@celery\_app.task

def send\_installment\_reminders():

&#x20;   """

&#x20;   Run daily. For each installment due tomorrow (due\_date == today + 1 day),

&#x20;   send a WhatsApp notification to the parent.

&#x20;   Uses event\_key = f"installment\_reminder:{installment.id}:{today}" for dedup.

&#x20;   """



@celery\_app.task  

def check\_overdue\_installments():

&#x20;   """

&#x20;   Run daily. Calls payment\_plan\_service.check\_and\_mark\_overdue().

&#x20;   Logs count of newly overdue installments.

&#x20;   """

```



Register both in the Celery beat schedule (check existing beat config for the pattern).



\### Task 5 — API router (`app/api/v1/payment\_plan.py`)



```

POST   /billing/invoices/{invoice\_id}/plan          — create plan

GET    /billing/plans                                — list all (admin)

GET    /billing/plans/{plan\_id}                      — get plan + installments

GET    /billing/parent/{parent\_id}/plan              — active plan for parent

POST   /billing/plans/{plan\_id}/cancel               — cancel plan

PUT    /billing/plans/{plan\_id}/installments/{inst\_id}/pay    — mark paid

PUT    /billing/plans/{plan\_id}/installments/{inst\_id}/waive  — waive

```



All write endpoints require `require\_role("super\_admin", "admin")`.

Register in `app/api/v1/\_\_init\_\_.py`.



\### Task 6 — Admin dashboard API client



Add to `admin-dashboard/src/api/client.js`:



```js

export const paymentPlans = {

&#x20; create: (invoiceId, data) =>

&#x20;   client.post(`/billing/invoices/${invoiceId}/plan`, data).then(r => r.data),

&#x20; list: (params) =>

&#x20;   client.get('/billing/plans', { params }).then(r => r.data),

&#x20; get: (id) =>

&#x20;   client.get(`/billing/plans/${id}`).then(r => r.data),

&#x20; parentPlan: (parentId) =>

&#x20;   client.get(`/billing/parent/${parentId}/plan`).then(r => r.data),

&#x20; cancel: (id) =>

&#x20;   client.post(`/billing/plans/${id}/cancel`).then(r => r.data),

&#x20; markPaid: (planId, instId) =>

&#x20;   client.put(`/billing/plans/${planId}/installments/${instId}/pay`).then(r => r.data),

&#x20; waive: (planId, instId) =>

&#x20;   client.put(`/billing/plans/${planId}/installments/${instId}/waive`).then(r => r.data),

};

```



\### Task 7 — Admin dashboard UI



\*\*Extend `admin-dashboard/src/pages/Billing.jsx`\*\* — do not create a separate page.



In the invoices table, add a "Set Up Plan" action button for invoices with

`status === "sent" || status === "overdue"` that don't already have a plan.



Clicking "Set Up Plan" expands an inline panel below that invoice row (not a modal)

with:

\- Installment count (number input, 2–24)

\- Frequency (select: weekly / biweekly / monthly)

\- Start date (date picker, default today + 7 days)

\- "Create Plan" button → calls `paymentPlans.create(invoiceId, data)` → collapses panel, reloads



For invoices that already have a plan, show a "View Plan" button instead.

"View Plan" opens a detail section below the row with:

\- Plan status badge (active / completed / cancelled / defaulted)

\- Progress bar: paid installments / total

\- Installment table: #, Due Date, Amount, Status badge, Actions (Mark Paid / Waive for pending/overdue installments)

\- Cancel Plan button (two-click confirm)



Use the same Tailwind style as the existing Billing page.



\## Guardrails



1\. \*\*One plan per invoice\*\* — `create\_plan` must check `get\_plan\_for\_invoice` and raise

&#x20;  `ValueError("This invoice already has a payment plan.")` if one exists.



2\. \*\*Rounding\*\* — last installment = total - (amount \* (count - 1)). Never let rounding

&#x20;  cause total installments to exceed or fall short of total\_amount by more than 1 kobo.



3\. \*\*Cancellation restores invoice\*\* — `cancel\_plan` sets invoice.status = "overdue" if

&#x20;  any installments are unpaid; "paid" if somehow all were paid before cancel (no-op).



4\. \*\*Completion is automatic\*\* — whenever `mark\_installment\_paid` or `waive\_installment`

&#x20;  is called, check if all installments are paid/waived; if so, set plan.status = "completed"

&#x20;  and invoice.status = "paid".



5\. \*\*Bot summary is read-only\*\* — the WhatsApp flow only shows the plan; it does not let

&#x20;  parents mark their own installments paid. Payment confirmation happens via the existing

&#x20;  payment webhook (Paystack/Flutterwave) or admin override.



6\. \*\*Verify Vite build\*\* — run `npm run build` in `admin-dashboard/` and confirm zero

&#x20;  errors before reporting complete.

