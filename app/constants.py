# Format definitions for Lawn Tennis
TOURNAMENT_FORMATS = {
    'single_elimination': {
        'name': 'Single Elimination (Knockout)',
        'description': 'Standard knockout format where a player is eliminated after a single match loss.',
        'icon': '🏆',
        'min_participants': 2
    },
    'round_robin': {
        'name': 'Round Robin (League)',
        'description': 'Everyone plays everyone. Rankings are determined by total points/wins.',
        'icon': '🔄',
        'min_participants': 3
    },
    'group_stage': {
        'name': 'Group Stage + Knockout',
        'description': 'Round-robin group matches followed by a single elimination knockout bracket for top qualifiers.',
        'icon': '🎪',
        'min_participants': 4
    },
    'category': {
        'name': 'Multiple Categories/Events',
        'description': 'Tournament separated by age groups, genders, or skill levels.',
        'icon': '🗂️',
        'min_participants': 2
    }
}

