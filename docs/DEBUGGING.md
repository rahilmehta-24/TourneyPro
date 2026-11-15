# The Baseline Society — Troubleshooting Playbook & Operational Diagnostics (DEBUGGING.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`TESTING.md`](TESTING.md), [`SETUP.md`](SETUP.md), [`DATABASE.md`](DATABASE.md), and [`ARCHITECTURE.md`](ARCHITECTURE.md)  
**Primary Audience:** Site Reliability Engineers (SRE), Backend Engineers & Technical Support Admins  
**Last Updated:** November 2026  

---

## 1. Quick Diagnostic Decision Tree

```
Encountered an Issue?
│
├── Database Connection / Pool Failure? ───────────► Section 2.1 (PgBouncer) and 2.2 (Quoted URL)
├── Missing Column / SQLite Schema Error? ─────────► Section 2.3 (Schema Sync Tool)
├── Wrong Postgres Driver (psycopg2 vs psycopg 3)? ► Section 2.4 (URL Normalization)
├── Match Progression Lock Rejection (400)? ───────► Section 3.1 (Feeder Match Checks)
├── Rubber Summation Score Error ($T=7$)? ─────────► Section 3.2 (Summation & Walkovers)
├── Player Rest Buffer Warning? ───────────────────► Section 3.3 (Rest Interval Overlap)
├── Bracket Missing / "Draws Being Finalized"? ────► Section 3.4 (Draft Draw Publication State)
├── BOLA / IDOR Ownership Forbidden (403)? ────────► Section 4.1 (Roles & Staff Records)
├── CSRF Failure on Web Form? ─────────────────────► Section 4.2 (CSRF vs API Header)
├── Conflict of Interest Forbidden (403)? ─────────► Section 4.3 (Participant Officiating Guard)
├── 409 Conflict: Match Concurrently Updated? ────► Section 4.4 (Optimistic Lock Version Collision)
├── Court PIN Rejected / Locked Out? ──────────────► Section 4.5 (Court PIN v2)
├── 429 Too Many Requests? ────────────────────────► Section 4.6 (Rate Limiting)
├── 401 on API (expired / invalid JWT)? ───────────► Section 4.7 (JWT Problems)
├── App Refuses to Start in Production? ───────────► Section 4.8 (Startup Safety Checks)
├── Vercel Serverless Cold Start Timeout? ─────────► Section 5.1 (Cold-Start Guard)
├── Live Scores Not Pushing (WebSocket)? ──────────► Section 5.2 (WebSockets on Vercel)
└── Login Loops / Session Lost Behind Proxy? ──────► Section 5.3 (ProxyFix & Secure Cookies)
```

---

## 2. Database & Persistence Troubleshooting

### 2.1 Supabase PgBouncer `prepared statement already exists`
* **Symptom:** Fatal PostgreSQL exception: `prepared statement "..." already exists` or `statement cache collision`.
* **Root Cause:** Supabase uses PgBouncer in Transaction Pooling mode (port 6543). Standard PostgreSQL client drivers attempt to cache prepared statements per session, causing name collisions when PgBouncer switches backend connections.
* **Resolution:** Ensure `prepare_threshold: None` is configured in [`config.py`](config.py):
  ```python
  if db_url and db_url.startswith('postgresql'):
      SQLALCHEMY_ENGINE_OPTIONS = {
          'pool_pre_ping': True,
          'connect_args': {
              'prepare_threshold': None  # Must remain None
          }
      }
  ```

### 2.2 Host Name Translation Failure / Quoted `DATABASE_URL`
* **Symptom:** Driver fails with `could not translate host name "..." or address not known` or connection string syntax errors.
* **Root Cause:** Environment variables copied from dashboards often include hidden newline characters, spaces, or surrounding quotes (`"postgresql://..."`).
* **Resolution:** Sanitize the variable in `config.py` using:
  ```python
  db_url = os.environ.get('DATABASE_URL')
  if db_url:
      db_url = db_url.strip().strip("'\"")
  ```

### 2.3 SQLite `no such column` after Code Pull
* **Symptom:** Pulling the latest branch produces `sqlite3.OperationalError: no such column: categories.start_date`.
* **Root Cause:** A new model column was introduced without running the schema reconciler on your local database.
* **Resolution:** Execute the schema sync utility:
  ```bash
  python scripts/sync_db_schema.py
  ```
  The script directly inspects the SQLite schema and runs safe `ALTER TABLE ... ADD COLUMN` statements.

---

### 2.4 Wrong Postgres Driver (`No module named psycopg2`)
* **Symptom:** `ModuleNotFoundError: No module named 'psycopg2'` right after setting `DATABASE_URL`.
* **Root Cause:** a URL beginning with `postgresql://` makes SQLAlchemy load psycopg2, but the project uses psycopg 3. The sanitizer must rewrite both `postgres://` and `postgresql://` to `postgresql+psycopg://` (see [`INTEGRATIONS.md`](INTEGRATIONS.md) §2.2).
* **Resolution:** use the normalized URL, or write `postgresql+psycopg://...` directly in the environment.

