# -*- coding: utf-8 -*-
"""
Database migration script to add missing columns
Run this to update existing database schema
"""
import sqlite3
import os

db_path = 'instance/tournaments.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== Migrating tournaments table ===")
cursor.execute("PRAGMA table_info(tournaments)")
columns = [col[1] for col in cursor.fetchall()]

if 'has_categories' not in columns:
    print("Adding has_categories column...")
    cursor.execute("ALTER TABLE tournaments ADD COLUMN has_categories BOOLEAN DEFAULT 0")
    conn.commit()
    print("[OK] Added has_categories column")
else:
    print("[OK] has_categories column already exists")

if 'tournament_type' not in columns:
    print("Adding tournament_type column...")
    cursor.execute("ALTER TABLE tournaments ADD COLUMN tournament_type VARCHAR(20) DEFAULT 'single_stage'")
    conn.commit()
    print("[OK] Added tournament_type column")
else:
    print("[OK] tournament_type column already exists")

print("\n=== Migrating participants table ===")
cursor.execute("PRAGMA table_info(participants)")
columns = [col[1] for col in cursor.fetchall()]

if 'category_id' not in columns:
    print("Adding category_id column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN category_id INTEGER")
    conn.commit()
    print("[OK] Added category_id column")
else:
    print("[OK] category_id column already exists")

if 'group_id' not in columns:
    print("Adding group_id column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN group_id INTEGER")
    conn.commit()
    print("[OK] Added group_id column")
else:
    print("[OK] group_id column already exists")

if 'manual_seed' not in columns:
    print("Adding manual_seed column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN manual_seed INTEGER")
    conn.commit()
    print("[OK] Added manual_seed column")
else:
    print("[OK] manual_seed column already exists")

if 'final_rank' not in columns:
    print("Adding final_rank column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN final_rank INTEGER")
    conn.commit()
    print("[OK] Added final_rank column")
else:
    print("[OK] final_rank column already exists")

if 'group_wins' not in columns:
    print("Adding group_wins column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN group_wins INTEGER DEFAULT 0")
    conn.commit()
    print("[OK] Added group_wins column")
else:
    print("[OK] group_wins column already exists")

if 'group_losses' not in columns:
    print("Adding group_losses column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN group_losses INTEGER DEFAULT 0")
    conn.commit()
    print("[OK] Added group_losses column")
else:
    print("[OK] group_losses column already exists")

if 'group_points' not in columns:
    print("Adding group_points column...")
    cursor.execute("ALTER TABLE participants ADD COLUMN group_points INTEGER DEFAULT 0")
    conn.commit()
    print("[OK] Added group_points column")
else:
    print("[OK] group_points column already exists")

print("\n=== Migrating matches table ===")
cursor.execute("PRAGMA table_info(matches)")
columns = [col[1] for col in cursor.fetchall()]

if 'category_id' not in columns:
    print("Adding category_id column...")
    cursor.execute("ALTER TABLE matches ADD COLUMN category_id INTEGER")
    conn.commit()
    print("[OK] Added category_id column")
else:
    print("[OK] category_id column already exists")

if 'group_id' not in columns:
    print("Adding group_id column...")
    cursor.execute("ALTER TABLE matches ADD COLUMN group_id INTEGER")
    conn.commit()
    print("[OK] Added group_id column")
else:
    print("[OK] group_id column already exists")

if 'bracket_type' not in columns:
    print("Adding bracket_type column...")
    cursor.execute("ALTER TABLE matches ADD COLUMN bracket_type VARCHAR(20) DEFAULT 'main'")
    conn.commit()
    print("[OK] Added bracket_type column")
else:
    print("[OK] bracket_type column already exists")

if 'match_type' not in columns:
    print("Adding match_type column...")
    cursor.execute("ALTER TABLE matches ADD COLUMN match_type VARCHAR(20) DEFAULT 'knockout'")
    conn.commit()
    print("[OK] Added match_type column")
else:
    print("[OK] match_type column already exists")

conn.close()
print("\n[SUCCESS] Database migration completed successfully!")
