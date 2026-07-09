import sqlite3
import os

from app import create_app, db

db_path = 'instance/tournaments.db'

# 1. Backup users if DB exists
users = None
if os.path.exists(db_path):
    print("Backing up users...")
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        cur.execute("SELECT * FROM users")
        cols = [description[0] for description in cur.description]
        users = [dict(zip(cols, row)) for row in cur.fetchall()]
        con.close()
        os.remove(db_path)
        print("Old database removed.")
    except Exception as e:
        print(f"Error backing up users: {e}")

# 2. Recreate schema
app = create_app()
with app.app_context():
    db.create_all()
    print("New schema created.")

# 3. Restore users
if users:
    print("Restoring users...")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    for u in users:
        placeholders = ', '.join(['?'] * len(u))
        columns = ', '.join(u.keys())
        sql = f"INSERT INTO users ({columns}) VALUES ({placeholders})"
        cur.execute(sql, list(u.values()))
    con.commit()
    con.close()
    print("Users restored.")
