# TourneyPro — Technology Stack, Coding Environment & Branch Audit

**Document Version:** 1.0
**Generated:** October 2026
**Repository:** `TourneyPro`
**Active Python Runtime:** Python 3.12.8

---

## 1. Executive Summary

**TourneyPro** is a comprehensive, production-ready tournament management web platform tailored for sports (lawn tennis, pickleball, badminton, padel) and gaming competitions. It provides end-to-end tournament lifecycle operations: multi-category management, single/doubles knockout brackets, round-robin leagues, group-stage team leagues with 3-rubber scoring, live scorekeeping, player registries, court scheduling algorithms, and role-based access control.

This document details the current **technology stack**, the **local and CI/CD coding environment**, and provides an exact audit of the code differences between the **`main`** and **`uat`** branches.

---

## 2. Technology Stack Breakdown

### 2.1 Backend Architecture & Runtime

* **Runtime:** Python 3.12 (specifically Python 3.12.8).
* **Core Framework:** [Flask](https://flask.palletsprojects.com/) (v3.1.3) built with [Werkzeug](https://werkzeug.palletsprojects.com/) (v3.1.8).
* **Pattern:** Application Factory Pattern (`create_app` in [`app/__init__.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/__init__.py)) with modular Flask Blueprints:
  * `main_bp` ([`app/web/controllers/main.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/main.py)): Homepage and public entry points.
  * `tournament_bp` ([`app/web/controllers/tournament.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/tournament.py)): Tournament creation, settings, court scheduling, and order of play.
  * `category_bp` ([`app/web/controllers/category.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/category.py)): Event formats, bracket generation, team drafts, rubber scoring, and match coordination.
  * `player_bp` ([`app/web/controllers/player.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/player.py)): Global player registry, player profiles, and career statistics.
  * `leaderboard_bp` ([`app/web/controllers/leaderboard.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/leaderboard.py)): Real-time tournament and overall standings.
  * `academy_bp` ([`app/web/controllers/academy.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/academy.py)): Club and academy management workflows.
  * `auth_bp` ([`app/web/controllers/auth.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py)): User authentication, session management, RBAC, audit logs, and superadmin bootstrapping.
  * `export_bp` ([`app/web/controllers/export.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/export.py)): PDF bracket and Excel roster exports.
  * `api_bp` ([`app/api/__init__.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/api/__init__.py)): RESTful JSON API (`/api/v1/`) with JWT authentication.

### 2.2 Database, ORM & Storage

* **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/) (v2.0.51) integrated via [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) (v3.1.1).
* **Dual Database Strategy:**
  1. **SQLite (Development / Testing / Local UAT):**
     * Local database file at [`instance/tournaments.db`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/instance/tournaments.db).
     * Configured with Alembic batch mode (`render_as_batch=True`) to support full SQLite schema alterations and migrations.
  2. **PostgreSQL / Supabase (Staging / Production Cloud):**
     * Connected via [psycopg](https://www.psycopg.org/) & `psycopg-binary` (v3.3.4).
     * Connection pooling configured with `pool_pre_ping=True` and `prepare_threshold: None` in [`config.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/config.py) to ensure compatibility with Supabase transaction connection poolers (PgBouncer).
* **Database Migration & Synchronization Engine:**
  * **Flask-Migrate** (v4.1.0) & **Alembic** (v1.20.0): Track schema revisions in [`migrations/versions/`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/migrations/versions/).
  * **Automated Schema Verifier & Sync Engine** ([`scripts/sync_db_schema.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/scripts/sync_db_schema.py)): Inspects target database tables and columns directly against SQLAlchemy models, automatically applying non-destructive additions (`CREATE TABLE`, `ALTER TABLE ... ADD COLUMN`) during automated deployments.

### 2.3 Authentication, Authorization & Security

