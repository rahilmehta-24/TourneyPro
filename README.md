# Tournament Manager

A robust Flask-based web application for managing sports and gaming tournaments. This application supports various tournament formats including Single Elimination, Double Elimination, Round Robin, and Group Stages.

## Features

- **Tournament Management**
  - Create and manage multiple tournaments
  - Customizable formats (Single/Double Elimination, Round Robin, Group Stage)
  - Automatic bracket generation
  - Seeding management
  - PDF Export of brackets

- **Categories**
  - Support for multiple categories per tournament (e.g., Men's, Women's, Doubles)
  - Independent formats for each category

- **Match Management**
  - Interactive bracket view
  - Match reporting and score tracking
  - Automatic progression of winners
  - Leaderboards and statistics

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
