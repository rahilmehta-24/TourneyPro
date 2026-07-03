with open('config.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if "SQLALCHEMY_ENGINE_OPTIONS =" in line:
        skip = True
    if skip and "}" in line and not line.startswith("    }"):
        pass
    if skip and line.startswith("    }"):
        skip = False
        continue
    
    if not skip:
        new_lines.append(line)
        if "SQLALCHEMY_TRACK_MODIFICATIONS = False" in line:
            new_lines.append("    if db_url and db_url.startswith('postgresql'):\n")
            new_lines.append("        SQLALCHEMY_ENGINE_OPTIONS = {\n")
            new_lines.append("            'pool_pre_ping': True,\n")
            new_lines.append("            'connect_args': {\n")
            new_lines.append("                'prepare_threshold': None\n")
            new_lines.append("            }\n")
            new_lines.append("        }\n")

with open('config.py', 'w') as f:
    f.writelines(new_lines)
