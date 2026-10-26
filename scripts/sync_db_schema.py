import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlalchemy as sa
from config import Config
from app import create_app
from app.domain.models import db


def sync_schema():
    """Compare SQLAlchemy models (UAT code) against the target database (Supabase)

    and automatically apply any missing tables or columns.
    """
    print("=" * 60)
    print("TourneyPro Database Schema Verifier & Sync Engine")
    print("=" * 60)

    db_url = Config.SQLALCHEMY_DATABASE_URI
    if not db_url or "sqlite" in db_url:
        print("[Info] Active database is SQLite or unspecified. Schema sync skipped.")
        return 0

    # Ensure engine options match production
    engine_options = {}
    if db_url.startswith("postgresql"):
        engine_options["connect_args"] = {"prepare_threshold": None}
        engine_options["pool_pre_ping"] = True

    app = create_app()
    with app.app_context():
        engine = sa.create_engine(db_url, **engine_options)
        inspector = sa.inspect(engine)

        db_tables = set(inspector.get_table_names())
        model_tables = db.metadata.tables

        added_tables = []
        added_columns = []

        # 1. Check for missing tables
        for table_name, table in model_tables.items():
            if table_name not in db_tables:
                print(f"[Sync] Missing table detected: '{table_name}'. Creating table...")
                try:
                    table.create(engine)
                    added_tables.append(table_name)
                    print(f"[Sync] Successfully created table: '{table_name}'")
                except Exception as e:
                    print(f"[Error] Failed to create table '{table_name}': {e}", file=sys.stderr)
                    return 1

        # Refresh tables list after table creations
        inspector = sa.inspect(engine)
        db_tables = set(inspector.get_table_names())

        # 2. Check for missing columns in existing tables
        for table_name, table in model_tables.items():
            if table_name not in db_tables:
                continue

            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}

            for col in table.columns:
                if col.name not in existing_cols:
                    print(f"[Sync] Missing column detected: {table_name}.{col.name} ({col.type}). Adding...")
                    try:
                        col_type_sql = col.type.compile(engine.dialect)

                        # Determine default value clause
                        default_sql = ""
                        if col.server_default is not None:
                            arg = col.server_default.arg
                            default_text = arg.text if hasattr(arg, "text") else str(arg)
                            default_sql = f" DEFAULT {default_text}"
                        elif col.default is not None and hasattr(col.default, "arg") and not callable(col.default.arg):
                            val = col.default.arg
                            if isinstance(val, bool):
                                default_sql = f" DEFAULT {'TRUE' if val else 'FALSE'}"
                            elif isinstance(val, (int, float)):
                                default_sql = f" DEFAULT {val}"
                            elif isinstance(val, str):
                                default_sql = f" DEFAULT '{val}'"

                        # Keep additions nullable to prevent failing on tables with existing rows
                        null_sql = ""
                        if not col.nullable and default_sql:
                            null_sql = " NOT NULL"

                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type_sql}{default_sql}{null_sql}"
                        with engine.begin() as conn:
                            conn.execute(sa.text(sql))

                        added_columns.append(f"{table_name}.{col.name}")
                        print(f"[Sync] Successfully added column: {table_name}.{col.name}")
                    except Exception as e:
                        print(f"[Error] Failed to add column {table_name}.{col.name}: {e}", file=sys.stderr)
                        return 1

        # 3. Bootstrap superadmin if database has no users
        try:
            from app.web.controllers.auth import bootstrap_superadmin
            bootstrap_superadmin()
        except Exception as e:
            print(f"[Notice] Superadmin bootstrap check: {e}")

        print("-" * 60)
        if added_tables or added_columns:
            print(f"[Success] Schema sync complete: Added {len(added_tables)} tables, {len(added_columns)} columns.")
            if added_tables:
                print(f"  - New Tables: {', '.join(added_tables)}")
            if added_columns:
                print(f"  - New Columns: {', '.join(added_columns)}")
        else:
            print("[Success] All tables and columns are 100% in sync with models. No additions required.")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(sync_schema())
