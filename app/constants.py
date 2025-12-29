# Format definitions
TOURNAMENT_FORMATS = {
    'single_elimination': {
        'name': 'Single Elimination',
        'description': 'Participants are eliminated after one loss',
        'icon': '🏆',
        'min_participants': 2
    },
    'double_elimination': {
        'name': 'Double Elimination',
        'description': 'Participants must lose twice to be eliminated',
        'icon': '🥇',
        'min_participants': 3
    },
    'round_robin': {
        'name': 'Round Robin',
        'description': 'Every participant plays every other participant',
        'icon': '🔄',
        'min_participants': 3
    },
    'swiss': {
        'name': 'Swiss System',
        'description': 'Participants play opponents with similar records',
        'icon': '🎯',
        'min_participants': 4
    },
    'free_for_all': {
        'name': 'Free For All',
        'description': 'All participants compete simultaneously',
        'icon': '⚔️',
        'min_participants': 3
    },
    'leaderboard': {
        'name': 'Leaderboard',
        'description': 'Ranking-based competition',
        'icon': '📊',
        'min_participants': 2
    },
    'time_trial': {
        'name': 'Time Trial',
        'description': 'Individual time-based competition',
        'icon': '⏱️',
        'min_participants': 1
    },
    'single_race': {
        'name': 'Single Race',
        'description': 'One-off race with placement ranking',
        'icon': '🏁',
        'min_participants': 2
    },
    'grand_prix': {
        'name': 'Grand Prix',
        'description': 'Series of races with points system',
        'icon': '🏎️',
        'min_participants': 2
    },
    'group_stage': {
        'name': 'Group Stage + Knockout',
        'description': 'Group round-robin followed by knockout bracket',
        'icon': '🎪',
        'min_participants': 4
    }
}
