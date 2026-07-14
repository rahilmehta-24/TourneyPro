from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.connect() as conn:
        columns = [
            ("registration_no", "VARCHAR(100)"),
            ("dob", "DATE"),
            ("email", "VARCHAR(120)"),
            ("contact_number", "VARCHAR(50)"),
            ("height", "VARCHAR(50)"),
            ("weight", "VARCHAR(50)"),
            ("blood_group", "VARCHAR(10)"),
            ("nationality", "VARCHAR(100)"),
            ("address", "TEXT"),
            ("coach", "VARCHAR(100)"),
            ("academy", "VARCHAR(100)"),
            ("registration_details", "TEXT"),
            ("registration_date", "DATE"),
            ("registration_validity", "DATE"),
            ("current_status", "VARCHAR(50) DEFAULT 'Active'")
        ]
        
        for col_name, col_type in columns:
            try:
                conn.execute(text(f"ALTER TABLE players ADD COLUMN {col_name} {col_type};"))
                print(f"Added {col_name} to players")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                
        conn.commit()
