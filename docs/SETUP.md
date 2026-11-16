# The Baseline Society — Developer & Deployment Setup Guide (SETUP.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`PLAN.md`](PLAN.md), [`README.md`](README.md), and [`ARCHITECTURE.md`](ARCHITECTURE.md)  
**Target Environments:** Local Workstations (macOS, Linux, Windows), UAT Staging, and Production (Vercel + Supabase)  
**Last Updated:** November 2026  

---

## 1. System Prerequisites

Before setting up The Baseline Society, verify that your development machine has the following tools installed:

* **Python:** Python 3.12 (specifically Python 3.12.8 recommended).
* **Package Manager:** `pip` (v24.0+).
* **Version Control:** `git` (v2.30+).
* **Virtual Environment:** Built-in Python `venv` module.

---

## 2. Local Environment Setup

### 2.1 Clone Repository
```bash
git clone <repository-url>
cd TourneyPro
```

### 2.2 Create and Activate Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2.3 Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Environment Configuration (`.env`)

Create a `.env` file in the project root by copying the template:

```bash
cp .env.example .env
```

### 3.1 Environment Variable Reference

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `FLASK_APP` | Yes | `run.py` | Flask WSGI entry point. |
| `FLASK_DEBUG` | No | `0` | Set `1` for local development only. (`FLASK_ENV` was removed in Flask 2.3+ and is ignored.) |
| `APP_ENV` | Yes in cloud | `development` | `production` enables strict startup validation (see §3.2). |
| `SECRET_KEY` | Yes | dev value | Session signing and CSRF. Must be unique and random in production. |
| `JWT_SECRET_KEY` | Yes | dev value | API token signing; must differ from `SECRET_KEY`. |
| `JWT_ACCESS_TOKEN_EXPIRES` | No | `3600` | API token lifetime in seconds. |
| `DATABASE_URL` | No | `sqlite:///instance/tournaments.db` | Database URI. Both `postgres://` and `postgresql://` are normalized to `postgresql+psycopg://`. |
| `SUPERADMIN_USERNAME` | Production | `superadmin` | Initial administrator handle. |
| `SUPERADMIN_PASSWORD` | Production | `adminpassword` (dev only) | Initial administrator password; production requires 12+ characters and rejects the default. |
| `SESSION_COOKIE_SECURE` | Yes in production | `False` | Must be `True` in production. |
| `RATELIMIT_STORAGE_URI` | Production | memory | Shared storage (for example Redis) for rate limits. |
| `COURT_PIN_HMAC_KEY` | Production | none | Secret used to hash Court PINs. |
| `VERCEL` | No | `None` | Set automatically by Vercel; bypasses cold-start schema queries. |
| `UAT_DATABASE_URL` | No | `None` | Secondary URI for staging deployments in GitHub Actions. |

> Variables marked "Production" or introduced for hardening require the code changes tracked in [`SECURITY_REVIEW.md`](SECURITY_REVIEW.md); until then they are documented targets.

### 3.2 Production Safety Checklist
With `APP_ENV=production` the application must refuse to start unless all of the following hold:
1. `SECRET_KEY`, `JWT_SECRET_KEY`, and `COURT_PIN_HMAC_KEY` are set, at least 32 random bytes, distinct, and not documented defaults.
2. `SUPERADMIN_PASSWORD` is set, at least 12 characters, and not `adminpassword`.
3. `DEBUG` is off and `SESSION_COOKIE_SECURE` is `True`.
4. `DATABASE_URL` points to PostgreSQL with `sslmode=require`.
5. A shared rate-limit store is configured.

Also make sure `.env`, `instance/`, and local databases are listed in `.gitignore` and never committed. Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

---

## 4. Database Setup & Initialization

### 4.1 Local SQLite (Default)
When `DATABASE_URL` is omitted, the application automatically initializes SQLite:
* Database file: `instance/tournaments.db`
* Automatically provisions all tables on first startup via `db.create_all()`.
* Automatically bootstraps the initial superadmin credentials (`superadmin` / `adminpassword`).

### 4.2 Supabase PostgreSQL (Cloud / Staging)
To connect to a Supabase or PostgreSQL instance:
1. From the Supabase dashboard (Connect panel) copy the **Transaction pooler** connection string (port 6543) for the app, and the direct or session string (port 5432) for migrations:
   ```ini
   DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@[POOLER-HOST]:6543/postgres"
   ```
   The exact host format comes from the dashboard. The application rewrites `postgresql://` to `postgresql+psycopg://`, disables prepared statements (`prepare_threshold=None`), and enables `pool_pre_ping`. Use a strong, unique database password and never commit the string.
2. Initialize or migrate the target database using the automated provisioning script:
   ```bash
   python scripts/init_uat_db.py
   ```
   This script verifies connectivity, runs Alembic migrations (`flask db upgrade`), synchronizes newly declared columns (`scripts/sync_db_schema.py`), and bootstraps the superadmin account.

---

## 5. Running the Application Locally

Start the local Flask development server:
```bash
python run.py
```
* **Local Web URL:** `http://127.0.0.1:5000`
* **Default Superadmin Login (development only, never in production):**
  * Username: `superadmin`
  * Password: `adminpassword`

---

## 6. Code Quality, Linting & Automated Testing

### 6.1 Code Linting with Ruff
The Baseline Society enforces code style via [Ruff](https://docs.astral.sh/ruff/):
```bash
# Run linter checks
ruff check .

# Automatically apply safe fixes
ruff check . --fix
```

### 6.2 Running Automated Test Suites
Run the 82-test test suite to verify system integrity:
```bash
python -m unittest discover tests -v
```

### 6.3 Security Scans
```bash
bandit -r app -ll
pip-audit -r requirements.txt
```
Run both before every release and in CI.

---

## 7. Cloud Deployment & CI/CD Workflows

### 7.1 Serverless Deployment on Vercel
The Baseline Society is configured for zero-configuration serverless deployment on Vercel via [`vercel.json`](vercel.json):
```json
{
  "builds": [
    {
      "src": "run.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "run.py"
    }
  ]
}
```

### 7.2 GitHub Actions Secrets Setup
For automated deployments via GitHub Actions (`.github/workflows/`), configure the following repository secrets:
* `DATABASE_URL`: Production Supabase connection string.
* `UAT_DATABASE_URL`: Staging Supabase connection string.
* `SECRET_KEY`, `JWT_SECRET_KEY`, `COURT_PIN_HMAC_KEY`: Production secrets (unique per environment).
* `SUPERADMIN_USERNAME`, `SUPERADMIN_PASSWORD`: Production administrator credentials (strong, 12+ characters).

Rules: use separate secrets for UAT and production; give the migration job the only credentials with DDL rights and give the running app a role without `DROP` or audit-table `UPDATE`/`DELETE`; never echo secrets in workflow logs; rotate everything after any suspected exposure; require review before workflows can access production secrets.
