# EduConnect AI — Project Instructions

## Secrets

Treat secrets as radioactive. Never read, cat, print, echo, log, or paste the
contents of `.env`, `.env.*`, or any file containing credentials. Never output
the literal value of an API key, token, password, connection string, or secret,
even while debugging. Refer to every secret by its variable NAME only (for
example `PAYSTACK_SECRET_KEY`), and in code always read it via
`settings.<NAME>` (see `app/config.py`), never inline the value. If you think
you need a secret's value to proceed, stop and ask instead of revealing it.

Secrets live in three places and nowhere else:

- **Locally** — `.env` at the repo root (gitignored). `.env.example` holds the
  variable names with placeholder values and is the only env file committed.
- **Production (API)** — Railway project → Variables.
- **Production (dashboard)** — Cloudflare Pages → Environment variables.

The admin dashboard is a **Vite** app, so any variable prefixed `VITE_` is
baked into the public JavaScript bundle and readable by every visitor. Only
non-secret configuration may carry that prefix. Today the only one is
`VITE_API_URL`. Never add a secret behind `VITE_`.

If a secret is ever exposed — in a bundle, a commit, a log, a screenshot, or a
chat transcript — rotate it in the provider's dashboard. Deleting it from
`.env` does nothing, because the leaked copy still authenticates.

## Working on this codebase

- Don't refactor working code as a side effect of an unrelated change. Fix the
  thing that was asked for.
- Identity for parents comes from the verified chat ID on the webhook, never
  from a value the user typed or a model supplied. Anything that reads or
  writes a parent's data must be scoped to that verified identity — see
  `IDENTITY_SCOPED_TOOLS` in `app/services/ai_service.py` and
  `get_invoice_by_number_for_parent` in `app/services/billing_service.py` for
  the established pattern.
- Admin API routes need two gates: authentication (`get_current_user`) and,
  for anything sensitive or destructive, a role check (`require_role`).
  Financial reads require `finance`; administrative writes require `admin`.
- Routes with nested IDs (`/plans/{plan_id}/installments/{inst_id}`) must
  verify the child actually belongs to the parent before mutating it.
