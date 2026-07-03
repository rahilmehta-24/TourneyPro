from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    result = db.session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='participants';"))
    columns = [row[0] for row in result]
    print("Participant columns:", columns)