---

## 3. Tournament Logic & Scheduling Diagnostics

### 3.1 Feeder Match Progression Locks
* **Symptom:** Score reporting fails with HTTP 400: `"Cannot start match until predecessor matches are completed"`.
* **Root Cause:** The Baseline Society enforces strict progression locking via `check_match_progression_allowed(match)` in [`app/services/utils/scheduler.py`](app/services/utils/scheduler.py). A Round 2 match cannot be reported while either of its feeder Round 1 matches is still `pending` or `in_progress`.
* **Resolution:** 
  1. Inspect the upstream bracket tree.
  2. Locate the two feeder matches (whose winners advance to this match).
  3. Report and finalize scores for the feeder matches first.

### 3.2 Rubber Summation Rule ($T=7$) Rejections
* **Symptom:** Score report error: `"Total rubber games must equal 7"`.
* **Root Cause:** In the Group Stage Team League format, every rubber must total exactly 7 games ($G_1 + G_2 = 7$).
* **Resolution:**
  * Standard finishes must sum to 7: `4-3`, `5-2`, `6-1`, or `7-0`.
  * If score is tied `3-3`, the tiebreak decides the 7th game, resulting in `4-3`.
  * If a player retires mid-match (e.g. at `2-1`), apply the Walkover Rule: award all remaining unplayed games to the opponent so total reaches 7 (`2-5`).

### 3.3 Player Rest Interval Overlap
* **Symptom:** Scheduler flags a warning: `"Player scheduled with insufficient rest buffer"`.
* **Root Cause:** An athlete competing in multiple categories (e.g. Singles and Doubles) has matches scheduled closer than `min_rest_minutes` (default: 30 minutes).
* **Resolution:** In the Order of Play dashboard, drag or adjust the start time of the second match to provide at least 30 minutes after the estimated finish time (`scheduled_end_time`) of the first match.

### 3.4 Spectators Cannot View Bracket / "Draws for this event are being finalized"
* **Symptom:** Public spectators or players see a banner message instead of the tournament draw tree.
* **Root Cause:** The category is in Draft mode (`draw_published = False`). Organizers must review and publish the draw before it becomes public.
* **Resolution:** Log in as the tournament organizer or desk staff, navigate to the category dashboard, and click the **"Publish Draw"** button (or toggle via `/categories/<id>/toggle-publish`). Once published, the bracket and vector PDF export become immediately accessible.

---

## 4. Security & Access Control Diagnostics

### 4.1 `403 Forbidden: You do not own this tournament`
* **Symptom:** Users receive an HTTP 403 when saving settings or accessing management dashboards.
* **Root Cause:** the central guard `check_tournament_access()` found no match for tournament ownership, superadmin role, or an active `TournamentStaff` record of sufficient rank.
* **Resolution:**
  * Owner-only actions (settings, staff appointment, Court PIN generation, draw publication, payment settings) are never available to staff. Sign in as the owner or a superadmin.
  * Appoint the user via `/tournaments/<slug>/staff` as `manager`, `official`, or `scorer`. Legacy values (`tournament_admin`, `desk`, `umpire`) in `tournament_staff.role` should be migrated; if they are still present, run the role data migration.
  * For on-court tablets see §4.5.

### 4.2 `CSRF session token missing or invalid`
* **Symptom:** Submitting a web form returns `400 Bad Request: The CSRF session token is missing`.
* **Root Cause:** Session cookie expired, or a form template was rendered without `{{ csrf_token() }}`.
* **Resolution:**
  * For Web Forms: Verify `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>` is present.
  * For REST API: Ensure the request targets `/api/v1/` with header `Authorization: Bearer <token>`. The API blueprint is explicitly exempted from CSRF.

### 4.3 `403 Forbidden: Conflict of interest`
* **Symptom:** Official receives HTTP 403: `"Conflict of interest: Active participants cannot officiate or score their own matches"`.
* **Root Cause:** Sporting integrity guard `check_scoring_conflict_of_interest()` detected that the logged-in user is an active player (or captain of a competing team) in that specific fixture.
* **Resolution:** Hand over match officiating to a neutral chair umpire, desk manager, or tournament director. Active players are prohibited from scoring their own matches.

### 4.4 `409 Conflict: Match was updated by another official`
* **Symptom:** Submitting a match score returns HTTP 409 Conflict with prompt to refresh.
* **Root Cause:** Optimistic concurrency control detected that `submitted_lock_version != match.lock_version`, indicating that another desk official or umpire modified the match score simultaneously.
* **Resolution:** Refresh the page to load the latest score state, verify the current scoreline, and re-submit the updated score.

