# AI Agent Development Security Pipeline

A repeatable process for shipping AI-assisted code without shipping AI-assisted
vulnerabilities.

This exists because AI coding tools fail in a *predictable* way: they produce
code that satisfies the request and passes the obvious test, while silently
omitting the cross-cutting concerns nobody asked for. Authentication gets
scaffolded consistently; authorization does not. The happy path gets written;
the retry path does not. The feature works; the boundary is missing.

Every gate below targets one of those blind spots. The commands are written for
**this stack** — Python/FastAPI/SQLAlchemy + React/Vite — not the
TypeScript/Next/Supabase examples the source guides use.

---

## How to use this

| When | Run |
|---|---|
| Once, per repo | Stage 0 |
| Every task, before prompting | Stage 1 |
| Every task, before merge | Stage 2 gates that touch what you changed |
| Before deploy | Stage 3 |
| Monthly / on offboarding | Stage 4 |

A gate is either **PASS**, or it produces a finding with a file, a line, and a
concrete exploit sentence. "Looks fine" is not a result.

---

## Stage 0 — Repo guardrails (one-time)

These make the *next* mistake harder, and they cost nothing after setup.

### 0.1 Agent instruction file

`CLAUDE.md` at the repo root, loaded automatically into agent context. It must
contain, at minimum, the secrets rule:

```
Treat secrets as radioactive. Never read, cat, print, echo, log, or paste the
contents of .env, .env.*, or any file containing credentials. Never output the
literal value of an API key, token, password, connection string, or secret,
even while debugging. Refer to every secret by its variable NAME only. If you
think you need a secret's value to proceed, stop and ask.
```

Plus the invariants an agent cannot infer from the code:

- Where identity comes from (for us: the verified chat ID on the webhook, never
  user-typed input or model-supplied arguments).
- Which roles gate which class of action.
- Any rule that, if broken, is a security bug rather than a style disagreement.

### 0.2 Ignore rules

```bash
# Verify real env files are ignored and examples are NOT
for f in .env .env.local .env.production .env.staging .wrangler .env.example; do
  git check-ignore -q "$f" && echo "IGNORED  $f" || echo "tracked  $f"
done
```

Expected: everything ignored **except** `.env.example`. A bare `.env` line in
`.gitignore` is not enough — `.env.local` and `.env.production` slip through
without a `.env.*` wildcard plus a `!.env.example` negation.

### 0.3 Secret scanning

Enable GitHub secret scanning + push protection. It catches the leak the
pipeline misses.

---

## Stage 1 — Before you prompt

Cheap habits that prevent findings instead of detecting them.

**Name the boundary in the prompt.** Not "add an endpoint to cancel an
invoice" but "add an endpoint to cancel an invoice, callable only by finance
roles, verifying the invoice belongs to the requesting tenant."

**State the failure paths.** "Handle the webhook" produces the happy path only.
"Handle the webhook, including duplicate delivery, a refund event, and a
transient lookup failure that should trigger provider retry" produces all four.

**Ask for the check to be centralized.** Copy-paste drift is how gaps spread:
one route implements the ownership check correctly, three siblings scaffolded by
analogy do not. Ask for a shared helper.

**Never paste a secret into the prompt.** Refer to `PAYSTACK_SECRET_KEY`, never
its value. A key that touches a chat transcript is burned and must be rotated.

---

## Stage 2 — Pre-merge gates

Run the gates relevant to what changed. Each has a reusable agent prompt and a
mechanical check.

---

### Gate 1 — Endpoint authorization

**Bug class:** every route has an auth check, so review looks clean — but
nothing verifies *this user* may touch *this object*. Authentication is not
authorization.

**Mechanical check — list every route and its guard:**

```bash
python - <<'PY'
import ast, pathlib
AUTH = {"get_current_user", "require_role"}
def guard(fn):
    for d in fn.args.defaults + fn.args.kw_defaults:
        if d is None: continue
        for s in ast.walk(d):
            if isinstance(s, ast.Call) and isinstance(s.func, ast.Name):
                if s.func.id == "require_role":
                    return "require_role(" + ",".join(
                        a.value for a in s.args if isinstance(a, ast.Constant)) + ")"
                if s.func.id == "get_current_user": return "any-authenticated"
            if isinstance(s, ast.Name) and s.id == "get_current_user":
                return "any-authenticated"
    return ">>> NO GUARD"
rows = []
for f in sorted(pathlib.Path("app/api").rglob("*.py")):
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if not isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)): continue
        for d in n.decorator_list:
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) \
               and d.func.attr in ("get","post","put","patch","delete"):
                p = d.args[0].value if d.args and isinstance(d.args[0], ast.Constant) else ""
                rows.append((d.func.attr.upper(), p, guard(n), f.name, n.lineno))
# destructive first — highest impact
for m,p,g,fn,ln in sorted(rows, key=lambda r: (r[0] not in ("DELETE","PATCH","PUT"), r[3])):
    print(f"{m:7} {p:46} {g:44} {fn}:{ln}")
print(f"\ntotal routes: {len(rows)}")
PY
```

