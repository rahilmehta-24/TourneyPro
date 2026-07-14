from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # clear users for testing
    User.query.filter_by(username='testuser').delete()
    db.session.commit()
    
    # register
    u = User(username='testuser', email='test@example.com', role='user')
    u.set_password('password123')
    db.session.add(u)
    db.session.commit()
    
    # login
    u_login = User.query.filter_by(username='testuser').first()
    print("User found:", u_login is not None)
    if u_login:
        print("Password check:", u_login.check_password('password123'))
