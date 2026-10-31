# TourneyPro — AI & Autonomous Agent Operating Manual (AGENTS.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`API.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/API.md), [`DATABASE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/DATABASE.md), and [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md)  
**Target Audience:** AI Coding Assistants (Antigravity, Cursor, Copilot, Claude Code) & Autonomous Multi-Agent Workflows  
**Last Updated:** October 2026  

---

## 1. Agent Mission & Operational Context

You are operating on **TourneyPro**, a production-grade sports and gaming tournament management platform. Every change you make must preserve structural stability, relational integrity across 17 database tables, and the strict mathematical rules governing brackets, byes, rubbers, and court scheduling.

---

## 2. Immutable Architecture & Technology Guardrails

When modifying or extending TourneyPro, you MUST adhere strictly to these rules:

1. **Backend Tech Stack:**
   * Runtime: Python 3.12 (specifically Python 3.12.8).
   * Framework: Flask 3.1+ using the Application Factory Pattern (`create_app` in [`app/__init__.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/__init__.py)).
   * ORM: SQLAlchemy 2.0 idioms. Avoid legacy SQLAlchemy 1.x queries where possible.
2. **Frontend Architecture:**
   * **STRICT RULE:** Use **Vanilla HTML5, CSS3, and Vanilla JavaScript**.
   * **FORBIDDEN:** Do NOT install or introduce heavy frontend frameworks (React, Vue, Angular, Svelte) to the web application.
   * **FORBIDDEN:** Do NOT install or inject Tailwind CSS unless explicitly ordered by the user. Rely on the curated design token system in [`app/web/static/css/style.css`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/static/css/style.css).
3. **Database Dual Strategy:**
   * Local development and automated tests run on **SQLite** (`instance/tournaments.db`).
   * Cloud production runs on **PostgreSQL / Supabase** with PgBouncer transaction pooling.
   * Never remove `'prepare_threshold': None` or `'pool_pre_ping': True` from `SQLALCHEMY_ENGINE_OPTIONS` in [`config.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/config.py).
   * Always sanitize database URLs with `.strip().strip("'\"")`.
4. **Timezone Policy:**
   * All database datetime columns store pure **UTC** (`datetime.utcnow` or `datetime.now(timezone.utc)`).
   * For user presentation in web templates, apply the custom Jinja filter `| ist` (which converts UTC natively to `Asia/Kolkata`).

---

## 3. Security & Access Control Mandates

### 3.1 Broken Object Level Authorization (BOLA/IDOR)
Every organizer-facing route that modifies or views sensitive tournament data MUST enforce ownership checks:

```python
# In Web Controllers:
from app.web.controllers.auth import login_required, role_required, check_tournament_ownership

@tournament_bp.route('/t/<slug>/settings', methods=['POST'])
@login_required
@role_required('admin', 'superadmin')
def update_settings(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    check_tournament_ownership(tournament)  # Aborts 403 if not owner and not superadmin
    ...

# In API Controllers:
@api_bp.route('/matches/<int:match_id>/report', methods=['POST'])
@jwt_required()
def report_match(match_id):
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    match = Match.query.get_or_404(match_id)
    if user.role != 'superadmin' and match.tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden"}), 403
```

### 3.2 CSRF vs. API Exemption
* Web controllers render WTForms with `{{ csrf_token() }}`.
* The API Blueprint (`/api/v1/`) is explicitly exempted via `csrf.exempt(api_bp)` in [`app/__init__.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/__init__.py). Never disable CSRF globally.

---

## 4. Database Modification & Migration Protocol

If your task requires changing database models in [`app/domain/models.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/domain/models.py):

1. **Update Models First:** Declare fields using standard SQLAlchemy 2.0 column declarations.
2. **Never Edit Past Migration Scripts:** Do NOT edit existing scripts in [`migrations/versions/`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/migrations/versions/). Always generate a new migration revision.
3. **SQLite Batch Mode:** Ensure any new migration supports SQLite batch mode via `with op.batch_alter_table('table_name') as batch_op:`.
4. **Automated Schema Sync:** Verify that [`scripts/sync_db_schema.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/scripts/sync_db_schema.py) recognizes your new column, so automated CI/CD deployments to Supabase remain non-destructive.

---

## 5. Match Progression & Tournament Logic Rules

When writing or modifying tournament logic:
1. **Feeder Match Lock:** Always call `check_match_progression_allowed(match)` before marking a match completed or advancing winners. Downstream matches MUST NOT start while feeder matches are incomplete.
2. **Double Advancement Prevention:** Always check if a winner has already been advanced to prevent orphan fixtures or duplicate next-round participants.
3. **Rubber Summation Rule ($T=7$):** For team leagues, validate that $G_1 + G_2 = 7$ (or $4-3$ on tiebreak). In walkovers or retirements, award remaining unplayed games to the non-retiring participant.

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
   Verify that **all 72+ unit and integration tests pass**. Any test failure indicates an architectural regression that you must immediately diagnose and fix.
