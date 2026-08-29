\# Phase E Implementation Prompt — Report Cards



\## Context



Edpassare WhatsApp Platform — FastAPI + PostgreSQL + Redis + Celery backend,

React 18 + Vite + Tailwind CSS admin dashboard.

Project root: `C:\\Users\\HP\\OneDrive - gdl.com.ng\\Desktop\\AI-CustomerSupport\\Edpassāre WhatsApp Platform`



\*\*Docker cp workflow is mandatory.\*\* Every new/changed Python file must be `docker cp`'d

into `edpassare-build-api-1`. Use `alembic/env\_migrate.py` for migrations.



Phases A–D must be complete. Migration down\_revision = "012".



\## Existing patterns to read before writing any code



| What you need | File |

|---|---|

| PermissionSlip model (two-table pattern) | `app/models/permission\_slip.py` |

| Permission service (get\_pending, record\_response) | `app/services/permission\_service.py` |

| Pending-slip interrupt in conversation engine | `app/services/conversation\_engine.py` lines 246–275 |

| fan\_out\_permission\_slip Celery task | `app/tasks/broadcast\_tasks.py` |

| send\_notification with event\_key dedup | `app/services/notification\_service.py` |

| FlowResult + interactive buttons | `app/flows/permission\_flow.py` |

| Broadcast page (tab pattern, detail view) | `admin-dashboard/src/pages/Broadcast.jsx` |

| Permissions page (detail view + response table) | `admin-dashboard/src/pages/Permissions.jsx` |

| resolve\_recipients | `app/services/broadcast\_service.py` |

| whatsapp\_helpers | `app/utils/whatsapp\_helpers.py` |



\## Goal



An admin uploads a student's term report card (subjects + scores + grades + teacher

comments). Publishing it fans out a WhatsApp notification to the parent(s) of that

student. The parent sees a formatted grade summary via the bot and taps "Acknowledge".

Unacknowledged report cards appear as an interrupt the next time the parent messages

the bot. The admin sees a delivery dashboard per report card.



\## Data model



\### `report\_cards`



| Column | Type | Notes |

|---|---|---|

| id | UUID PK | |

| student\_id | UUID FK → students.id CASCADE | |

| academic\_term | String(100) | e.g. "2025/2026 Term 1" |

| overall\_grade | String(10) | nullable — e.g. "A", "Distinction" |

| overall\_score | Numeric(5,2) | nullable — aggregate/average |

| position\_in\_class | Integer | nullable |

| class\_size | Integer | nullable |

| teacher\_comment | Text | nullable |

| status | String(20) | draft / published |

| published\_at | DateTime TZ | nullable |

| published\_by | UUID FK → admin\_users.id SET NULL | nullable |

| created\_at | DateTime TZ | server\_default now() |

| updated\_at | DateTime TZ | server\_default now(), onupdate now() |



UNIQUE constraint on `(student\_id, academic\_term)` — one card per student per term.



\### `report\_card\_subjects`



| Column | Type | Notes |

|---|---|---|

| id | UUID PK | |

| report\_card\_id | UUID FK → report\_cards.id CASCADE | |

| subject\_name | String(100) | |

| score | Numeric(5,2) | nullable |

| grade | String(10) | nullable — A / B / C / F |

| teacher\_comment | Text | nullable |

| sort\_order | Integer | for display ordering |



\### `report\_card\_deliveries`



| Column | Type | Notes |

|---|---|---|

| id | UUID PK | |

| report\_card\_id | UUID FK → report\_cards.id CASCADE | |

| parent\_id | UUID FK → parents.id CASCADE | |

| delivered\_at | DateTime TZ | nullable |

| acknowledged\_at | DateTime TZ | nullable |

| acknowledged\_via | String(20) | nullable — whatsapp / admin |



UNIQUE constraint on `(report\_card\_id, parent\_id)`.



\## Tasks — complete in this order



\### Task 1 — Models



Create `app/models/report\_card.py` with `ReportCard`, `ReportCardSubject`,