**Triage the output:**

- `NO GUARD` on anything state-changing → **critical**, unless it is a
  signature-verified webhook or deliberately public.
- `any-authenticated` on a destructive or sensitive route → check whether a
  sibling route on the same resource requires a role. Inconsistency between
  siblings is the tell for copy-paste drift.
- Nested IDs (`/plans/{plan_id}/installments/{inst_id}`) → the URL asserts a
  relationship. Confirm the code *verifies* it rather than looking the child up
  by its own ID alone.

**Agent prompt:**

```
Audit every API route that accepts an object ID for missing object-level
authorization. For each: (1) does it authenticate, and (2) SEPARATELY, does it
verify via a database lookup that the caller owns / is assigned to / has a role
right over THIS specific object before reading or mutating it? Flag routes with
gate 1 but not gate 2. Prioritize DELETE/PATCH/PUT. For routes with nested IDs,
confirm the child is verified to belong to the parent. Report file, line, and
the concrete exploit. Do not fix anything yet.
```

---

### Gate 2 — Identity provenance

**Bug class:** identity read from the request body, a URL parameter, or an LLM
tool argument instead of from the verified session. This is impersonation.

For agent-based apps this has a form the source guides don't cover: **the model
supplies the identity argument**. If a tool takes `user_id` or `phone` and the
dispatcher passes the model's arguments straight through, any user can ask the
assistant for someone else's data in plain language.

**Mechanical check:**

```bash
# Identity fields taken from a request body
grep -rnE "body\.(user_?id|email|role|phone)|data\.(user_?id|email|role)" \
  app/ --include="*.py"

# LLM tool dispatch — does the verified identity reach the handler?
grep -rn "\*\*tool_input\|\*\*args\|handler(" app/services/*ai* --include="*.py"
```

**The rule:** for any tool or endpoint scoped to a user, the identity must be
*injected server-side*, overriding anything the caller or model supplied — and
removed from the model-facing schema so it cannot be requested at all.

**Agent prompt:**

```
Find every place user identity (user id, email, phone, role) is read from a
request body, query string, URL path, or LLM tool argument rather than derived
from a verified session/token/webhook. For LLM tools specifically: trace whether
the verified identity reaches the tool handler, or whether the model's arguments
are passed through unmodified. Flag each as an impersonation risk with the
concrete exploit phrasing a user would type.
```

---

### Gate 3 — Payments and webhooks

**Bug class:** the money code is written for one successful non-concurrent
request. The bugs live in retries, duplicates, and refunds.

**Mechanical check:**

```bash
# Which provider events are actually handled?
grep -rn 'event ==\|event in\|"charge\.\|"refund\.' app/ --include="*.py"

# Refund / chargeback path exists at all?
grep -rniE "refund|chargeback|dispute|reversal" app/api app/services --include="*.py"

# Idempotency: is the guard inside the lock?
grep -n "with_for_update\|already\|_credited" app/services/billing_service.py
```

**The four questions:**

1. **Is idempotency a database guarantee or an application guess?** A
   check-then-act outside a transaction lock is a race. For an `INSERT`, use a
   `UNIQUE` constraint and catch the violation. For a read-modify-write
   (`amount_paid += x`), lock the row *before* reading the guard flag.
2. **Do the guard and the mutation share one lock?** Check the ordering: lock →
   check → mutate → set flag. A check above the lock is not a guard.
3. **Is there a refund path?** Granting on purchase without revoking on refund
   is pure loss. Alert-only is an acceptable first version; silence is not.
4. **Does a transient error look like "not applicable"?** Any `except: return
   None` that the caller treats as "skip and mark processed" turns a network
   blip into a customer who paid and got nothing, with no retry.

Also confirm signature verification runs on the **raw body**, before any JSON
parsing.

**Agent prompt:**

```
Audit payment and webhook handling for: (1) idempotency implemented as an
application-level check-then-act with no backing database constraint or row
lock — check whether the guard is read before or after the lock is acquired;
(2) error handling that collapses "this event doesn't apply to us" and "the
lookup failed" into the same silent skip; (3) missing refund/chargeback/dispute
handlers; (4) buyer resolution by secondary lookup (email) rather than an
identifier set at checkout; (5) signature verification on a parsed rather than
raw body. Report the concrete failure scenario for each.
```

