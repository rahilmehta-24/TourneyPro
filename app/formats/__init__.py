from app.formats.single_elimination.logic import SingleEliminationFormat
from app.formats.double_elimination.logic import DoubleEliminationFormat
from app.formats.round_robin.logic import RoundRobinFormat
from app.formats.group_stage.logic import GroupStageFormat

FormatRegistry = {
    'single_elimination': SingleEliminationFormat,
    'double_elimination': DoubleEliminationFormat,
    'round_robin': RoundRobinFormat,
    'group_stage': GroupStageFormat
}

def get_format(format_key):
    return FormatRegistry.get(format_key)

def get_all_formats():
    return {
        key: {
            'name': cls.name,
            'description': cls.description,
            'icon': cls.icon,
            'min_participants': cls.min_participants
        } for key, cls in FormatRegistry.items()
    }
