# Manual Coverage Catalog

Use this catalog while building the inventory. Mark an item `N/A` only with a product-specific reason and reviewer acceptance; do not use `N/A` for missing access, credentials, devices, or time.

## Surface inventory

- All applications: web, mobile, desktop, admin, public site, embedded surfaces, and background workers with user-visible outcomes.
- All environments and supported device/browser/OS combinations.
- All roles, account states, subscriptions/plans, permissions, tenants, organizations, groups, and ownership boundaries.
- All routes: menus, tabs, nested routes, deep links, notification links, shared links, redirects, legacy aliases, 404/expired links, and browser/app back paths.
- All screens: loading, skeleton, empty, populated, partial, stale, error, offline, permission denied, disabled, archived, deleted, and first-use states.
- All overlays: dialogs, sheets, drawers, menus, popovers, tooltips, snackbars/toasts, pickers, and confirmation prompts.

## Control inventory

- Buttons, icon buttons, links, floating actions, list/grid rows, cards, tabs, breadcrumbs, pagination, pull-to-refresh, infinite scroll, and swipe actions.
- Inputs, password reveals, search, filters, sorting, selectors, date/time pickers, toggles, radios, checkboxes, sliders, editors, mentions, and autocomplete.
- Submit, save, draft, publish, archive, restore, duplicate, reorder, approve, reject, assign, export, import, print, share, copy, refresh, retry, cancel, close, and logout.
- Upload, camera, gallery, audio/video playback, seek, speed, captions, fullscreen, download, open, delete, replace, and failed transfer recovery.
- Keyboard submit/cancel, focus traversal, shortcuts, Android/iOS/browser back, escape, gestures, double taps, and rapid repeated activation.
- Disabled controls and their enabling conditions, destructive controls and confirmations, unsaved-change prompts, optimistic state, and rollback.

## Data and integration inventory

- Every read endpoint, mutation endpoint, websocket/channel event, push notification, queued job, scheduled task, mail/SMS, file-storage operation, and third-party integration.
- Authentication, registration/invitation, verification, password reset, MFA if present, session refresh/expiry, logout, revocation, device binding, and disabled accounts.
- Create/read/update/delete plus lifecycle transitions, bulk operations, idempotency, retry, concurrent updates, stale state, and conflict resolution.
- Server validation, client validation, status/body contract, null/missing/extra fields, Unicode/Arabic, large values, boundary dates, time zones, currencies, and rounding.
- Search, sort, filter combinations, pagination edges, empty last pages, duplicate items, cache invalidation, and refresh/relaunch persistence.
- Cross-role and cross-tenant visibility and mutation denial through both UI and direct API paths.

## Static and fake behavior inventory

- Hardcoded hosts, credentials, IDs, business values, dates, prices, totals, chart points, user names, images, and API responses.
- Mock/demo/sample/fixture/fallback arrays and objects in active builds.
- Placeholder copy or fake success presented as functional behavior.
- No-op, null, logging-only, local-only, delayed-fake, random, swallowed-error, and unconditional-success handlers.
- UI rendered without required server props/providers, disconnected controls, dead routes, retired endpoints, duplicate/shadowed routes, and unreachable features.
- Debug controls, test accounts, bypasses, insecure defaults, verbose exceptions, and sensitive logs.

## Experience and resilience inventory

- Phone/tablet/desktop breakpoints, orientation, safe areas, zoom, text scaling, long translations, RTL/LTR, light/dark/high-contrast modes.
- WCAG AA contrast, semantics/names, focus visibility/order, keyboard-only operation, screen reader output, and reduced motion.
- Slow network, offline, DNS/TLS failure, timeout, 4xx/5xx, malformed response, interrupted upload/download, background/foreground, restart, low storage, and denied permissions.
- Duplicate submit, rapid navigation, concurrent sessions, session expiry mid-flow, partial success, crash recovery, and retry without duplicate effects.
- Startup and critical-flow performance, memory/crash logs, monitoring/alert evidence, migration safety, backup/restore, queue/scheduler health, and rollback readiness.
