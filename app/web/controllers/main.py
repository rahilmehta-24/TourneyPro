from flask import Blueprint, render_template
from app.domain.models import Tournament
from app.core.constants import TOURNAMENT_FORMATS
from app.web.controllers.auth import get_current_user

main_bp = Blueprint('main', __name__)

def get_visible_tournaments(limit=None):
    current_user = get_current_user()
    query = Tournament.query
    
    if current_user:
        user_academy_ids = [m.academy_id for m in current_user.academy_memberships]
        if user_academy_ids:
            query = query.filter((Tournament.is_internal == False) | (Tournament.is_internal == None) | (Tournament.academy_id.in_(user_academy_ids)))
        else:
            query = query.filter((Tournament.is_internal == False) | (Tournament.is_internal == None))
    else:
        query = query.filter((Tournament.is_internal == False) | (Tournament.is_internal == None))
        
    query = query.order_by(Tournament.created_at.desc())
    if limit:
        return query.limit(limit).all()
    return query.all()

@main_bp.route('/')
def index():
    """Homepage with tournament list"""
    tournaments = get_visible_tournaments(limit=10)
    return render_template('index.html', tournaments=tournaments, formats=TOURNAMENT_FORMATS)

@main_bp.route('/tournaments')
def tournament_list():
    """List all tournaments"""
    tournaments = get_visible_tournaments()
    return render_template('tournament/list.html', tournaments=tournaments, formats=TOURNAMENT_FORMATS)