* **Session & CSRF Protection:** [Flask-WTF](https://flask-wtf.readthedocs.io/) (v1.3.0) & [WTForms](https://wtforms.readthedocs.io/) (v3.2.2) enforcing `CSRFProtect` across all HTML forms and state-mutating requests, with explicit exemptions for `/api/v1/`.
* **API Authentication:** [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) (v4.7.4) & [PyJWT](https://pyjwt.readthedocs.io/) (v2.13.0) for bearer token authentication.
* **Access Control (RBAC):**
  * Roles: `superadmin`, `admin` (tournament organizer), `player`/`user`, and unauthenticated public viewers.
  * Broken Object Level Authorization (BOLA/IDOR) guards: Enforced at both web controller and API levels, preventing organizers from modifying other organizers' tournaments or fixtures.
* **Superadmin Bootstrapping:** [`bootstrap_superadmin()`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/controllers/auth.py) executes automatically on boot to create or synchronize administrative credentials from environment variables.

### 2.4 Serialization & Validation

* **Schemas:** [Flask-Marshmallow](https://flask-marshmallow.readthedocs.io/) (v1.5.0), [Marshmallow-SQLAlchemy](https://marshmallow-sqlalchemy.readthedocs.io/) (v1.5.0), and [Marshmallow](https://marshmallow.readthedocs.io/) (v4.3.0) define schemas for Users, Tournaments, Categories, Matches, and Participants ([`app/domain/schemas.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/domain/schemas.py)).
* **Validation Layer:** Custom validation utilities in [`app/services/utils/validation.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/services/utils/validation.py).

### 2.5 Frontend Architecture & UI

* **Vanilla Architecture:** Lightweight, responsive, server-side rendered (SSR) web architecture. **No heavy frontend frameworks (React, Vue, Angular)** on the web client, ensuring lightning-fast load times and zero frontend build pipelines.
* **Templating:** [Jinja2](https://jinja.palletsprojects.com/) (v3.1.6) with custom filters:
  * `ist`: Localized date and time formatting (Asia/Kolkata).
  * `format_tennis_score`: Tiebreak formatting with `<sup>` superscripts.
  * `display_match_score`: Intelligent display for numeric games, rubbers, or multi-set tennis scores.
  * `participant_players`: Dynamic player extraction for doubles pairs and teams.
* **Styling & Design System:**
  * Vanilla CSS3 ([`app/web/static/css/style.css`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/static/css/style.css)).
  * Curated design tokens, CSS variables, Dark Mode toggle, Glassmorphism, and responsive CSS grid/flexbox layouts.
* **Dynamic Bracket Connectors:** Client-side SVG connector generator rendering tournament bracket paths dynamically based on match node coordinates.
* **Performance:** [Flask-Compress](https://github.com/colour-science/flask-compress) (v1.24) with Brotli and Gzip compression, combined with 1-hour browser cache headers for static assets.

### 2.6 Export & Document Generation

* **PDF Rendering:** [xhtml2pdf](https://github.com/xhtml2pdf/xhtml2pdf) (v0.2.17), [reportlab](https://www.reportlab.com/) (v4.5.1), [pycairo](https://pycairo.readthedocs.io/) (v1.29.0), [pypdf](https://pypdf.readthedocs.io/) (v6.13.2).
* **Spreadsheet Rosters:** [openpyxl](https://openpyxl.readthedocs.io/) (v3.1.5) for exporting and importing participant entries.

### 2.7 Deployment & Hosting

* **WSGI Server:** [gunicorn](https://gunicorn.org/) (v26.0.0).
* **Serverless Deployment:** [Vercel](https://vercel.com/) configured via [`vercel.json`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/vercel.json) using the `@vercel/python` builder routing all paths to [`run.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/run.py).

---

## 3. Coding & Development Environment

### 3.1 Local Environment

* **Operating System:** macOS (Darwin).
* **Shell:** Zsh.
* **Project Directory:** `/Users/rahilmehta24/VS_Code/Projects/TourneyPro`
* **Virtual Environment:** Located in [`venv/`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/venv) (Python 3.12.8, Pip 24.3.1).
* **Activation:**
  ```bash
  source venv/bin/activate
  ```
* **Local Run Command:**
  ```bash
  python run.py
  # Serves at http://127.0.0.1:5000 with debug=True
  ```

### 3.2 Environment Variables Configuration

Configured in [`.env`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.env) with a reference template in [`.env.example`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.env.example):

* `SECRET_KEY`: Cryptographic signing key for sessions and CSRF tokens.
* `FLASK_APP`: WSGI target (`run.py`).
* `FLASK_ENV`: Environment identifier (`development` or `production`).
* `SUPERADMIN_USERNAME` & `SUPERADMIN_PASSWORD`: Administrative credentials.
* `DATABASE_URL`: Connection string. Defaults to `sqlite:///instance/tournaments.db` when commented out or omitted. When targeting Supabase, format: `postgresql://user:password@host:port/dbname`.

### 3.3 Code Quality & Linting

* **Tool:** [Ruff](https://docs.astral.sh/ruff/) (v0.15.20).
* **Configuration:** [`ruff.toml`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ruff.toml).
  * Target Python Version: `py312`.
  * Line Length: 100 characters.
  * Linter Rules: Pycodestyle errors (`E`), Pyflakes (`F`), and Pycodestyle warnings (`W`).
  * Run Command:
    ```bash
    ruff check .
    ```

### 3.4 Automated Test Suite

* **Framework:** Python standard library `unittest` (compatible with `pytest`).
* **Test Isolation:** Each test suite provisions an isolated temporary SQLite database fixture and runs Alembic migrations/tables cleanly.
* **Key Test Suites:**
  * [`tests/test_team_league.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/tests/test_team_league.py): 1,154 lines covering group stage creation, player tier allocations, team draft workflows, 3-rubber match scoring, tiebreakers, and match progression locks.
  * [`tests/test_security_remediation.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/tests/test_security_remediation.py): BOLA/IDOR protection, API bearer token auth, and cross-tournament ownership barriers.
  * [`tests/test_migrations.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/tests/test_migrations.py): Migration upgrade paths, SQLite batch mode verification, and schema column presence.
* **Test Execution:**
  ```bash
  python -m unittest discover tests -v
  # 22 tests passing
  ```

### 3.5 CI/CD Workflows (GitHub Actions)

Located in [`.github/workflows/`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.github/workflows/):

1. **CI & Quality Gate ([`ci.yml`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.github/workflows/ci.yml)):**
   * Triggers: Pushes and Pull Requests targeting `main` and `uat`.
   * Actions: Sets up Python 3.12, installs dependencies, executes `ruff check .`, and runs the 69-test automated test suite.
2. **Production Database Migration & Sync ([`deploy-production.yml`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.github/workflows/deploy-production.yml)):**
   * Triggers: Pushes to `main`, manual `workflow_dispatch`.
   * Actions: Connects to Supabase Production using `secrets.DATABASE_URL`, applies pending Alembic migrations (`flask db upgrade`), and runs `scripts/sync_db_schema.py` to reconcile tables and columns.
3. **UAT Database Migration & Sync ([`deploy-uat.yml`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.github/workflows/deploy-uat.yml)):**
   * Triggers: Pushes to `uat`, manual `workflow_dispatch`.
   * Actions: Connects to Supabase UAT using `secrets.UAT_DATABASE_URL` (with fallback to `DATABASE_URL`), applies pending Alembic migrations, runs `scripts/sync_db_schema.py`, and automatically bootstraps superadmin.
4. **Local / CLI UAT Initializer ([`scripts/init_uat_db.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/scripts/init_uat_db.py)):**
   * Verifies connectivity, applies migrations, runs schema sync, bootstraps superadmin, and outputs a table roster report for any new Supabase project.

---

## 4. Branch Audit: What is in `main` vs. What is in `uat`

### 4.1 Relationship Overview

* **`main` Commit:** `3cdec22` (`origin/main`, `origin/HEAD`)
* **`uat` Commit:** `958822c` (`origin/uat`, `origin/bracket-view-export`)
* **Git Status:** In **Pull Request #4** (`c81d3f8`), `uat` was merged into `main`. Consequently, **`main` contains 100% of all features, bug fixes, and logic present in `uat`**.
* In addition, `main` contains **4 subsequent commits** that provide production database migrations, schema synchronization automation, and configuration hardening.

```mermaid
gitGraph
   commit id: "43c5af4"
   branch uat
   checkout uat
   commit id: "01d6f46 (CI & Migrations)"
   commit id: "f4b1d82 (Group Stage)"
   commit id: "c7cb179 (Ruff Linter)"
   commit id: "726c9fe (Draft & Rankings)"
   commit id: "958822c (UAT Head)"
   checkout main
   merge uat id: "c81d3f8 (Merge PR #4)"
   commit id: "ea64e65 (Fix DATABASE_URL)"
   commit id: "da6689d (Schema Sync)"
   commit id: "3cdec22 (Main Head)"
```

---

### 4.2 Shared Features (Present in Both `main` and `uat`)

Both `main` and `uat` include all features introduced during the Phase 1 Group Stage Team League milestone:

1. **Group Stage Team League Engine:**
   * Models: `groups`, `player_category_tiers`, `team_members`, rubber fields in `matches`.
   * Multi-rubber scoring logic (Singles 1, Doubles, Singles 2 or custom sets/points).
   * Live team draft wizard UI with role allocation and tier designations.
2. **Order of Play Progression Engine:**
   * Strict progression locking: Downstream matches on court schedules remain locked until prerequisite matches finish.
   * Session filtering: Separate views for Day and Evening matches.
   * Match count badges on tournament day tabs and smart court scheduling.
3. **Player Identity & Doubles Parsing:**
   * Extraction of individual player names from doubles pair entries with direct profile links.
   * Registered participant-to-player mapping.
4. **Cleaned Repository:**
   * Removal of legacy React Native `mobile-app/` codebase to focus repo solely on Flask web platform.
   * Removal of deprecated PDF export templates.
5. **Testing & Quality Assurance:**
   * Comprehensive test suites (`test_team_league.py`, `test_security_remediation.py`, `test_migrations.py`).
   * CI quality gate (`ci-uat.yml`).

---

### 4.3 Exclusively in `main` (Ahead of `uat` by 4 Commits)

The following files and capabilities are currently in `main` and have not yet been back-ported to `uat`:

| Component / File                                                                                                                                                                                     | Commit                   | Description & Impact                                                                                                                                                                          |
| :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`migrations/versions/21e2eb139372_add_category_scheduling_columns.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/migrations/versions/21e2eb139372_add_category_scheduling_columns.py) | `3cdec22`              | Alembic migration script adding `start_date`, `end_date`, `start_time`, `end_time`, and `daily_schedule` columns to the `categories` table with idempotent `sa.inspect` checks. |
| [`scripts/sync_db_schema.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/scripts/sync_db_schema.py)                                                                                     | `3cdec22`              | Automated schema reconciliation engine that directly checks PostgreSQL/Supabase database schema against SQLAlchemy models and auto-adds missing tables/columns.                               |
| [`.github/workflows/deploy-migrations.yml`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.github/workflows/deploy-migrations.yml)                                                         | `ea64e65`, `3cdec22` | GitHub Actions workflow updated to sanitize `DATABASE_URL` (trimming hidden newlines/spaces) and run `scripts/sync_db_schema.py` after `flask db upgrade`.                              |
| [`config.py`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/config.py)                                                                                                                     | `ea64e65`              | Added `.strip().strip("'\"")` to `db_url` parsing to prevent connection failures caused by trailing whitespace or quote wraps in environment variables.                                   |
| [`.env.example`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.env.example)                                                                                                               | `3cdec22`              | Standard environment variable template with clean baseline keys for developers and CI/CD runners.                                                                                             |
| [`.gitignore`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/.gitignore)                                                                                                                   | `3cdec22`              | Comprehensive gitignore rules blocking cache files, temporary databases, test outputs, and node leftovers.                                                                                    |
| [`app/web/static/uploads/.gitkeep`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/static/uploads/.gitkeep)                                                                         | `3cdec22`              | Preserves upload folder structure in fresh clones.                                                                                                                                            |
| `scratch/debug_standard_view.mjs`                                                                                                                                                                  | `3cdec22`              | Cleaned up temporary debugging script (removed from `main`).                                                                                                                                |

---

## 5. Recommended Maintenance Step

Because `main` has received production fixes (`DATABASE_URL` sanitization, migration `21e2eb139372`, `scripts/sync_db_schema.py`), it is recommended to sync `uat` with `main` to maintain branch parity:

```bash
# Checkout uat and merge main
git checkout uat
git merge main
git push origin uat
```

This will ensure both branches share identical migration history and production-tested synchronization scripts.
