# The Baseline Society — AI & Autonomous Agent Operating Manual (AGENTS.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`API.md`](API.md), [`DATABASE.md`](DATABASE.md), and [`ARCHITECTURE.md`](ARCHITECTURE.md)  
**Target Audience:** AI Coding Assistants (Antigravity, Cursor, Copilot, Claude Code) & Autonomous Multi-Agent Workflows  
**Last Updated:** November 2026  

---

## 1. Agent Mission & Operational Context

> **Naming:** use **The Baseline Society** in all user-facing text and documentation. Do not rename code identifiers (repository folder, `tourneypro_*` MCP tools, `tourneypro://` URIs, file names) as a side effect of another task; that needs its own reviewed change.

You are operating on **The Baseline Society**, a production-grade sports and gaming tournament management platform. Every change you make must preserve structural stability, relational integrity across 18 database tables, and the strict mathematical rules governing brackets, byes, rubbers, and court scheduling.

---

## 2. Immutable Architecture & Technology Guardrails

When modifying or extending The Baseline Society, you MUST adhere strictly to these rules:

1. **Backend Tech Stack:**
   * Runtime: Python 3.12 (specifically Python 3.12.8).
   * Framework: Flask 3.1+ using the Application Factory Pattern (`create_app` in [`app/__init__.py`](app/__init__.py)).
   * ORM: SQLAlchemy 2.0 idioms. Avoid legacy SQLAlchemy 1.x queries where possible.
2. **Frontend Architecture:**
   * **STRICT RULE:** Use **Vanilla HTML5, CSS3, and Vanilla JavaScript**.
   * **FORBIDDEN:** Do NOT install or introduce heavy frontend frameworks (React, Vue, Angular, Svelte) to the web application.
   * **FORBIDDEN:** Do NOT install or inject Tailwind CSS unless explicitly ordered by the user. Rely on the curated design token system in [`app/web/static/css/style.css`](app/web/static/css/style.css).
3. **Database Dual Strategy:**
   * Local development and automated tests run on **SQLite** (`instance/tournaments.db`).
   * Cloud production runs on **PostgreSQL / Supabase** with PgBouncer transaction pooling.
   * Never remove `'prepare_threshold': None` or `'pool_pre_ping': True` from `SQLALCHEMY_ENGINE_OPTIONS` in [`config.py`](config.py).
   * Always sanitize database URLs with `.strip().strip("'\"")`.
4. **Timezone Policy:**
   * All database datetime columns store pure **UTC** (always `datetime.now(timezone.utc)`; `datetime.utcnow()` is deprecated since Python 3.12 and must not appear in new code).
   * For user presentation in web templates, apply the custom Jinja filter `| ist` (which converts UTC natively to `Asia/Kolkata`).

---

## 3. Security & Access Control Mandates

### 3.1 Broken Object Level Authorization (BOLA/IDOR)
Every route that reads private data or mutates tournament data MUST call the central guard `check_tournament_access()`. Never compare `tournament.user_id` by hand: hand-written checks skip delegated staff, Court PIN rules, and audit logging.

```python
# Web controller
from app.web.controllers.auth import login_required, check_tournament_access

@tournament_bp.route('/tournaments/<slug>/settings', methods=['POST'])
@login_required
def update_settings(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_access(tournament, min_role="owner")   # aborts 403 on failure (fail-closed)
    ...

# API controller (JWT identity is NOT visible to Flask-Login, so pass the user explicitly)
@api_bp.route('/matches/<int:match_id>/report', methods=['POST'])
@jwt_required()
def report_match(match_id):
    user = db.session.get(User, int(get_jwt_identity()))     # SQLAlchemy 2.0 idiom
    if user is None or user.role == 'deleted':
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    match = db.session.get(Match, match_id) or abort(404)
    check_tournament_access(match.tournament, min_role="scorer", user=user)
    check_scoring_conflict_of_interest(match, user)           # raises 403; never ignore a return value
    ...
```

> **Rule:** a guard must either raise/abort or return a value that the caller is forced to check. A guard whose return value can be silently ignored is a security bug.

### 3.2 CSRF vs. API Exemption
* Web controllers render WTForms with `{{ csrf_token() }}`.
* The API Blueprint (`/api/v1/`) is explicitly exempted via `csrf.exempt(api_bp)` in [`app/__init__.py`](app/__init__.py). Never disable CSRF globally.
* Because the API is CSRF-exempt it must never accept session cookies as authentication; Bearer JWT only.

