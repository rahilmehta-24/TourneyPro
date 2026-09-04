from app.formats.round_robin.logic import RoundRobinFormat

class DoublesRoundRobinFormat(RoundRobinFormat):
    name = "Doubles Round Robin"
    description = "Team-based round-robin format where pairs compete against every other pair."
    icon = "🔄"
    min_participants = 2
