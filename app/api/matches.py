from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import api_bp
from app.models import Match, User, db
from app.schemas import matches_schema
from app.formats import get_format
from app.leaderboard_logic import update_live_player_stats, recalculate_all_group_stats
from datetime import datetime

@api_bp.route('/matches/category/<int:category_id>', methods=['GET'])
def get_matches(category_id):
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.round, Match.match_number).all()
    return jsonify({
        "success": True,
        "matches": matches_schema.dump(matches)
    }), 200

@api_bp.route('/matches/<int:match_id>/report', methods=['POST'])
@jwt_required()
def report_match(match_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or user.role not in ['admin', 'superadmin']:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    match = Match.query.get_or_404(match_id)
    data = request.get_json()

    # Determine action type (pending, live_score, complete_match)
    action_type = data.get('action_type', 'complete_match')
    
    scheduled_time_str = data.get('scheduled_time')
    if scheduled_time_str:
        try:
            match.scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        except ValueError:
            pass
            
    if action_type == 'pending':
        match.status = 'pending'
        match.winner_id = None
        match.score1 = None
        match.score2 = None
        match.completed_at = None
        db.session.commit()
        return jsonify({"success": True, "message": "Match set to pending"}), 200

    # Parse scores
    try:
        p1_sets = []
        p2_sets = []
        # In this simplified API version, we expect the frontend to send parsed scores.
        # e.g., "6(7)", "4"
        score1 = data.get('score1', '')
        score2 = data.get('score2', '')
        
        match.score1 = score1
        match.score2 = score2
        
        if action_type == 'live_score':
            match.status = 'in_progress'
            match.winner_id = None
            db.session.commit()
            return jsonify({"success": True, "message": "Live score updated"}), 200
            
        elif action_type == 'complete_match':
            winner_id = data.get('winner_id')
            if not winner_id:
                return jsonify({"success": False, "message": "Winner ID required"}), 400
                
            match.winner_id = winner_id
            match.status = 'completed'
            match.completed_at = datetime.utcnow()
            db.session.commit()
            
            update_live_player_stats(match)

            fmt = get_format(match.category.format)
            if fmt:
                fmt.advance_match(match, match.category, winner_id)
            
            db.session.commit()

            if match.category.format in ['group_stage', 'round_robin']:
                recalculate_all_group_stats(match.category_id)
                
            return jsonify({"success": True, "message": "Match completed"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
