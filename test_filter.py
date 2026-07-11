import re

def format_tennis_score(score_str):
    if not score_str:
        return ""
    # Find something like (4) and replace with <sup>4</sup>
    return re.sub(r'\((\d+)\)', r'<sup>\1</sup>', score_str)

print(format_tennis_score("7-6(4), 6-4"))
