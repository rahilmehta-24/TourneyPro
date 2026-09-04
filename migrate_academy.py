from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        db.session.execute(text('ALTER TABLE tournaments ADD COLUMN is_internal BOOLEAN DEFAULT false'))
        db.session.commit()
        print("Added is_internal to tournaments.")
    except Exception as e:
        db.session.rollback()
        print(f"is_internal might already exist or error occurred: {e}")

    print("Migration complete!")