### 4.5 Court PIN Rejected or Locked Out (Court PIN v2)
* **Symptom:** the scorer tablet says the PIN is invalid, expired, locked, or "wrong court".
* **Root Cause / Checks:**
  * PINs are **6 digits** (older docs said 4) and expire after 8, 24, or 48 hours.
  * Five wrong attempts lock entry for 15 minutes per IP and tournament.
  * A PIN may be bound to one court; it cannot score matches on another court.
  * Court PIN sessions work only in the web UI, never against `/api/v1/`.
* **Resolution:** the owner generates a new PIN at `/tournaments/<slug>/court-pin`, or waits out the lock. Check the audit log for the failed attempts if a brute-force attack is suspected.

### 4.6 `429 Too Many Requests`
* **Symptom:** login, registration, PIN entry, or public polling returns 429 with `Retry-After`.
* **Root Cause:** a rate limit in [`AUTH.md`](AUTH.md) §9 was exceeded. If every user behind one proxy is limited at once, the proxy IP is being used instead of the client IP.
* **Resolution:** wait for `Retry-After`; verify `ProxyFix` trusts exactly the right number of proxies; confirm the limiter uses shared storage (Redis or database), not per-process memory.

### 4.7 API `401 Unauthorized` (JWT Problems)
* **Symptom:** valid-looking requests fail with 401.
* **Checks:** token expired (default 60 minutes), missing `Bearer ` prefix, signed with a different `JWT_SECRET_KEY` than the server uses (for example after secret rotation), or the account's role is `deleted`.
* **Resolution:** log in again at `/api/v1/auth/login`; never put tokens in URLs.

### 4.8 App Refuses to Start with `APP_ENV=production`
* **Symptom:** startup error about secrets or superadmin credentials.
* **Root Cause:** the production safety check found a missing or default `SECRET_KEY`, `JWT_SECRET_KEY`, or `SUPERADMIN_PASSWORD`, or `DEBUG` enabled.
* **Resolution:** set strong unique values in the platform secret store. Do not bypass the check.

### 4.9 Public API Returns 403 for a Category
* **Symptom:** `GET /api/v1/tournaments/<slug>/categories/<id>` returns 403 "Draws for this event are being finalized".
* **Root Cause:** the category is still a draft (`draw_published = false`). The API intentionally returns no fixtures or participants to the public.
* **Resolution:** the organizer publishes the draw (see §3.4).

---

## 5. Hosting & Deployment Diagnostics

### 5.1 Vercel Serverless Function Timeouts (Cold Starts)
* **Symptom:** Initial request after idle period triggers Vercel `FUNCTION_INVOCATION_TIMEOUT` (10s limit).
* **Root Cause:** Boot script attempting to execute heavy DDL checks (`db.create_all()`) on every lambda container cold start.
* **Resolution:** Verify the serverless environment check in [`app/__init__.py`](app/__init__.py):
  ```python
  if not os.environ.get('VERCEL'):
      db.create_all()
      # Column checks...
  ```
  In serverless mode, schema migrations must run in CI/CD deployment pipelines, not on application boot.

### 5.2 Live Scores Not Pushing (WebSockets on Vercel)
* **Symptom:** WebSocket connections fail or time out on the Vercel deployment.
* **Root Cause:** Vercel serverless functions cannot hold persistent WebSocket connections.
* **Resolution:** keep the 5-second polling fallback (`/api/v1/live/<slug>/scores`, CDN-cached), use a managed realtime service, or host the app on a container platform (see [`ARCHITECTURE.md`](ARCHITECTURE.md) §7).

### 5.3 Login Loops / Session Lost Behind a Proxy
* **Symptom:** users log in but are immediately logged out, or CSRF errors occur only in production.
* **Root Cause:** `SESSION_COOKIE_SECURE=True` with the app believing the request is HTTP (missing `ProxyFix`/`X-Forwarded-Proto`), or the cookie domain does not match.
* **Resolution:** configure `ProxyFix` for the real number of proxies and confirm the proxy forwards `X-Forwarded-Proto: https`.

---

## 6. SRE & Diagnostic Command Cheat Sheet

| Task | Command |
| :--- | :--- |
| **Run Linter Checks** | `ruff check .` |
| **Run Entire Test Suite (82 tests)** | `python -m unittest discover tests -v` |
| **Run RBAC & Concurrency Tests** | `python -m unittest tests/test_rbac.py -v` |
| **Run Team League Tests** | `python -m unittest tests/test_team_league.py -v` |
| **Reconcile Database Schema** | `python scripts/sync_db_schema.py` |
| **Initialize / Verify UAT Database** | `python scripts/init_uat_db.py` |
| **Generate Sample Tournament Data** | `python scripts/create_sample_tournament.py` |
| **Inspect Active Local Routes** | `python -c "from app import create_app; app=create_app(); print(app.url_map)"` |
| **Check SQLite Database Tables** | `sqlite3 instance/tournaments.db ".tables"` |
| **Static Security Scan** | `bandit -r app -ll` |
| **Dependency Vulnerability Audit** | `pip-audit -r requirements.txt` |
| **List Registered Routes** | `flask routes` |