`ReportCardDelivery`.



Add to `app/models/\_\_init\_\_.py` and `\_\_all\_\_`.



Write `alembic/versions/013\_report\_cards.py` (down\_revision = "012").

Verify: CASCADE on subjects and deliveries, SET NULL on published\_by.

Apply via env\_migrate.py.



\### Task 2 — Service layer (`app/services/report\_card\_service.py`)



```python

async def create\_report\_card(

&#x20;   student\_id, academic\_term, db,

&#x20;   overall\_grade=None, overall\_score=None, position\_in\_class=None,

&#x20;   class\_size=None, teacher\_comment=None, created\_by=None

) -> ReportCard

\# Raises ValueError if a card for (student\_id, academic\_term) already exists.



async def add\_subject(

&#x20;   report\_card\_id, subject\_name, db,

&#x20;   score=None, grade=None, teacher\_comment=None, sort\_order=0

) -> ReportCardSubject



async def replace\_subjects(

&#x20;   report\_card\_id, subjects: list\[dict], db

) -> list\[ReportCardSubject]

\# Deletes existing subjects and inserts the new list in one transaction.

\# Each dict: {subject\_name, score, grade, teacher\_comment, sort\_order}



async def get\_report\_card(report\_card\_id, db) -> ReportCard | None



async def list\_report\_cards(

&#x20;   db, student\_id=None, status=None, limit=50, offset=0

) -> list\[ReportCard]



async def publish\_report\_card(

&#x20;   report\_card\_id, published\_by, db

) -> ReportCard

\# Sets status=published, published\_at=now().

\# Creates a ReportCardDelivery row (status undelivered) for each parent

\# enrolled with this student. Raises ValueError if already published.



async def get\_unacknowledged\_for\_parent(

&#x20;   parent\_id, db

) -> list\[ReportCard]

\# Returns published report cards where the parent's delivery row

\# has acknowledged\_at IS NULL.



async def acknowledge(

&#x20;   report\_card\_id, parent\_id, db, via="whatsapp"

) -> ReportCardDelivery

\# Sets acknowledged\_at=now(), acknowledged\_via=via.

\# Idempotent — re-acknowledging updates the existing row.



async def get\_delivery\_summary(report\_card\_id, db) -> dict

\# Returns: total\_parents, delivered\_count, acknowledged\_count,

\#          deliveries list (parent\_id, delivered\_at, acknowledged\_at, via)



async def format\_report\_card\_message(report\_card: ReportCard) -> str

\# Returns a WhatsApp-formatted string:

\# \*Report Card — {student name} | {term}\*

\# Position: {x} of {class\_size}  (if available)

\#

\# 📚 Subjects:

\# Mathematics    85    B+

\# English        92    A

\# ...

\#

\# Overall: {overall\_grade} ({overall\_score})

\# {teacher\_comment}

```



\### Task 3 — WhatsApp flow (`app/flows/report\_card\_flow.py`)



Steps: `start` → `awaiting\_acknowledgement`



\- `start`: fetch the report card, format it via `format\_report\_card\_message`, send it

&#x20; with a single "Acknowledge" button (`report\_card\_ack\_{report\_card\_id}`).

\- `awaiting\_acknowledgement`: if input starts with `report\_card\_ack\_`, call

&#x20; `acknowledge()`, reply "Thank you — received. ✓", set `flow\_complete=True`.

&#x20; Any other input: re-show the button.

\- Store `report\_card\_id` in `flow\_data\["report\_card\_id"]`.

\- Never let exceptions propagate — always set `flow\_complete=True` on error.



\### Task 4 — Conversation engine



\*\*Edit 1\*\* — Add `"report\_card"` to `\_get\_flow\_handler()` after `"permission"`:



```python

if flow\_name == "report\_card":

&#x20;   from app.flows.report\_card\_flow import handle\_step

&#x20;   return handle\_step

```



\*\*Edit 2\*\* — Add a report-card interrupt that fires \*\*after\*\* the permission slip

