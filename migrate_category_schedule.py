"""Migration: Add scheduling fields to Category model"""
from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    conn = db.engine.connect()
    trans = conn.begin()
    try:
        for col_def in [
            "ALTER TABLE categories ADD COLUMN IF NOT EXISTS num_courts INTEGER DEFAULT 1",
            "ALTER TABLE categories ADD COLUMN IF NOT EXISTS court_names TEXT",
            "ALTER TABLE categories ADD COLUMN IF NOT EXISTS start_date_time TIMESTAMP",
            "ALTER TABLE categories ADD COLUMN IF NOT EXISTS avg_match_duration INTEGER DEFAULT 60",
        ]:
            conn.execute(text(col_def))
            print(f"✓ {col_def[:60]}...")

        trans.commit()
        print("\n✅ Category migration complete!")
    except Exception as e:
        trans.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        conn.close()
