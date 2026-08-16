---
name: production-qa-gate
description: Execute an evidence-backed, end-to-end manual production-readiness audit of an entire product. Use whenever Codex or another agent is asked to test, QA, validate, accept, release, ship, certify, or call a web/mobile/desktop product production-ready; when asked to inspect every screen, route, button, control, user role, frontend-backend integration, real-data behavior, static/mock/placeholder content, or complete system quality; and after broad feature work where release confidence is requested. Unit, widget, integration, or automated tests may supplement this skill but never replace its physical/manual workflow.
---

# Production QA Gate

Treat production readiness as a proof obligation. Do not infer a pass from source code, automated tests, a successful build, an HTTP health check, another agent's summary, or a partial walkthrough.

Use `assets/coverage-matrix.csv`, `assets/defects.csv`, and `assets/production-qa-report.md` as the run ledger. Read [manual-coverage-catalog.md](references/manual-coverage-catalog.md) before inventorying the system. Run `scripts/validate_qa_evidence.py` before any final readiness claim.

## Non-negotiable rules

1. Test the real runnable product manually on every supported client and representative device class. Use browser/device control, not source inspection alone.
2. Discover the complete surface before testing: clients, roles, permissions, routes, screens, dialogs, sheets, tabs, menus, controls, gestures, background jobs, integrations, and lifecycle states.
3. Create one coverage row for every meaningful role × platform × screen × state × control/action combination. Split rows whenever actions can fail independently.
4. Exercise every reachable control one by one, including controls below the fold, overflow menus, keyboard actions, gestures, back navigation, deep links, retries, refresh, uploads, downloads, and destructive confirmations.
5. Prove the full integration chain for each data-backed action: UI action → request/event → auth and validation → backend handler → persistence or side effect → response → rendered state → refresh/relaunch persistence.
6. Use real API-backed test data. Treat silent mock fallbacks, hardcoded business values, placeholder statistics, canned lists, fake success, no-op callbacks, and locally fabricated server data as release blockers unless the product explicitly labels them as demo/sample content.
7. Capture evidence at the time of execution. A claim written later without traceable evidence is `UNTESTED`.
8. Test happy, empty, loading, validation, permission-denied, failure, timeout/offline, retry, duplicate-submit, and recovery states wherever applicable.
9. Test every supported role with its own credentials and authorization boundaries. A successful owner/admin path does not cover assistant, student, parent, guest, or other roles.
10. Never convert `BLOCKED`, `UNTESTED`, `NOT RUN`, an unavailable credential/device, or an unexplained skip into `PASS`.
11. Never say “all buttons,” “fully tested,” “bug-free,” or “production-ready” unless the ledger and validator prove the exact claim. State the tested scope and residual uncertainty explicitly.
12. Do not mutate production data destructively or weaken security to enable QA. Prefer an isolated production-like environment and disposable fixtures. If live production testing is explicitly authorized, use reversible, scoped records and clean them up with evidence.

## Execute the workflow

### 1. Establish the test baseline

- Record repositories, branches, commit hashes, build identifiers, environment, API base URL, database engine, feature flags, devices, OS/browser versions, locale, time zone, and run timestamp.
- Confirm which deployed backend and frontend builds are actually under test. Do not mix local source conclusions with a different deployed release.
- Record the supported role matrix and obtain valid, least-privilege QA credentials without writing secrets into reports, logs, source, or memory.
- Start from a clean install/profile where relevant, then also test upgrade/preserved-state behavior when the product supports upgrades.
- Run health, migration, queue, cache, storage, realtime, mail/SMS/push, scheduler, and third-party dependency checks applicable to the product.

### 2. Build the authoritative inventory

Triangulate, rather than trusting one source:

