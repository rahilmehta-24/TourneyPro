
with open('app/models.py', 'r') as f:
    content = f.read()

target = """    partner_mobile = db.Column(db.String(20)) # Mobile of partner for Doubles (Self Registration)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))"""

replace = """    partner_mobile = db.Column(db.String(20)) # Mobile of partner for Doubles (Self Registration)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    mobile = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    dob = db.Column(db.Date)"""

if target in content:
    content = content.replace(target, replace)
    with open('app/models.py', 'w') as f:
        f.write(content)
    print("models.py updated.")
else:
    print("Target not found.")