interrupt and \*\*before\*\* `if conversation.current\_flow and conversation.current\_step:`.

Identical pattern to the permission slip interrupt:



```python

\# Unacknowledged report card interrupt

if not conversation.current\_flow:

&#x20;   try:

&#x20;       from app.services import report\_card\_service as \_rcs

&#x20;       # reuse \_parent fetched above if available, else re-fetch

&#x20;       if \_parent:

&#x20;           \_pending\_rc = await \_rcs.get\_unacknowledged\_for\_parent(\_parent.id, db)

&#x20;           if \_pending\_rc:

&#x20;               \_rc = \_pending\_rc\[0]

&#x20;               conversation.current\_flow = "report\_card"

&#x20;               conversation.current\_step = "start"

&#x20;               conversation.flow\_data = {"report\_card\_id": str(\_rc.id)}

&#x20;               from app.flows.report\_card\_flow import handle\_step as \_rc\_handle

&#x20;               \_rc\_result = await \_rc\_handle(

&#x20;                   step="start",

&#x20;                   user\_input="",

&#x20;                   flow\_data={"report\_card\_id": str(\_rc.id)},

&#x20;                   conversation=conversation,

&#x20;                   db=db,

&#x20;               )

&#x20;               await \_handle\_flow\_result(\_rc\_result, whatsapp\_id, conversation, db, channel)

&#x20;               return

&#x20;   except Exception:

&#x20;       logger.exception("Report card interrupt failed for %s", whatsapp\_id)

```



Note: the permission-slip interrupt already fetches `\_parent`. Reuse that variable

rather than re-querying. Refactor the two interrupt blocks to share the parent lookup.



\### Task 5 — Celery fan-out (`app/tasks/report\_card\_tasks.py`)



```python

@celery\_app.task(bind=True, max\_retries=2, default\_retry\_delay=300)

def fan\_out\_report\_card(self, report\_card\_id: str) -> dict:

&#x20;   """

&#x20;   For each parent delivery row (created by publish\_report\_card),

&#x20;   send the formatted WhatsApp notification.

&#x20;   event\_key = f"rc\_delivery:{report\_card\_id}:{parent.id}"

&#x20;   After sending, set delivery.delivered\_at = now().

&#x20;   Rate-limit: time.sleep(0.2) between sends.

&#x20;   """

```



Call `fan\_out\_report\_card.delay(str(report\_card\_id))` from the publish API endpoint.



\### Task 6 — API router (`app/api/v1/report\_cards.py`)



```

POST   /report-cards                            — create (draft)

GET    /report-cards                            — list (filter: student\_id, status)

GET    /report-cards/{id}                       — get with subjects + delivery summary

PUT    /report-cards/{id}/subjects              — replace all subjects

POST   /report-cards/{id}/publish               — publish + queue fan-out

GET    /students/{student\_id}/report-cards      — student's full history

PUT    /report-cards/{id}/deliveries/{parent\_id}/acknowledge  — admin acknowledge

```



Register in `app/api/v1/\_\_init\_\_.py`.



Pydantic models:

\- `ReportCardCreate`: student\_id, academic\_term, optional fields

\- `SubjectIn`: subject\_name, score, grade, teacher\_comment, sort\_order

\- `ReportCardOut`: id, student\_id, academic\_term, status, published\_at,

&#x20; overall\_grade, overall\_score, position\_in\_class, class\_size, teacher\_comment,

&#x20; subject\_count, acknowledged\_count, total\_parents, created\_at



\### Task 7 — Admin dashboard API client



Add to `admin-dashboard/src/api/client.js`:



