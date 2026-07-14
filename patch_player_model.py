
with open('app/models.py', 'r') as f:
    content = f.read()

target = """    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(20), nullable=False) # e.g. Boys, Girls, Mens, Womens
    age_category = db.Column(db.String(20), nullable=False) # e.g. U8, U10, U12, U14, U18, Open
    avatar_url = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.Text, nullable=True)"""

replacement = """    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    registration_no = db.Column(db.String(100), nullable=True)
    dob = db.Column(db.Date, nullable=True)
    email = db.Column(db.String(120), nullable=True)
    contact_number = db.Column(db.String(50), nullable=True)
    height = db.Column(db.String(50), nullable=True)
    weight = db.Column(db.String(50), nullable=True)
    gender = db.Column(db.String(20), nullable=False) # e.g. Boys, Girls, Mens, Womens
    blood_group = db.Column(db.String(10), nullable=True)
    nationality = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    coach = db.Column(db.String(100), nullable=True)
    academy = db.Column(db.String(100), nullable=True)
    registration_details = db.Column(db.Text, nullable=True)
    registration_date = db.Column(db.Date, nullable=True)
    registration_validity = db.Column(db.Date, nullable=True)
    current_status = db.Column(db.String(50), default='Active')
    age_category = db.Column(db.String(20), nullable=False) # e.g. U8, U10, U12, U14, U18, Open
    avatar_url = db.Column(db.String(500), nullable=True)
    bio = db.Column(db.Text, nullable=True)"""

if target in content:
    content = content.replace(target, replacement)
    with open('app/models.py', 'w') as f:
        f.write(content)
    print("models.py successfully patched.")
else:
    print("Target not found in models.py!")
