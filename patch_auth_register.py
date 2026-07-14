with open('app/routes/auth.py', 'r') as f:
    content = f.read()

target = """        from dateutil.relativedelta import relativedelta
        import random
        
        current_date = date.today()
        # Generate Registration No: TP-YYYY-HEX
        reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"
        registration_date = current_date
        registration_validity = current_date + relativedelta(years=1)"""

replace = """        from datetime import timedelta
        import random
        
        current_date = date.today()
        # Generate Registration No: TP-YYYY-HEX
        reg_no = f"TP-{current_date.year}-{random.randint(0x1000, 0xFFFF):X}"
        registration_date = current_date
        registration_validity = current_date + timedelta(days=365)"""

if target in content:
    content = content.replace(target, replace)
    with open('app/routes/auth.py', 'w') as f:
        f.write(content)
    print("Auth register route patched to remove relativedelta.")
else:
    print("Target not found in auth.py")
