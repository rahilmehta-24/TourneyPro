# TourneyPro - Tournament Manager

A robust, production-ready Flask-based web application for managing sports and gaming tournaments. This application supports a fully-featured tournament lifecycle including participant management, dynamic bracket generation, and live interactive score reporting.

## Key Features

- **Advanced Tournament Logic**
  - **Single & Doubles Elimination (Knockout):** Automatic bracket generation, intelligent Bye placements for non-power-of-2 participant counts, and explicit seeding support.
  - **Round Robin (League):** Generates exhaustive grid match-ups. Ranks players based on total cumulative points across all matches. Can dynamically feed the top players into a Knockout Stage.
  - **Multi-Category Architecture:** A single tournament can host dozens of distinct events (e.g., Men's Singles, Under-15s, Mixed Doubles) all running completely different formats independently.

- **Match & Score Management**
  - Interactive grid and bracket UI for visualizing live progress.
  - Two distinct scoring modes: "Total Games Scoring" (cumulative numeric points) or "Standard Tennis Set Scoring" (traditional Best-of-3 or Best-of-5 sets with tiebreaks).
  - Admin controls for manual result reporting, progressing winners, and resetting faulty brackets.

- **Global Player Statistics**
  - Maintains a centralized Player Registry across all tournaments.
  - Dynamically calculates lifetime wins, losses, win rates, and podium finishes.
  - Real-time Leaderboards synchronized with live bracket results.

- **Enterprise & Security**
  - PostgreSQL Database backend optimized for relational integrity (Foreign Key enforcement).
  - Role-based Access Control (RBAC): SuperAdmin, Admin, and public viewer segregation.
  - PDF Export of brackets using `xhtml2pdf`.

## Tech Stack

- **Backend**: Python 3, Flask, SQLAlchemy ORM, psycopg2
- **Database**: PostgreSQL (Production) / SQLite (Development)
- **Frontend**: HTML5, CSS3, Vanilla JS (No heavyweight frontend frameworks)
- **Styling**: Custom CSS with CSS Variables, Dark Mode, and modern UI paradigms (Glassmorphism, Gradients, Shadows).

## Project Structure

```
TourneyPro/
├── app/
│   ├── algorithms/      # Bracket generation algorithms (Single Elim, Round Robin, Group Stage)
│   ├── routes/          # Flask Blueprints (Auth, Tournament, Category, Match, Leaderboard)
│   ├── templates/       # Jinja2 HTML Templates
│   ├── static/          # CSS, JS, and Images
│   ├── models.py        # SQLAlchemy Database Models
│   ├── constants.py     # Format definitions and system constants
│   ├── leaderboard_logic.py # Centralized stats recalculation module
│   └── __init__.py      # App factory and initialization
├── config.py            # Environment Configuration
├── run.py               # WSGI Entry point
├── RULEBOOK.md          # Comprehensive manual and rules engine
└── requirements.txt     # Python Dependencies
```

## Setup & Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TourneyPro
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Configure your `DATABASE_URL` and `SECRET_KEY` in `config.py` or `.env`.

5. **Run the application**
   ```bash
   python run.py
   ```
   Open your browser and navigate to `http://127.0.0.1:5000`

## Documentation
Please refer to the [RULEBOOK.md](RULEBOOK.md) file included in the root directory for an exhaustive breakdown of the mathematical algorithms, bracket lifecycle behaviors, and scoring logic that powers the system.
