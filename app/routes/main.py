from flask import Blueprint, render_template
from app.models import Tournament
from app.constants import TOURNAMENT_FORMATS

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Homepage with tournament list"""
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).limit(10).all()
    return render_template('index.html', tournaments=tournaments, formats=TOURNAMENT_FORMATS)

@main_bp.route('/tournaments')
def tournament_list():
    """List all tournaments"""
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return render_template('tournament/list.html', tournaments=tournaments, formats=TOURNAMENT_FORMATS)
