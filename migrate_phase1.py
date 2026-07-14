from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE players ADD COLUMN avatar_url VARCHAR(500);"))
            print("Added avatar_url to players")
        except Exception as e:
            print(f"avatar_url error: {e}")
            
        try:
            conn.execute(text("ALTER TABLE players ADD COLUMN bio TEXT;"))
            print("Added bio to players")
        except Exception as e:
            print(f"bio error: {e}")
            
        conn.commit()
