import os
from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

def add_columns():
    with engine.connect() as conn:
        print("Adding entry_fee to categories table...")
        try:
            conn.execute(text("ALTER TABLE categories ADD COLUMN entry_fee FLOAT DEFAULT 0.0"))
            conn.commit()
            print("Successfully added entry_fee to categories.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

        print("\nAdding payment_status to registrations table...")
        try:
            conn.execute(text("ALTER TABLE registrations ADD COLUMN payment_status VARCHAR(20) DEFAULT 'pending'"))
            conn.commit()
            print("Successfully added payment_status to registrations.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

        print("\nAdding amount_due to registrations table...")
        try:
            conn.execute(text("ALTER TABLE registrations ADD COLUMN amount_due FLOAT DEFAULT 0.0"))
            conn.commit()
            print("Successfully added amount_due to registrations.")
        except Exception as e:
            print(f"Error (might already exist): {e}")

if __name__ == "__main__":
    add_columns()
    print("\nDatabase migration complete!")
