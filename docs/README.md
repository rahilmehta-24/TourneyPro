# TourneyPro — Advanced Tournament Management Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.1-black.svg)](https://flask.palletsprojects.com/)
[![ORM](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-red.svg)](https://www.sqlalchemy.org/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20PostgreSQL-green.svg)](https://supabase.com/)
[![Tests](https://img.shields.io/badge/Tests-72%20Passing-brightgreen.svg)](../tests/)
[![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-purple.svg)](https://docs.astral.sh/ruff/)

**TourneyPro** is an enterprise-grade, full-lifecycle tournament management web platform engineered for racquet sports (Lawn Tennis, Pickleball, Badminton, Padel, Table Tennis) and competitive esports. It replaces paper draw sheets, complex spreadsheets, and manual WhatsApp group coordination with an automated, mathematical tournament operating system.

---

## 📖 Master Documentation Directory

TourneyPro features an exhaustive, interconnected documentation suite. Every document serves as a specialized source of truth:

| Document | Description & Focus |
| :--- | :--- |
| **[`PRD.md`](PRD.md)** | **Product Requirements Document:** Target personas, tournament formats, scoring modes, court scheduling constraints, and operational goals. |
| **[`DESIGN.md`](DESIGN.md)** | **System & UX/UI Design:** Visual design system, dark-mode tokens, interactive SVG bracket connectors, and component specifications. |
| **[`ARCHITECTURE.md`](ARCHITECTURE.md)** | **Technical Architecture:** Application factory pattern, blueprint layout, service layer, and data flow sequence diagrams. |
| **[`DATABASE.md`](DATABASE.md)** | **Database Schema & Relational Models:** Comprehensive breakdown of all 17 tables, columns, foreign keys, and migration rules. |
| **[`API.md`](API.md)** | **RESTful API Specification:** JSON contracts, JWT bearer token authentication, request/response models, and live score polling. |
| **[`AGENTS.md`](AGENTS.md)** | **AI & Developer Agent Operating Manual:** Rules of engagement, coding guidelines, security guardrails, and automated checks for AI agents. |
| **[`PLAN.md`](PLAN.md)** | **Phased Delivery Roadmap:** Milestones, completed Phase 1 capabilities, active Phase 2 items, and upcoming Phase 3 features. |
| **[`SETUP.md`](SETUP.md)** | **Installation & Environment Guide:** Local macOS/Linux/Windows setup, virtual environments, environment variables, and initial database bootstrapping. |
| **[`FEATURES.md`](FEATURES.md)** | **Functional Feature Matrix:** Detailed algorithmic breakdown of byes, seeding, 3-rubber team ties, and court scheduling. |
| **[`AUTH.md`](AUTH.md)** | **Authentication & Security Architecture:** Session cookies, CSRF defense, JWT API tokens, RBAC roles, and BOLA/IDOR protection. |
| **[`MCP.md`](MCP.md)** | **Model Context Protocol Specification:** MCP tools, resources, and server integration for AI developer agents. |
| **[`INTEGRATIONS.md`](INTEGRATIONS.md)** | **External Services & Infrastructure:** Supabase PostgreSQL, Vercel serverless, xhtml2pdf vector generation, and future Stripe/Twilio integrations. |
| **[`TESTING.md`](TESTING.md)** | **Quality Assurance & Testing Strategy:** 72-test automated suite inventory, SQLite test fixtures, and GitHub Actions CI gates. |
| **[`DEBUGGING.md`](DEBUGGING.md)** | **Troubleshooting & Diagnostics Playbook:** Runbooks for database connection pooling, Alembic batch desync, and court scheduling conflicts. |

---

## ⚡ Key Platform Capabilities

### 1. Mathematical Tournament Formats
* **Single & Doubles Elimination:** Automatic bracket balancing for non-power-of-2 entries ($2^{\lceil \log_2 N \rceil}$), intelligent Bye placement for top seeds, and explicit seed overrides.
* **Round Robin Leagues:** Exhaustive fixture matrices with cumulative game/point tracking. Supports 1-click promotion of top finishers into Knockout stages.
* **Group Stage Team Leagues:** Multi-rubber tie format (3 rubbers per match: Singles 1, Doubles, Singles 2) with the $T=7$ summation rule, 21-game tie caps, first-to-11 win conditions, and Mode A (manual chit draw) / Mode B (auto-balanced tier draft) team assembly.

### 2. Intelligent Court Scheduling & Order of Play
* Constraint-satisfaction scheduling engine respecting multi-day tournament calendars and daily operating hours (`08:00` to `20:00`).
* **Progression Locks:** Downstream matches are strictly locked until feeder matches complete.
* **Player Conflict Prevention:** Prevents athletes competing in multiple categories from being scheduled on two courts simultaneously, enforcing a mandatory 30-minute rest buffer between matches.

### 3. Smart Guest Registration & Player Ecosystem
* **Zero-Friction Registration:** Guest athletes can register without creating user accounts. The system provisions a global `Player` profile and links entries to internal tracking accounts.
* **Global Player Registry:** Tracks lifetime statistics (Matches Played, Won, Lost, Win %, Career Podiums, and Ranking Points) across all tournaments.

### 4. Vector PDF Export Suite
* Downloadable, publication-ready vector PDF documents rendered via `xhtml2pdf` and `reportlab`:
  * **Dynamic Draw Sheets:** Complete brackets with seeds, scores, and progression connectors.
  * **Order of Play:** Comprehensive daily court schedule matrices with start times and durations.
  * **Participant Rosters:** Player rosters, payment tracking, and check-in sheets.

### 5. First-Class Mobile Web App Experience
* **Native Smartphone UX:** 100% responsive architecture across iOS Safari and Android Chrome (320px–430px viewports) with zero regression or alteration to the desktop interface.
* **Knockout Bracket Touch Navigation:** Hardware-accelerated touch-drag panning (`touchstart`/`touchmove`/`touchend`) and round-by-round pill navigation tabs (`Round of 16` → `Quarterfinals` → `Semifinals` → `Finals`) that maintain full SVG connector geometry.
* **Mobile Bottom-Sheet Score Dialog:** Transforms match score reporting into an app-like bottom sheet on `≤ 640px` screens with dynamic viewport units (`dvh`), sticky action footers, and native numeric keypads (`inputmode="numeric"`).
* **1-Tap Mobile UPI Intent:** Direct `upi://pay` deep linking into installed UPI apps (Google Pay, PhonePe, Paytm) and 1-tap clipboard copying for frictionless on-device registrations.
* **Thumb Navigation & Safe Areas:** Off-canvas slide-out navigation drawer with backdrop blur, sticky bottom navigation quick bar, and safe-area notch compensation (`viewport-fit=cover`).

---

## 🛠️ Technology Stack

* **Runtime:** Python 3.12 (tested on Python 3.12.8)
* **Web Framework:** Flask 3.1.3 (Werkzeug 3.1.8)
* **ORM & Database:** SQLAlchemy 2.0.51, Flask-SQLAlchemy 3.1.1, psycopg 3.3.4
* **Database Dual Strategy:** SQLite (Development / Testing) & PostgreSQL / Supabase (Production)
* **Migrations:** Flask-Migrate 4.1.0, Alembic 1.20.0
* **API & Security:** Flask-JWT-Extended 4.7.4, Flask-WTF 1.3.0, WTForms 3.2.2
* **Frontend:** Vanilla HTML5, CSS3 (Design Tokens & Glassmorphism), Vanilla JavaScript
* **PDF Engine:** xhtml2pdf 0.2.17, ReportLab 4.5.1
* **Linter & Tests:** Ruff 0.15+, Python `unittest` (72 automated tests)

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* Python 3.12 or higher installed.
* Git installed.

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd TourneyPro

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root (or copy `.env.example`):
```ini
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
SUPERADMIN_USERNAME=superadmin
SUPERADMIN_PASSWORD=adminpassword
# Leave DATABASE_URL omitted or commented out to use local SQLite:
# DATABASE_URL=sqlite:///instance/tournaments.db
```

### 4. Run the Application
```bash
python run.py
```
Open your browser and navigate to `http://127.0.0.1:5000`. Log in with `superadmin` / `adminpassword` to access administrative controls.

### 5. Run the Automated Test Suite
```bash
python -m unittest discover tests -v
```

---

## 📂 Project Structure

```
TourneyPro/
├── app/
│   ├── api/                     # Headless RESTful API endpoints (/api/v1/)
│   ├── core/                    # Global constants and configuration helpers
│   ├── domain/                  # SQLAlchemy models and Marshmallow schemas
│   ├── services/
│   │   ├── format_engine/       # Bracket algorithms (Knockout, Round Robin, Team League)
│   │   ├── pdf/                 # Vector PDF draw, schedule, and roster adapters
│   │   ├── utils/               # Court scheduler, validation, and audit helpers
│   │   ├── leaderboard.py       # Live statistics and ranking calculations
│   │   └── tennis_logic.py      # Tennis score parsing and tiebreak rules
│   ├── web/
│   │   ├── controllers/         # Flask modular Blueprints (tournament, category, auth, etc.)
│   │   ├── static/              # Vanilla CSS stylesheets, JS scripts, and brand assets
│   │   └── templates/           # Server-side rendered Jinja2 templates
│   └── __init__.py              # Flask Application Factory (create_app)
├── instance/                    # Local SQLite database files
├── migrations/                  # Alembic database migration revisions
├── scripts/                     # Operational scripts (sync_db_schema.py, init_uat_db.py)
├── tests/                       # 72 automated unit and integration tests
├── config.py                    # Application configuration and connection pooling
├── requirements.txt             # Python dependencies
├── ruff.toml                    # Ruff linter rules and formatting configuration
├── run.py                       # WSGI entry point
└── vercel.json                  # Serverless deployment configuration
```

---

## 📄 License
TourneyPro is proprietary software. All rights reserved.