**Do not skip the live test:** fire the same webhook payload twice in quick
succession against a test environment and confirm no double-grant. Static review
cannot prove this.

---

### Gate 4 — Secrets

**Bug class:** a credential reaches a browser bundle, a git commit, or a chat
transcript, because it was treated as configuration.

**Mechanical check — never prints values:**

```bash
# 1. Real credentials in the committed example file?
python - <<'PY'
import pathlib, re
REAL = {
 "stripe_live": re.compile(r'^sk_live_[0-9a-zA-Z]{20,}$'),
 "paystack":    re.compile(r'^sk_(live|test)_[0-9a-zA-Z]{20,}$'),
 "anthropic":   re.compile(r'^sk-ant-[0-9A-Za-z_\-]{30,}$'),
 "jwt":         re.compile(r'^eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.'),
 "aws":         re.compile(r'^AKIA[0-9A-Z]{16}$'),
 # Generic high-entropy: 32+ chars with BOTH letters and digits. The digit
 # requirement is what stops placeholder prose like
 # "your_app_secret_for_signature_verification" from matching.
 "entropy":     re.compile(r'^(?=[A-Za-z0-9+/=_\-]{32,}$)(?=.*[A-Za-z])(?=.*\d).*$'),
}
PLACEHOLDER = re.compile(
    r'your|change|placeholder|dummy|example|todo|xxx+|secret_for|replace', re.I)

for rel in [".env.example", "admin-dashboard/.env.example"]:
    p = pathlib.Path(rel)
    if not p.exists(): continue
    for i, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s: continue
        name, _, val = s.partition("=")
        val = val.split("#")[0].strip().strip('"\'')
        if not val or PLACEHOLDER.search(val): continue   # obvious placeholder
        hits = [k for k, r in REAL.items() if r.match(val)]
        if hits:
            print(f"LEAK  {rel}:{i}  {name.strip()}  matches {hits}")
print("scan complete — no output above means clean")
PY

# 2. Was a real .env ever committed?
git log --all --diff-filter=A --name-only --format="" | grep -iE "(^|/)\.env" | sort -u

# 3. Did a secret ship to the browser bundle?
cd admin-dashboard && npm run build >/dev/null 2>&1
grep -rlE "sk_live|sk_test|sk-ant-|service_role|-----BEGIN|AKIA[0-9A-Z]{16}" dist/ \
  || echo "bundle clean"

# 4. Any secret behind a PUBLIC prefix? (Vite ships every VITE_* to the browser)
grep -rnE "VITE_[A-Z_]*(SECRET|TOKEN|PASSWORD|PRIVATE|KEY)" . \
  --include="*.js" --include="*.jsx" --include="*.example" \
  || echo "no secret behind a public prefix"

# 5. Does .env.example match what the code actually reads?
python - <<'PY'
import ast, pathlib
cfg = ast.parse(pathlib.Path("app/config.py").read_text(encoding="utf-8"))
fields = [t.target.id for n in ast.walk(cfg)
          if isinstance(n, ast.ClassDef) and n.name == "Settings"
          for t in n.body
          if isinstance(t, ast.AnnAssign) and isinstance(t.target, ast.Name)
          and t.target.id.isupper()]
env = {l.split("=")[0].strip()
       for l in pathlib.Path(".env.example").read_text(encoding="utf-8", errors="replace").splitlines()
       if l.strip() and not l.strip().startswith("#") and "=" in l}
missing = [f for f in fields if f not in env]
print("undocumented vars:", missing or "none")
PY
```

> **Known limitation of the scanner above.** The placeholder filter keeps it
> quiet on your own `.env.example`, but it suppresses any value containing
> `your`, `change`, `example`, `dummy`, `todo`, or `replace` — so a genuine key
> that happens to contain one of those substrings will be missed. It is a noise
> filter, not a guarantee. Treat a clean scan as "nothing obvious," and rely on
> GitHub push protection (Stage 0.3) as the real net.

**The `VITE_` / `NEXT_PUBLIC_` rule:** these prefixes are an instruction to bake
the value into public JavaScript. Safe for a publishable key or an API URL.
Catastrophic for anything else. There is no un-shipping it.

**If a secret was exposed: rotate it.** Deleting it from `.env` does nothing —
the leaked copy still authenticates. Revoke in the provider dashboard.

---

### Gate 5 — Input and transport hardening

**Bug class:** the boring layer nobody prompts for.

```bash
# Unbounded string fields — memory and abuse surface
grep -rn ": str$\|: str | None = None" app/schemas/ --include="*.py" | head -30

# Is the login endpoint rate limited?
grep -n "limiter.limit" app/api/v1/auth.py || echo ">>> LOGIN NOT RATE LIMITED"

# Security headers + body size middleware registered?
grep -n "add_middleware" app/main.py

# Fail-closed check: does a missing secret disable verification, or reject?
grep -rn "if settings\..*SECRET:" app/api/ --include="*.py"
```

