# TourneyPro — Developer & Deployment Setup Guide (SETUP.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`PLAN.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/PLAN.md), [`README.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/README.md), and [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md)  
**Target Environments:** Local Workstations (macOS, Linux, Windows), UAT Staging, and Production (Vercel + Supabase)  
**Last Updated:** October 2026  

---

## 1. System Prerequisites

Before setting up TourneyPro, verify that your development machine has the following tools installed:

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
| `FLASK_ENV` | Yes | `development` | Environment mode (`development` or `production`). |
| `SECRET_KEY` | Yes | `dev-secret-key-change-in-production` | Secret cryptographic key for session signing and CSRF tokens. |
| `DATABASE_URL` | No | `sqlite:///instance/tournaments.db` | Target database connection URI. If omitted or commented out, defaults to local SQLite. |
| `SUPERADMIN_USERNAME` | No | `superadmin` | Initial bootstrapped administrator handle. |
| `SUPERADMIN_PASSWORD` | No | `adminpassword` | Initial bootstrapped administrator password. |
| `VERCEL` | No | `None` | Set automatically by Vercel; when detected, bypasses cold-start schema queries. |
| `UAT_DATABASE_URL` | No | `None` | Secondary URI for staging database deployments in GitHub Actions. |

---

## 4. Database Setup & Initialization

### 4.1 Local SQLite (Default)
When `DATABASE_URL` is omitted, the application automatically initializes SQLite:
* Database file: `instance/tournaments.db`
* Automatically provisions all tables on first startup via `db.create_all()`.
* Automatically bootstraps the initial superadmin credentials (`superadmin` / `adminpassword`).

### 4.2 Supabase PostgreSQL (Cloud / Staging)
To connect to a Supabase or PostgreSQL instance:
1. Obtain the **Session Mode** or **Transaction Mode (PgBouncer)** connection string from your Supabase Dashboard:
   ```ini
   DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
   ```
2. Initialize or migrate the target database using the automated provisioning script:
   ```bash
   python scripts/init_uat_db.py
   ```
   This script verifies connectivity, runs Alembic migrations (`flask db upgrade`), synchronizes any newly declared columns (`scripts/sync_db_schema.py`), and bootstraps the superadmin account.

---

## 5. Running the Application Locally

Start the local Flask development server:
```bash
python run.py
```
* **Local Web URL:** `http://127.0.0.1:5000`
* **Default Superadmin Login:**
  * Username: `superadmin`
  * Password: `adminpassword`

---

## 6. Code Quality, Linting & Automated Testing

### 6.1 Code Linting with Ruff
TourneyPro enforces code style via [Ruff](https://docs.astral.sh/ruff/):
```bash
# Run linter checks
ruff check .

# Automatically apply safe fixes
ruff check . --fix
```

### 6.2 Running Automated Test Suites
Run the 72-test test suite to verify system integrity:
```bash
python -m unittest discover tests -v
```

---

## 7. Cloud Deployment & CI/CD Workflows

### 7.1 Serverless Deployment on Vercel
TourneyPro is configured for zero-configuration serverless deployment on Vercel via [`vercel.json`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/vercel.json):
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
* `SECRET_KEY`: Production session key.
* `SUPERADMIN_USERNAME`: Production superadmin handle.
* `SUPERADMIN_PASSWORD`: Production superadmin password.
