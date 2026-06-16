# Format definitions for Lawn Tennis
TOURNAMENT_FORMATS = {
    'single_elimination': {
        'name': 'Single Elimination (Knockout)',
        'description': 'Standard knockout format where a player is eliminated after a single match loss.',
        'icon': '🏆',
        'min_participants': 2
    },
    'double_elimination': {
        'name': 'Double Elimination (Knockout)',
        'description': 'Knockout format where players must lose twice to be eliminated from the tournament.',
        'icon': '🥇',
        'min_participants': 3
    },
    'group_stage': {
        'name': 'Group Stage + Knockout',
        'description': 'Round-robin group matches followed by a single elimination knockout bracket for top qualifiers.',
        'icon': '🎪',
        'min_participants': 4
    }
}