```js

export const reportCards = {

&#x20; list: (params) =>

&#x20;   client.get('/report-cards', { params }).then(r => r.data),

&#x20; get: (id) =>

&#x20;   client.get(`/report-cards/${id}`).then(r => r.data),

&#x20; create: (data) =>

&#x20;   client.post('/report-cards', data).then(r => r.data),

&#x20; setSubjects: (id, subjects) =>

&#x20;   client.put(`/report-cards/${id}/subjects`, { subjects }).then(r => r.data),

&#x20; publish: (id) =>

&#x20;   client.post(`/report-cards/${id}/publish`).then(r => r.data),

&#x20; studentHistory: (studentId) =>

&#x20;   client.get(`/students/${studentId}/report-cards`).then(r => r.data),

&#x20; getDeliveries: (id) =>

&#x20;   client.get(`/report-cards/${id}`).then(r => r.data),

&#x20; adminAcknowledge: (id, parentId) =>

&#x20;   client.put(`/report-cards/${id}/deliveries/${parentId}/acknowledge`).then(r => r.data),

};

```



\### Task 8 — Admin dashboard page (`admin-dashboard/src/pages/ReportCards.jsx`)



\*\*List view:\*\*

\- Columns: Student (name), Term, Status badge, Overall Grade, Position, Subjects,

&#x20; Acknowledged (x/y), Actions

\- Status badge: draft → gray, published → green

\- Actions: Draft → "Add Subjects" + "Publish" (two-click confirm)

&#x20; Published → "View Deliveries"

\- Create form (collapsible, above table): student search/select, academic term

&#x20; (text input), overall grade, overall score, position in class, class size, teacher comment



\*\*Subject editor (shown inline when "Add Subjects" is clicked):\*\*

\- Dynamic table with Add Row / Remove Row: Subject Name, Score, Grade, Teacher Comment

\- "Save Subjects" button → calls `reportCards.setSubjects(id, subjects)` → reloads



\*\*Delivery view (shown when "View Deliveries" is clicked):\*\*

\- Counts: Total Parents, Delivered, Acknowledged

\- Delivery table: Parent ID, Delivered At, Acknowledged At, Via, Admin Ack button

\- "Back to list" button



\### Task 9 — Wire routing + sidebar



`App.jsx`: add `import ReportCards from "./pages/ReportCards"` and

`<Route path="report-cards" element={<ReportCards />} />`.



`Layout.jsx`: add to NAV after Permissions:

```jsx

{ to: "/report-cards", label: "Report Cards", icon: ReportCardIcon }

```



```jsx

function ReportCardIcon() {

&#x20; return (

&#x20;   <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">

&#x20;     <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}

&#x20;       d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />

&#x20;   </svg>

&#x20; );

}

```



\## Guardrails



1\. \*\*One card per student per term\*\* — `create\_report\_card` raises `ValueError` on

&#x20;  duplicate `(student\_id, academic\_term)`. The UNIQUE constraint is the DB-level guard;

&#x20;  the service check is the application-level guard.



2\. \*\*Publish is one-way\*\* — once published, status cannot go back to draft. The publish

&#x20;  endpoint raises HTTP 400 if `status != "draft"`.



3\. \*\*Fan-out uses delivery rows\*\* — `publish\_report\_card` creates all `ReportCardDelivery`

&#x20;  rows synchronously. The Celery task reads those rows and sends notifications. This

&#x20;  means even if the task retries, the parent list is fixed at publish time.



4\. \*\*Interrupt ordering\*\* — permission slips interrupt first, report cards second. A parent

&#x20;  who has both a pending slip and an unacknowledged report card will see the slip first.

&#x20;  After they respond, the next message shows the report card. This chains naturally.



5\. \*\*Parent refetch optimisation\*\* — the permission slip interrupt already fetches `\_parent`

&#x20;  from the DB. The report card interrupt must reuse `\_parent` (already in scope) rather

&#x20;  than issuing a second SELECT. Refactor both interrupts to share a single parent lookup

&#x20;  block at the top.



6\. \*\*`format\_report\_card\_message` is pure\*\* — no DB access. Takes the fully loaded

&#x20;  ReportCard object (with subjects eager-loaded) and returns a string. Subjects are

&#x20;  sorted by `sort\_order` then `subject\_name`.



7\. \*\*Verify Vite build\*\* — run `npm run build` in `admin-dashboard/` and confirm zero

&#x20;  errors before reporting complete.

