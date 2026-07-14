with open('app/models.py', 'r') as f:
    content = f.read()

target = """class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False) # e.g. Boys, Girls, Mens, Womens
    age_category = db.Column(db.String(20), nullable=False) # e.g. U8, U10, U12, U14, U18, Open
    total_points = db.Column(db.Float, default=0.0)"""

replacement = """class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False) # e.g. Boys, Girls, Mens, Womens
    age_category = db.Column(db.String(20), nullable=False) # e.g. U8, U10, U12, U14, U18, Open
    avatar_url = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    total_points = db.Column(db.Float, default=0.0)"""

if target in content:
    content = content.replace(target, replacement)
    with open('app/models.py', 'w') as f:
        f.write(content)
    print("models.py patched successfully.")
else:
    print("target not found in models.py")
