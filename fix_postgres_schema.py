from app import create_app, db
from sqlalchemy import text
import traceback

app = create_app()
with app.app_context():
    try:
        with db.engine.connect() as conn:
            # Add user_id to tournaments if it doesn't exist
            try:
                conn.execute(text("ALTER TABLE tournaments ADD COLUMN user_id INTEGER REFERENCES users(id);"))
                print("Added user_id to tournaments")
            except Exception as e:
                print(f"Skipping tournaments user_id: {e}")
                
            # Add user_id to players if it doesn't exist
            try:
                conn.execute(text("ALTER TABLE players ADD COLUMN user_id INTEGER REFERENCES users(id);"))
                print("Added user_id to players")
            except Exception as e:
                print(f"Skipping players user_id: {e}")
                
            conn.commit()
            print("Successfully migrated Postgres database!")
    except Exception as e:
        print(f"Error connecting: {e}")
        traceback.print_exc()
