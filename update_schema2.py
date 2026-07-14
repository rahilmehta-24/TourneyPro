from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE participants ADD COLUMN gender VARCHAR(20);"))
        db.session.execute(text("ALTER TABLE participants ADD COLUMN dob DATE;"))
        db.session.commit()
        print("gender and dob added to participants.")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
