from app import create_app
from app.models import db, User
import os
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Altering table...")
    db.session.execute(text("ALTER TABLE users ALTER COLUMN password_hash TYPE VARCHAR(256);"))
    db.session.commit()
    
    username = os.environ.get('SUPERADMIN_USERNAME', 'superadmin')
    password = os.environ.get('SUPERADMIN_PASSWORD', 'adminpassword')
    
    superadmin = User.query.filter_by(username=username).first()
    if not superadmin:
        print(f"Creating superadmin user '{username}'...")
        superadmin = User(
            username=username,
            email=f'{username}@tourneypro.com',
            role='superadmin'
        )
        superadmin.set_password(password)
        db.session.add(superadmin)
        db.session.commit()
        print("Superadmin created successfully!")
    else:
        print("Superadmin already exists.")
