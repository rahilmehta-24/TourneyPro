with open('app/routes/category.py', 'r') as f:
    content = f.read()

content = content.replace('''        if not dummy_data and category.format == 'double_elimination':
            from app.algorithms.double_elimination import generate_double_elimination
            dummy_data = generate_double_elimination(participants, use_manual_seeding=False)
            
        if not dummy_data and category.format == 'double_elimination':
            from app.algorithms.double_elimination import generate_double_elimination
            dummy_data = generate_double_elimination(participants)''', '')

with open('app/routes/category.py', 'w') as f:
    f.write(content)
