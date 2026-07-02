# Tournament Manager

A robust Flask-based web application for managing sports and gaming tournaments. This application supports various tournament formats including Single Elimination, Double Elimination, Round Robin, and Group Stages.

## Features

- **Tournament Management**

  - Create and manage multiple tournaments
  - Modern, responsive UI with premium sports styling
  - Dynamic formatting where different categories can run different formats simultaneously

- **Formats Supported**
  
  - 🏆 Single Elimination (Knockout)
  - 🎪 Group Stage + Knockout (with Intelligent "Lucky Loser" logic)
  - 🔄 Round Robin (League)
  - PDF Export of brackets

- **Categories & Match Settings**

  - Bulk participant registration (comma-separated lists)
  - Independent match formats for each category (e.g., Men's Singles, Mixed Doubles)
  - "Total Games" scoring mode (e.g., 6-1, 5-2 valid sums)
  - Legacy set-based scoring (e.g., Best of 3 sets, 6 games per set)

- **Match Management**

  - Interactive bracket view
  - Seamless match reporting and score tracking
  - Automatic progression of winners
  - Leaderboards and statistics
  - Cross-tab session synchronization (logging out in one tab instantly safely refreshes others)

## Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLite (SQLAlchemy ORM)
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **PDF Generation**: xhtml2pdf

## Project Structure

```
test/
├── app/
│   ├── algorithms/      # Tournament logic (brackets, seeding)
│   ├── routes/          # Blueprint definitions (endpoints)
│   ├── templates/       # HTML templates (Jinja2)
│   ├── models.py        # Database models
│   └── __init__.py      # App factory and initialization
├── instance/            # SQLite database location
├── config.py            # Configuration settings
├── run.py               # Entry point
└── requirements.txt     # Dependencies
```

## Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd test
   ```
2. **Create a virtual environment**

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application**

   ```bash
   python run.py
   ```
5. **Access the app**
   Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

1. **Create a Tournament**: Click "Create Tournament" on the home page.
2. **Add Categories**: Once inside a tournament, create categories (e.g., "Singles").
3. **Add Participants**: Add players manually or import them.
4. **Start Tournament**: When ready, click "Start Category" to generate the bracket.
5. **Manage Matches**: Click on matches to report scores and advance winners.