- Enumerate routes/screens from runtime navigation, router declarations, menus, deep links, notifications, and role-gated entry points.
- Enumerate backend endpoints from route definitions and runtime network traffic. Resolve duplicate/shadowed routes by proving which handler executes.
- Enumerate interactive controls from the rendered UI and semantics/accessibility tree, then compare with source to find hidden, conditional, or unreachable controls.
- Enumerate server-driven states from models, API contracts, fixtures, database relationships, and business rules.
- Add each item to the coverage matrix before execution. Keep discovered items; never shrink the inventory merely to make the gate pass.

### 3. Prepare deterministic real data

- Create a minimal, traceable fixture set covering every role, permission boundary, relationship, lifecycle status, empty state, populated state, pagination boundary, validation boundary, and business transition.
- Mark each fixture with a run identifier. Record creation and cleanup methods without recording credentials or sensitive personal data.
- Ensure one role cannot see or mutate another tenant/owner/user's records unless the specification allows it.
- Verify timestamps, locale, currency, RTL/LTR, media, file storage, and notification data where used.

### 4. Execute screen by screen and control by control

For each role and platform:

1. Open the screen through every supported entry path.
2. Capture the initial loading-to-final transition and compare it with the backend response.
3. Scroll the complete surface and open every menu, tab, dialog, sheet, tooltip, filter, selector, and expandable region.
4. Activate one control at a time. Record expected result, observed result, and evidence.
5. For mutations, record the request/response, verify the exact persisted backend state independently, refresh, leave and return, then relaunch when persistence is expected.
6. Repeat with invalid, unauthorized, empty, duplicate, offline/timeout, server-error, and recovery conditions as applicable.
7. Verify navigation stack, Android/iOS/browser back behavior, cancellation, unsaved changes, keyboard/focus, double taps, rapid repeat taps, and concurrent changes.
8. Verify responsive layouts, text scaling, RTL/LTR, contrast, semantics/labels, focus order, and screen-reader discoverability for critical flows.
9. Mark the row `PASS` only when observed behavior matches the expected behavior and evidence is present. Otherwise use `FAIL`, `BLOCKED`, or `UNTESTED`.

Do not batch several buttons into one generic row or claim. Controls sharing a screen require separate rows when they trigger distinct navigation, requests, validation, or state changes.

### 5. Prove frontend-backend integration

For every data-bearing read and mutation, correlate a unique marker such as a request ID, fixture ID, timestamp, or record ID across:

- rendered input/output;
- request method, canonical URL, headers/auth context, and payload;
- actual resolved backend route and handler;
- validation and authorization outcome;
- database/storage/queue/realtime/third-party side effect;
- response status and contract;
- client parsing, state management, displayed result, and persistence after refresh/relaunch.

Reject these false positives:

- UI success message while the request failed or never fired;
- HTTP 200 with an error body or ignored `success: false`;
- client updates that disappear after refresh;
- a correct endpoint tested directly while the UI calls a different/legacy endpoint;
- a route existing in source but shadowed by an earlier duplicate registration;
- an owner token masking assistant/student/parent authorization defects;
- cached or fallback data masking server failure.

### 6. Audit static, mock, placeholder, and dead behavior

Perform both a source scan and a runtime proof. Search active code/config/build artifacts for:

- mock, fake, dummy, sample, demo, fixture, fallback, placeholder, TODO, WIP, coming soon;
- hardcoded API hosts, tokens, user IDs, record IDs, prices, counts, charts, dates, and business copy presented as live data;
- inline arrays/objects used when server props are missing;
- delayed fake loading, random success, swallowed errors, empty catches, and unconditional success messages;
- `onPressed`/`onTap`/submit handlers that are null, empty, log-only, or local-state-only for server-backed actions;
- routes/screens rendered without the props or providers they require;
- retired endpoints and duplicate registrations;
- debug menus, bypasses, insecure defaults, and development credentials.

Then force the backend data to a unique recognizable value and verify the UI shows it; change it through the UI and verify persistence. Record every match and its disposition. Static labels, legal copy, design tokens, and explicitly labeled demo/sample content are allowed; unlabeled business data or fake behavior is not.