**Checklist:**

- [ ] Every free-text schema field has `max_length`.
- [ ] Login is rate limited (brute force) — separately from the global default.
- [ ] Security headers middleware registered (`X-Content-Type-Options`,
      `X-Frame-Options`, `Referrer-Policy`, HSTS).
- [ ] Request body size capped.
- [ ] Startup refuses to boot on a default/short `SECRET_KEY` in production.
- [ ] Webhook secret checks **fail closed** — a missing secret rejects the
      request rather than skipping verification.
- [ ] CORS lists explicit methods and headers, not `*`.

---

## Stage 3 — Pre-deploy

- [ ] Gate 4 run and clean.
- [ ] Production secrets set in the host panel (Railway / Cloudflare), not the
      repo. Mark write-once credentials **Sensitive** where the host supports
      it; leave human-readable config visible so you can audit it.
- [ ] `SECRET_KEY` is 32+ random chars. Generate:
      `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] Database backups / point-in-time recovery confirmed enabled.
- [ ] Migrations reviewed — a new `UNIQUE` constraint fails on existing
      duplicate rows. Check for duplicates *before* deploying it.
- [ ] Webhook endpoints reachable and signature-verifying in the target env.

---

## Stage 4 — Recurring

**Monthly:** re-run Gates 1 and 4. Gate 1 catches drift as routes are added;
Gate 4 catches a key that crept into a bundle.

**On offboarding:** rotate every shared credential. Access removal is not
credential rotation.

**Quarterly:** rotate high-value keys on schedule, not only on incident.

**On any exposure:** rotate immediately, then investigate. Order matters.

---

## Severity triage

Use this to decide what blocks a merge.

| Severity | Definition | Example from this repo |
|---|---|---|
| **Critical** | Unauthenticated access to data or destructive action; privilege escalation; financial loss | Unauthenticated `POST /telegram/setup` let anyone repoint the bot webhook |
| **High** | Authenticated but unauthorized cross-account access; money bugs; PII disclosure | AI tools accepted a model-supplied phone number, returning another family's children and payment history |
| **Medium** | Role drift; missing hardening with no direct exploit | Payment reads open to every admin role while equivalent billing routes required `finance` |
| **Low** | Defence in depth; documentation drift | `.env.example` missing three variables the code reads |

**Critical and High block the merge. Medium gets a ticket. Low gets batched.**

---

## Worked examples from this repo

Real findings, as calibration for what each gate catches.

| Gate | Finding | Why review missed it |
|---|---|---|
| 2 | LLM tools took `parent_phone` as a model argument; `_execute_tool` passed `**tool_input` straight through. Anyone messaging the bot could ask for another family's payment history and children's names. | The tool schema *looked* correct and the happy path worked — the caller's own number produced the right answer. |
| 1 | `PUT /plans/{plan_id}/installments/{inst_id}/pay` accepted `plan_id` and never used it. A mismatched pair silently mutated another plan's installment. | The URL asserted the relationship, so it read as verified. |
| 1 | `GET /admin/customer/{number}` returned full payment records to every admin role, bypassing the `finance` gate on `/payments/*`. The UI hid the tab, so it looked handled. | One endpoint aggregated data owned by another module's access rules. A single route guard can't express two sensitivity levels. |
| 3 | Invoice credit guard was read 11 lines *above* the row lock. Webhook and browser callback arrive together in normal operation — both could pass the check and each add the payment amount. | Sequential testing never reproduces it. Two guards existed and both looked sufficient. |
| 3 | Only `charge.success` was handled. A refund left the invoice marked paid, silently. | "Add checkout" never implies "handle the reverse." |
| 4 | `.gitignore` had `.env` but no `.env.*`, so `.env.production` was not ignored. | The common case was covered, which is what makes it easy to miss. |

The pattern across all six: **the feature worked, and the gap was in the path
nobody demonstrated.** That is what the gates are for.

---

## What this pipeline does not cover

Be honest about the edges:

- **Dependency vulnerabilities.** Add `pip-audit` and `npm audit` to CI.
- **Live concurrency.** Gate 3's race conditions need a real database and
  duplicate deliveries to prove. Static review only shows the ordering.
- **Infrastructure.** Database network exposure, TLS config, and host-level
  access are outside the repo.
- **Trust boundaries you inherit.** Identity here anchors on a chat ID from a
  signature-verified webhook. Spoofing at the carrier or provider level is
  outside what application code can defend.
- **Social engineering and insider misuse.** Role gates limit blast radius;
  they do not stop an authorized person acting in bad faith. Audit logs matter.
