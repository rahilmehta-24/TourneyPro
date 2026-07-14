from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        # Alter Participant to add mobile
        db.session.execute(text("ALTER TABLE participants ADD COLUMN mobile VARCHAR(20);"))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error adding mobile to participants: {e}")

    try:
        # Alter Registration to drop NOT NULL on user_id and player_id
        db.session.execute(text("ALTER TABLE registrations ALTER COLUMN user_id DROP NOT NULL;"))
        db.session.execute(text("ALTER TABLE registrations ALTER COLUMN player_id DROP NOT NULL;"))
        db.session.commit()
        print("Registration constraints updated.")
    except Exception as e:
        db.session.rollback()
        print(f"Error updating Registration constraints: {e}")
