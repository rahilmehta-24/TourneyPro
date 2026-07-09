from flask import jsonify
from . import api_bp
from app.models import Tournament, Category
from app.schemas import tournaments_schema, tournament_schema, category_schema

@api_bp.route('/tournaments', methods=['GET'])
def get_tournaments():
    tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    return jsonify({
        "success": True,
        "tournaments": tournaments_schema.dump(tournaments)
    }), 200

@api_bp.route('/tournaments/<slug>', methods=['GET'])
def get_tournament_by_slug(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    return jsonify({
        "success": True,
        "tournament": tournament_schema.dump(tournament)
    }), 200

@api_bp.route('/tournaments/<slug बॉर्डर>/categories/<int:category_id>', methods=['GET'])
def get_category_details(slug, category_id):
    category = Category.query.get_or_404(category_id)
    return jsonify({
        "success": True,
        "category": category_schema.dump(category)
    }), 200
