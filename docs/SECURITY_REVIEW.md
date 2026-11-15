# The Baseline Society — Security, Consistency & Resolution Review (SECURITY_REVIEW.md)

**Review date:** November 2026
**Scope:** the 16 documentation files supplied (README, PRD, DESIGN, ARCHITECTURE, DATABASE, API, AUTH, AGENTS, FEATURES, INTEGRATIONS, MCP, PLAN, SETUP, DEBUGGING, RULEBOOK, new_features) and the code snippets embedded in them.

> **Important limitation:** no source code, tests, or configuration files were provided, so `ruff`, the 82-test suite, and the real implementation could not be run or inspected. Findings come from the specifications and the code excerpts in them. Every item marked **Verify** must be confirmed against the repository (`flask routes`, `app/domain/models.py`, `app/web/controllers/auth.py`, `config.py`). Findings describe what the documents say; fixes are written into the updated documents as required behavior, not as proof that the code has changed.

---

## 1. Security Findings

Severity: **High** = exploitable authorization/credential weakness; **Medium** = significant hardening gap; **Low** = best-practice gap.

| ID | Sev | Finding | Evidence | Fix (applied to docs) | Verify in code |
| :--- | :---: | :--- | :--- | :--- | :--- |
| S-01 | High | **Fail-open authorization.** In `check_tournament_access`, `min_ranks.get(min_role, 0)` and `role_ranks.get(role, 0)` default to 0, so an unknown `min_role` (for example `"scorer"` as AUTH.md calls it) lets any staff row pass. A delegated `tournament_admin` (rank 4) also satisfies `min_role="owner"`, so staff can appoint more staff. | ARCHITECTURE §5.2 vs AUTH §4.1 | Fail-closed guard, `ValueError` on unknown role, owner-only operations unreachable by staff (AUTH §4.1, ARCH §5.2) | Yes |
| S-02 | High | **Role vocabulary mismatch.** DATABASE/AUTH use `manager`/`official`/`scorer`; ARCHITECTURE/API/PRD/RULEBOOK/DEBUGGING use `tournament_admin`/`desk`/`umpire`. Staff rows with DB-documented roles rank 0. | DATABASE §2.18 vs ARCHITECTURE §5.2 | Canonical roles + alias table + data migration + CHECK constraint (DATABASE §4) | Yes (**decide canonical set**) |
| S-03 | High | **Court PIN weaknesses.** Tournament-wide 4-digit PIN (10,000 values), plain comparison, no rate limit, no expiry, session not bound to a court, so a PIN holder can score any match. Docs disagree (4-digit tournament column vs 6-digit per-staff row). | ARCH §6.2, PRD §10.2, new_features §5 vs AUTH §2.3, DATABASE §2.18 | Court PIN v2: 6-digit, HMAC-hashed, expiring, court-bound, rate-limited, session regenerated, scoring-only (AUTH §2.3) | Yes |
| S-04 | High | **Conflict-of-interest guard is incomplete.** Reads `participant.user_id`, a column that does not exist; doubles and team checks are comments; the example returns a tuple that callers can ignore (fail-open); PIN sessions have no identity; superadmin bypass unaudited. | ARCH §5.3 vs DATABASE §2.4 | Guard raises 403 and resolves via `Player.user_id`, partner, team roster, rubber lineup, parent tie; PIN compensating controls (AUTH §3.1) | Yes |
| S-05 | High | **Draft draws and private data can leak through public endpoints.** Public endpoints (`/matches/category/<id>`, `/tournaments/<slug>/categories/<id>`, live feed) have no `draw_published` gate in the spec; `ParticipantSchema` exposes `payment_status`, `checked_in`; `UserSchema` includes `email`; `is_private` tournaments are not filtered. | API §3, §4 vs ARCH §5.5 | Draft-draw guard on API and live feed, separate public/staff schemas, visibility rules (API §3, §4.2, §4.3, §4.4) | Yes |
| S-06 | High | **Default credentials and secrets.** `adminpassword` and `dev-secret-key-change-in-production` are documented defaults; bootstrap runs when `User.count()==0` on every cold start (race on serverless; no production guard). | AUTH §6, SETUP §3.1 | Production startup validation; bootstrap only when no superadmin exists; pipeline-time bootstrap (AUTH §6, SETUP §3.2) | Yes |
| S-07 | High | **Atomicity of optimistic locking.** "Verify version, then update" is a check-then-act race; `lock_version` is described as something clients "should" send, so omitting it may skip the check. | ARCH §5.4, API §2 | Mandatory field (400 if missing), atomic `UPDATE ... WHERE lock_version`, or `version_id_col` (AUTH §3.2, ARCH §5.4) | Yes |
| S-08 | Medium | **Realtime plan conflicts with hosting.** Flask-SocketIO needs persistent connections; Vercel serverless cannot hold them. | PLAN WP 2.1, new_features, INTEGRATIONS §3 | Three-option decision table; polling + CDN recommended now (ARCH §7) | Decision needed |
| S-09 | Medium | **JWT policy gaps.** No stated expiry, refresh, revocation, algorithm pinning, or separate signing secret; role may be trusted from claims. The guard uses Flask-Login `current_user`, which does not see a JWT identity, so API calls may be denied or mis-authorized. | API §2, ARCH §5.2 | Token policy, per-request user reload, explicit `user=` parameter (API §2.1, AUTH §4.1) | Yes |
| S-10 | Medium | **No rate limiting or brute-force protection** on login, registration, PIN, guest registration, or the live feed (5-second polling by every spectator). | AUTH, API, PRD §9 | Limits table with shared storage, `429`, CDN cache and ETag (AUTH §9, API §5, §4.4) | Yes |
| S-11 | Medium | **Guest registration and account claiming.** Linking history by matching unverified email/mobile enables account takeover and profile data exposure; all guests share the `anonymous_registrations` user (must be non-loginable). | FEATURES §2.6, PRD §7.1 | Verified-contact claiming; non-loginable shared account; no profile data shown to guests (AUTH §10, FEATURES §2.6, PRD §7.1) | Yes |
| S-12 | Medium | **Uploads in `app/web/static/uploads/`.** Public by default, stored-XSS risk (SVG/HTML), path traversal risk, and the filesystem is read-only on Vercel. | DATABASE §2.7, new_features | Object storage, allow-list, size cap, random names, signed URLs (AUTH §11, DATABASE §4 #9) | Yes |
| S-13 | Medium | **PDF HTML injection / SSRF.** `xhtml2pdf` renders HTML containing user-supplied names; remote resource fetching must be blocked. | INTEGRATIONS §4 | Escape, local-only `link_callback`, local TTF fonts (INTEGRATIONS §4.4, ARCH §3.4) | Yes |
| S-14 | Medium | **Spreadsheet formula injection and unsafe import** (`openpyxl`). | INTEGRATIONS §5 | Neutralize `= + - @`, read-only import, size/row limits, audit (INTEGRATIONS §5) | Yes |
| S-15 | Medium | **Cookies, headers, proxy trust.** `Secure` only "over HTTPS", no CSP/HSTS/frame protections, no `ProxyFix`, external Google Fonts, open-redirect risk on `next`. | AUTH §5, ARCH §7 | `SESSION_COOKIE_SECURE` in production, Talisman headers, `ProxyFix`, self-hosted fonts, relative-only `next` (AUTH §5, ARCH §5.8, DESIGN §3) | Yes |
| S-16 | Medium | **Incorrect hashing statement.** Docs say PBKDF2-HMAC-SHA256 with 260,000 iterations; Werkzeug 3.x defaults to scrypt. No password policy or rehash-on-login. | AUTH §5, DATABASE §2.8 | Corrected text, explicit method, policy, 128-character cap, rehash (AUTH §5) | Yes |
| S-17 | Medium | **MCP server risk.** Runs as local superadmin, accepts any `DATABASE_URL` (could be production), `sync_database_schema` defaults to `dry_run=false`, diagnostics run subprocesses, tool output includes user text (prompt injection). | MCP §2, §3.9, §5 | Read-only default, production gating, real actor identity, confirmations, injection defenses (MCP §5) | Yes |
| S-18 | Medium | **Audit gaps.** Score changes, PIN actions, publishes, failed logins not required in the audit log; `audit_logs.user_id` is NOT NULL so PIN actions cannot be logged. | AUTH §8, DATABASE §2.13 | Expanded audit scope, nullable `user_id`, actor fields, append-only (AUTH §8, DATABASE §4 #7) | Yes |
| S-19 | Medium | **Payment integrity.** `participants.payment_status` defaults to `'paid'`; UPI `transaction_id` is not unique; webhook controls unspecified. | DATABASE §2.4, §2.14, INTEGRATIONS §6 | Default `'pending'`, unique partial index, signature/idempotency/amount reconciliation (DATABASE §4, INTEGRATIONS §6.2) | Yes |
| S-20 | Low | **Personal data of minors.** Date of birth, address, blood group, and contact stored; public portfolio route may expose them; DPDP Act duties apply to children's data. | DATABASE §2.9, new_features | Data classification, public schema rules, consent/retention/deletion (AUTH §12, DATABASE §4.2) | Yes; legal review |
| S-21 | Low | **Credential handling guidance.** Guide suggests SendGrid "Full Access" key and offers to share keys with an assistant. | new_features | Restricted keys, secret store, never paste keys into chats (new_features, INTEGRATIONS §8) | No |
| S-22 | Low | **PDF ETag computed from PDF bytes** cannot save CPU (the PDF is already rendered); `304` must come after authorization. | INTEGRATIONS §4.2, ARCH §3.4 | Version-stamp ETag before rendering (INTEGRATIONS §4.2) | Yes |
| S-23 | Low | **`datetime.utcnow` is deprecated** in Python 3.12; naive datetimes. | AGENTS §2.4, DATABASE | Use `datetime.now(timezone.utc)` (AGENTS §2.4, DATABASE §4 #13) | Yes |
| S-24 | Low | **Schema hygiene.** `tournaments.user_id` nullable; unique constraint ineffective when `category_id` is NULL; no `ON DELETE` rules; no index list; `court_names` stored as "JSON or comma-separated". | DATABASE | Proposed hardening and index table (DATABASE §4, §4.1) | Yes |
| S-25 | Low | **Postgres driver selection.** Only `postgres://` is rewritten to `postgresql+psycopg://`; a plain `postgresql://` URL (as in SETUP) selects psycopg2. | INTEGRATIONS §2.2, SETUP §4.2 | Normalize both prefixes (INTEGRATIONS §2.2, DEBUGGING §2.4) | Yes |
| S-26 | Low | **`sync_db_schema.py` cannot enforce constraints.** It adds only missing tables/columns, so constraint and default fixes need Alembic. | DATABASE §3.2 | Documented limitation (DATABASE §3.3) | No |

---

## 2. Documentation Inconsistencies Fixed

| ID | Inconsistency | Resolution |
| :--- | :--- | :--- |
| D-01 | Test count: 72+ (AGENTS), 72 (MCP, PLAN Phase 1), 82 elsewhere | 82 everywhere; PLAN states 72 at Phase 1 close |
| D-02 | Table count: 17 (AGENTS, DATABASE) vs 18 (README, actual list) | 18 |
| D-03 | Staff roles: `manager/official/scorer` vs `tournament_admin/desk/umpire` | Canonical + alias table (see S-02) |
| D-04 | Court PIN: 4-digit tournament column vs 6-digit staff-row PIN | Court PIN v2 (see S-03) |
| D-05 | Routes: `/t/<slug>/...` vs `/tournaments/<slug>/...` | `/tournaments/<slug>/...` |
| D-06 | Lineup lock: 15 minutes before start (AUTH) vs on `in_progress` (ARCH) | Earlier of the two |
| D-07 | DEBUGGING decision tree pointed to wrong sections | Tree rebuilt and extended |
| D-08 | README said DESIGN.md has "dark-mode tokens" | Single light theme described |
| D-09 | Absolute `file:///Users/...` links and a local path in MCP config | Relative links and placeholder path |
| D-10 | `FLASK_ENV` (removed in Flask 2.3+) | `FLASK_DEBUG` and `APP_ENV` |
| D-11 | API envelope described with `data`, but examples use top-level keys | Envelope text matches examples; live feed noted as legacy (**Verify against code**) |
| D-12 | Final-rank semantics: "3" vs "3-4" vs "5-8" | Stored 3 (tied); "3-4"/"5-8" are display labels (**Verify**) |
| D-13 | Five tiers (A-E) but rubbers use only A to D | Tier E documented as reserve (**confirm intent**) |
| D-14 | Manual paths (`USER_MANUAL.md` vs `docs/...`) and README badge `../tests/` | `docs/` paths; badge fixed |
| D-15 | "Last Updated" dates mixed Oct/Nov | November 2026 for edited files |
| D-16 | Mobile "app" wording for a mobile web experience (RULEBOOK) | "mobile web experience" |
| D-17 | LCP targets differ (PRD 1.2 s vs DESIGN 2.5 s) | Both stated with context |
| D-18 | Naming: product was The Baseline Society while design system/logo said "The Baseline Society" | Product renamed to The Baseline Society in all prose; technical identifiers kept (see README note) |
| D-19 | `AGENTS.md` snippet used legacy `User.query.get` and hand-written ownership checks | SQLAlchemy 2.0 idiom and central guard |

---

## 3. Resolution & Responsive Coverage

| ID | Gap | Resolution |
| :--- | :--- | :--- |
| R-01 | DESIGN.md claimed mobile-first `min-width` breakpoints (480/768/1024/1280) but the shipped CSS is desktop-first (`max-width` 640/768) | DESIGN §7.1 now documents the real convention and a full tier matrix |
| R-02 | Tablet portrait (641 to 1023 px) had no defined behavior | Defined in DESIGN §7.1, ARCH §8.4, FEATURES §2.8.1 (marked as needing tests) |
| R-03 | Phone range stated as 320 to 430 px; current large phones are about 440 px wide | Extended to 480 px |
| R-04 | Landscape phones, 200 % zoom, large system text not covered | Added to DESIGN §7.1, §7.11, PRD §9.4 |
| R-05 | Venue TV / large display (PLAN WP 2.3) had no resolution spec | DESIGN §10 and PLAN WP 2.3 |
| R-06 | `dvh`/`svh` used without fallback | `vh` fallback rule added |
| R-07 | Mobile button sizes written as base styles (would regress desktop) | Wrapped in `@media (max-width: 640px)` |
| R-08 | Web fonts cannot render in PDFs; Google Fonts hurt CSP/privacy | Self-hosted WOFF2 plus TTF registration for PDFs |
| R-09 | No forced-dark-mode protection for a light-only theme | `color-scheme` meta and CSS rule |
| R-10 | PRD lacked accessibility target | WCAG 2.2 AA added |

---

## 4. Code-Review Notes on Embedded Snippets

1. `check_tournament_access` returns a tuple on success but `abort(403)` on failure and reads `session` and `current_user`; it cannot serve JWT callers unless the user is passed in. Unused parameter `write_required`. (Fixed in doc: explicit `user`, string return.)
2. `check_scoring_conflict_of_interest` returns `(bool, msg)` while docs say it "returns 403". Mixed contracts are a silent-bypass risk.
3. Sequence diagram 6.2 stores the PIN-authorized court in the session, but no later step compares it with `match.court_name`.
4. `make_pdf_response` hashes bytes, accepts `If-None-Match` as a single value only (weak or multi-value ETags ignored), and does not check authorization before a `304`.
5. `SQLALCHEMY_ENGINE_OPTIONS` are defined only inside the PostgreSQL branch; keep that, but ensure `DATABASE_URL` normalization runs before the `startswith('postgresql')` test.
6. `bootstrap_superadmin()` using `User.query.count() == 0` is racy and does not recover when ordinary users exist without a superadmin.
7. Public live-feed polling (5 s) multiplied by spectators needs caching; the PRD's 60 ms target is for origin latency and is only realistic with caching and indexes.

---

## 5. Not Verifiable From the Documents (please check)

- Actual enum values stored in `tournament_staff.role` and whether legacy values exist in production data.
- Whether `Tournament.court_pin` still exists in code or migrations.
- Whether `participants` has a `user_id` column (the schema says no; the snippet uses it).
- Real route names (`flask routes`) and the `/t/...` vs `/tournaments/...` question.
- Whether the API wraps payloads in `data` or returns top-level keys.
- The actual CSS media queries and the `final_rank` values stored.
- `TESTING.md` and `USER_MANUAL.md` were referenced but not supplied, so they were not reviewed or updated.

## 6. Recommended Order of Work
1. S-01 to S-04 and S-06 (authorization, PIN, default credentials), with the regression tests listed in AUTH §13.
2. S-05, S-07, S-09, S-10 (public data gating, atomic locking, JWT, rate limits).
3. S-08 decision, then S-11 to S-19.
4. Remaining Low items, then run `bandit`, `pip-audit`, `ruff`, and the full test suite.
