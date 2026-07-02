from sqlalchemy import text
from app.models import db
from app import create_app

app = create_app()

with app.app_context():
    with db.engine.begin() as conn:
        try:
            # Add allow_lucky_losers
            conn.execute(text("ALTER TABLE categories ADD COLUMN allow_lucky_losers BOOLEAN DEFAULT FALSE"))
            print("Added allow_lucky_losers")
        except Exception as e:
            print(f"allow_lucky_losers might already exist: {e}")

        try:
            # Add max_players_per_team
            conn.execute(text("ALTER TABLE categories ADD COLUMN max_players_per_team INTEGER"))
            print("Added max_players_per_team")
        except Exception as e:
            print(f"max_players_per_team might already exist: {e}")

        try:
            # Add total_games
            conn.execute(text("ALTER TABLE categories ADD COLUMN total_games INTEGER"))
            print("Added total_games")
        except Exception as e:
            print(f"total_games might already exist: {e}")
