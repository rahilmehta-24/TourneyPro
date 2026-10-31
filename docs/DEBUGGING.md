# TourneyPro — Troubleshooting Playbook & Operational Diagnostics (DEBUGGING.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`TESTING.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/TESTING.md), [`SETUP.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/SETUP.md), [`DATABASE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/DATABASE.md), and [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md)  
**Primary Audience:** Site Reliability Engineers (SRE), Backend Engineers & Technical Support Admins  
**Last Updated:** October 2026  

---

## 1. Quick Diagnostic Decision Tree

```
Encountered an Issue?
│
├── Database Connection / Pool Failure? ───────────► Section 2.1 (PgBouncer & Quotes)
├── Missing Column / SQLite Schema Error? ─────────► Section 2.2 (Schema Sync Tool)
├── Match Progression Lock Rejection (400)? ───────► Section 3.1 (Feeder Match Checks)
├── Rubber Summation Score Error ($T=7$)? ─────────► Section 3.2 (Summation & Walkovers)
├── BOLA / IDOR Ownership Forbidden (403)? ────────► Section 4.1 (User ID Matching)
├── CSRF Failure on Web Form? ─────────────────────► Section 4.2 (CSRF vs API Header)
└── Vercel Serverless Cold Start Timeout? ─────────► Section 5.1 (Cold-Start Guard)
```

---

## 2. Database & Persistence Troubleshooting

### 2.1 Supabase PgBouncer `prepared statement already exists`
* **Symptom:** Fatal PostgreSQL exception: `prepared statement "..." already exists` or `statement cache collision`.
* **Root Cause:** Supabase uses PgBouncer in Transaction Pooling mode (port 6543). Standard PostgreSQL client drivers attempt to cache prepared statements per session, causing name collisions when PgBouncer switches backend connections.
* **Resolution:** Ensure `prepare_threshold: None` is configured in [`config.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/config.py):
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

## 3. Tournament Logic & Scheduling Diagnostics

### 3.1 Feeder Match Progression Locks
* **Symptom:** Score reporting fails with HTTP 400: `"Cannot start match until predecessor matches are completed"`.
* **Root Cause:** TourneyPro enforces strict progression locking via `check_match_progression_allowed(match)` in [`app/services/utils/scheduler.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/services/utils/scheduler.py). A Round 2 match cannot be reported while either of its feeder Round 1 matches is still `pending` or `in_progress`.
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

---

## 4. Security & Access Control Diagnostics

### 4.1 `403 Forbidden: You do not own this tournament`
* **Symptom:** Organizers receive an HTTP 403 when saving settings or reporting scores.
* **Root Cause:** Broken Object Level Authorization (BOLA) guard detected that `current_user.id != tournament.user_id`.
* **Resolution:** Verify which account created the tournament. Log in as that organizer account or sign in as `superadmin` (who has global override authority).

### 4.2 `CSRF session token missing or invalid`
* **Symptom:** Submitting a web form returns `400 Bad Request: The CSRF session token is missing`.
* **Root Cause:** Session cookie expired, or a form template was rendered without `{{ csrf_token() }}`.
* **Resolution:**
  * For Web Forms: Verify `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>` is present.
  * For REST API: Ensure the request targets `/api/v1/` with header `Authorization: Bearer <token>`. The API blueprint is explicitly exempted from CSRF.

---

## 5. Hosting & Deployment Diagnostics

### 5.1 Vercel Serverless Function Timeouts (Cold Starts)
* **Symptom:** Initial request after idle period triggers Vercel `FUNCTION_INVOCATION_TIMEOUT` (10s limit).
* **Root Cause:** Boot script attempting to execute heavy DDL checks (`db.create_all()`) on every lambda container cold start.
* **Resolution:** Verify the serverless environment check in [`app/__init__.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/__init__.py):
  ```python
  if not os.environ.get('VERCEL'):
      db.create_all()
      # Column checks...
  ```
  In serverless mode, schema migrations must run in CI/CD deployment pipelines, not on application boot.

---

## 6. SRE & Diagnostic Command Cheat Sheet

| Task | Command |
| :--- | :--- |
| **Run Linter Checks** | `ruff check .` |
| **Run Entire Test Suite (72 tests)** | `python -m unittest discover tests -v` |
| **Run Single Test Case** | `python -m unittest tests.test_team_league.TeamLeagueTestCase.test_01_rubber_scoring_default_t7` |
| **Reconcile Database Schema** | `python scripts/sync_db_schema.py` |
| **Initialize / Verify UAT Database** | `python scripts/init_uat_db.py` |
| **Generate Sample Tournament Data** | `python scripts/create_sample_tournament.py` |
| **Inspect Active Local Routes** | `python -c "from app import create_app; app=create_app(); print(app.url_map)"` |
| **Check SQLite Database Tables** | `sqlite3 instance/tournaments.db ".tables"` |
