from app.models import db
from sqlalchemy import text
from app import create_app

app = create_app()

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE participants ADD COLUMN player2_id INTEGER REFERENCES players(id);"))
        db.session.commit()
        print("Successfully added player2_id to PostgreSQL!")
    except Exception as e:
        print("Error:", e)