### 3.3 Fail-Closed Authorization
* Unknown roles, unknown `min_role` values, and missing records MUST deny access. Never use `dict.get(x, 0)` comparisons that let an unrecognized value pass.
* Canonical staff roles are `manager`, `official`, `scorer` (see [`AUTH.md`](AUTH.md) §2). Legacy names (`tournament_admin`, `desk`, `umpire`) are aliases to be migrated, not accepted for new code.
* Only the tournament owner or a superadmin may appoint staff, generate Court PINs, publish draws, or change payment settings.
* Superadmin overrides must always write an `AuditLog` entry.

### 3.4 Input, Output & Secrets Safety
1. **No default credentials in production.** The app must refuse to start when `APP_ENV=production` and `SECRET_KEY`, `JWT_SECRET_KEY`, or `SUPERADMIN_PASSWORD` are missing or equal to a documented default.
2. **Never log or echo** passwords, JWTs, PINs, UPI transaction IDs, or API keys. Never paste real keys into prompts, issues, or commits.
3. **Escape everything user-supplied** in Jinja (keep autoescape on; never use `|safe` on user data) and in PDF templates (`xhtml2pdf` renders HTML; see [`INTEGRATIONS.md`](INTEGRATIONS.md) §4).
4. **Spreadsheet/CSV exports** must neutralize cells starting with `=`, `+`, `-`, `@` (prefix with `'`). Imports must enforce file-size, row-count, and extension limits.
5. **Uploads** (avatars, match attachments) require a MIME allow-list (JPEG/PNG/WebP/PDF), size cap, random server-generated filenames, and storage outside `app/web/static/`. SVG and HTML uploads are forbidden.
6. **Rate-limit** login, registration, Court PIN entry, and public polling endpoints (see [`AUTH.md`](AUTH.md) §9).
7. **Never trust client-supplied IDs together**: validate that `winner_id` is one of the match's participants and that nested IDs belong to the same tournament.
8. Raw SQL is forbidden unless parameterized; prefer ORM expressions.

---

---

## 4. Database Modification & Migration Protocol

If your task requires changing database models in [`app/domain/models.py`](app/domain/models.py):

1. **Update Models First:** Declare fields using standard SQLAlchemy 2.0 column declarations.
2. **Never Edit Past Migration Scripts:** Do NOT edit existing scripts in [`migrations/versions/`](migrations/versions/). Always generate a new migration revision.
3. **SQLite Batch Mode:** Ensure any new migration supports SQLite batch mode via `with op.batch_alter_table('table_name') as batch_op:`.
4. **Automated Schema Sync:** Verify that [`scripts/sync_db_schema.py`](scripts/sync_db_schema.py) recognizes your new column, so automated CI/CD deployments to Supabase remain non-destructive.

---

## 5. Match Progression & Tournament Logic Rules

When writing or modifying tournament logic:
1. **Feeder Match Lock:** Always call `check_match_progression_allowed(match)` before marking a match completed or advancing winners. Downstream matches MUST NOT start while feeder matches are incomplete.
2. **Double Advancement Prevention:** Always check if a winner has already been advanced to prevent orphan fixtures or duplicate next-round participants.
3. **Rubber Summation Rule ($T=7$):** For team leagues, validate that $G_1 + G_2 = 7$ (a rubber decided by tiebreak is recorded `4-3`, which still sums to 7). In walkovers or retirements, award remaining unplayed games to the non-retiring participant.

---

## 6. Pre-Commit Verification Checklist for Agents

Before completing any coding task or reporting completion to the user, you MUST run:

1. **Linter Check:**
   ```bash
   ruff check .
   ```
   Resolve all syntax errors, import errors, and style issues.
2. **Automated Test Suite:**
   ```bash
   ./venv/bin/python -m unittest discover tests -v
   ```
   Verify that **all 82 unit and integration tests pass**. Any test failure indicates an architectural regression that you must immediately diagnose and fix.
3. **Security Scan:**
   ```bash
   bandit -r app -ll
   pip-audit -r requirements.txt
   ```
   Resolve all High/Medium findings or document an explicit, reviewed exception.
4. **Responsive Check (any UI change):** verify the screen at 320, 360, 390, 430, 768, 1024, 1440 and 1920 px widths plus landscape phone (height ≤ 500 px). There must be no horizontal page scroll, and all tap targets must stay ≥ 44 × 44 px (see [`DESIGN.md`](DESIGN.md) §7).
5. **Documentation Sync:** if you change a route, role name, column, or environment variable, update `API.md`, `DATABASE.md`, `AUTH.md`, and `SETUP.md` in the same change. Do not hard-code test counts in new documentation.
