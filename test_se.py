from app import create_app
from app.models import Category, Participant, Match

app = create_app()
with app.app_context():
    # Find a tournament and single elimination category
    cat = Category.query.filter_by(format='single_elimination').first()
    if cat:
        print(f"Found Category: {cat.id}")
        matches = Match.query.filter_by(category_id=cat.id).all()
        print(f"Matches count: {len(matches)}")
        
        # Test generation
        from app.formats import get_format
        fmt = get_format(cat.format)
        participants = Participant.query.filter_by(category_id=cat.id).all()
        try:
            dummy = fmt.generate(cat, participants)
            print("Generate successful! Match count: ", len(dummy))
        except Exception as e:
            print("Generate Failed:", e)
            import traceback
            traceback.print_exc()

