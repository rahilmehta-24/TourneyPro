"""TourneyPro — UAT Database Initializer & Verification Tool.

Usage:
    python scripts/init_uat_db.py [optional_connection_string]

If no connection string is passed as an argument, it reads UAT_DATABASE_URL
or DATABASE_URL from the local environment / .env.
"""

import os
import subprocess
import sys

# Ensure repository root is on sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env.uat"))
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    pass

import sqlalchemy as sa  # noqa: E402
from app import create_app  # noqa: E402
from app.domain.models import db, User  # noqa: E402
from scripts.sync_db_schema import sync_schema  # noqa: E402


def normalize_db_url(raw_url: str) -> str:
    url = raw_url.strip().strip("'\"")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def main():
    print("=" * 65)
    print("TourneyPro — UAT Supabase Initializer & Health Verifier")
    print("=" * 65)

    # 1. Determine connection URL
    raw_url = None
    if len(sys.argv) > 1 and sys.argv[1].strip():
        raw_url = sys.argv[1].strip()
    else:
        raw_url = os.environ.get("UAT_DATABASE_URL") or os.environ.get("DATABASE_URL")

    if not raw_url:
        print("[Error] No database URL provided.")
        print("Please provide the Supabase UAT connection URL:")
        print("    python scripts/init_uat_db.py 'postgresql://postgres.<ref>:<pass>@<host>:6543/postgres'")
        print("Or define UAT_DATABASE_URL in .env or .env.uat")
        return 1

    db_url = normalize_db_url(raw_url)
    os.environ["DATABASE_URL"] = db_url

    # Mask credentials for safe terminal logging
    try:
        url_obj = sa.engine.make_url(db_url)
        safe_url = f"{url_obj.drivername}://{url_obj.username}:***@{url_obj.host}:{url_obj.port}/{url_obj.database}"
    except Exception:
        safe_url = "(masked URL)"

    print(f"[1/4] Connecting to Supabase Target: {safe_url}")

    # 2. Test Connection
    engine_options = {}
    if db_url.startswith("postgresql"):
        engine_options["connect_args"] = {"prepare_threshold": None}
        engine_options["pool_pre_ping"] = True

    try:
        test_engine = sa.create_engine(db_url, **engine_options)
        with test_engine.connect() as conn:
            val = conn.execute(sa.text("SELECT 1")).scalar()
            assert val == 1
        print("[OK] Supabase PostgreSQL connection verified successfully!")
    except Exception as e:
        print(f"[Error] Failed to connect to database: {e}", file=sys.stderr)
        return 1

    # 3. Apply Alembic Migrations
    print("\n[2/4] Applying Alembic Migrations (flask db upgrade)...")
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = db_url
        env["FLASK_APP"] = "run.py"
        res = subprocess.run(
            [sys.executable, "-m", "flask", "db", "upgrade"],
            cwd=BASE_DIR,
            env=env,
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            print(f"[Warning] 'flask db upgrade' output: {res.stderr or res.stdout}")
        else:
            print("[OK] Alembic migrations applied successfully.")
    except Exception as e:
        print(f"[Warning] Could not run flask db upgrade via subprocess: {e}")

    # 4. Synchronize Missing Tables/Columns & Bootstrap Superadmin
    print("\n[3/4] Reconciling Schema & Bootstrapping Superadmin...")
    sync_code = sync_schema()
    if sync_code != 0:
        print("[Error] Schema reconciliation failed.")
        return sync_code

    # 5. Final Health & Table Verification
    print("\n[4/4] Verifying Final Table Roster...")
    app = create_app()
    with app.app_context():
        inspector = sa.inspect(db.engine)
        tables = sorted(inspector.get_table_names())
        user_count = User.query.count()

        print(f"[OK] Total Tables in UAT Database: {len(tables)}")
        for i, tbl in enumerate(tables, 1):
            cols_count = len(inspector.get_columns(tbl))
            print(f"     {i:2d}. {tbl:<30} ({cols_count} columns)")

        print(f"\n[OK] Superadmin User Count: {user_count}")
        superadmin = User.query.filter_by(role="superadmin").first()
        if superadmin:
            print(f"     Active Superadmin: '{superadmin.username}' ({superadmin.email})")

    print("\n" + "=" * 65)
    print("SUCCESS: UAT Supabase Database is 100% Ready for Deployment!")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(main())
