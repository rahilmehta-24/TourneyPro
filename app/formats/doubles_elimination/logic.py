from app.formats.single_elimination.logic import SingleEliminationFormat

class DoublesEliminationFormat(SingleEliminationFormat):
    name = "Doubles Elimination"
    description = "Team-based knockout tournament where pairs compete and advance together."
    icon = "🤝"
    min_participants = 2