### 7. Verify production qualities

- Authentication, session expiry, logout/revocation, password reset, device binding, and account state changes.
- Authorization and cross-role/cross-tenant isolation on both UI and direct API paths.
- Validation parity and safe error messages; no stack traces, secrets, or personal data leakage.
- Network interruption, retry, idempotency, double submit, concurrency, stale data, and conflict behavior.
- Pagination, search, sorting, filters, large/empty datasets, boundary values, Unicode/Arabic, and time-zone boundaries.
- Media/file upload limits, type validation, cancellation, storage retrieval, and cleanup.
- App restart, background/foreground, token expiration, deep links, notifications, and interrupted workflows.
- Critical performance, crash-free operation, logs, monitoring, backups/restore evidence, migrations, queues, and scheduled work appropriate to the release.

Automated suites, linters, type checks, build checks, security scans, and backend tests are mandatory supporting evidence when available, but they never substitute for the manual matrix.

### 8. Fix, retest, and regress within authorization

- If the request authorizes implementation, reproduce each defect, identify the root cause, implement the smallest safe fix, and rerun the failed row plus adjacent, role, backend-contract, persistence, and regression coverage.
- If the request authorizes diagnosis/review only, do not modify the product. Record the defect and exact reproduction evidence.
- Never close a defect from source reasoning alone. Link it to passing retest rows and a build/commit containing the fix.
- Rebuild and reinstall/redeploy before retesting whenever the changed layer requires it.

### 9. Enforce the release gate

Run:

```bash
python3 /path/to/production-qa-gate/scripts/validate_qa_evidence.py \
  /path/to/coverage-matrix.csv /path/to/defects.csv
```

Declare `PRODUCTION READY` only when all of the following are true:

- the inventory is complete and reconciled across runtime, frontend source, and backend routes;
- every in-scope matrix row is `PASS` with expected result, observed result, and traceable evidence;
- no row is `FAIL`, `BLOCKED`, `UNTESTED`, or omitted because of unavailable access;
- every supported role, platform, screen, state, control, integration, and critical lifecycle path is covered;
- no prohibited static/mock/placeholder business behavior remains;
- all discovered defects are fixed and manually retested, with no open release-blocking issue;
- real UI-to-backend-to-persistence behavior is proven, including error and recovery states;
- required supporting automated checks pass on the same build;
- fixture cleanup, credential/token revocation, and environment restoration are evidenced;
- the validator exits successfully for both the coverage matrix and defect ledger, and the report names the exact tested build and limits.

If any condition is false, output `NOT PRODUCTION READY`. Name the precise gaps and the evidence/access needed to continue. Do not soften this status because most paths passed.

Absolute absence of defects cannot be proven. Report only that the enumerated scope passed the stated gate on the named build/environment.

## Evidence contract

Use stable IDs:

- `SCR-...` for screens/routes;
- `CTL-...` for controls/actions;
- `INT-...` for integration traces;
- `STA-...` for static/mock findings;
- `DEF-...` for defects.

Each coverage row must contain the columns required by `assets/coverage-matrix.csv`. Evidence must be directly inspectable: screenshot/video path or URL, runtime timestamp, device/browser, network trace/request ID, server/database proof for mutations, and cleanup proof where relevant. Redact tokens, passwords, cookies, personal data, and secrets.

Keep raw artifacts outside ephemeral locations when the result must survive the session. The final report must link to the coverage matrix, defect ledger, raw evidence directory, build/commit identifiers, commands and outputs, static-content audit, integration traces, cleanup proof, and validator output.

## Delegation contract

When multiple agents participate, require every agent to load this skill, assign non-overlapping matrix row IDs, and return raw evidence rather than a prose assurance. The coordinating agent must reconcile the master inventory, inspect evidence, rerun the validator, and retain responsibility for the final status. Never mark a row passed merely because another agent says it passed.
