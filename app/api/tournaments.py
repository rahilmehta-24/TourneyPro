from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from . import api_bp
from app.domain.models import (
    db, Tournament, Category, Participant, Group,
    Registration, TournamentStaff, User, InAppNotification
)
from app.domain.schemas import tournament_schema, category_schema
from app.services.utils.scheduler import get_order_of_play
from app.services.leaderboard import recalculate_all_group_stats


@api_bp.route('/tournaments', methods=['GET'])
def get_tournaments():
    """List tournaments with optional filtering for mobile discovery & events landing."""
    status = request.args.get('status')
    query = Tournament.query.order_by(Tournament.created_at.desc())
    if status:
        query = query.filter_by(status=status)
    tournaments = query.all()

    data = []
    for t in tournaments:
        dates_disp = ""
        if t.start_date and t.end_date:
            dates_disp = f"{t.start_date.strftime('%b %d')} - {t.end_date.strftime('%b %d, %Y')}"
        elif t.start_date:
            dates_disp = t.start_date.strftime('%b %d, %Y')

        entry_fee_disp = f"₹{int(t.entry_fee):,}" if getattr(t, 'entry_fee', None) else "Free"
        reg_count = Registration.query.filter_by(tournament_id=t.id).count()

        venue_disp = getattr(t, 'venue_name', None) or getattr(t, 'court_names', None) or (t.academy.name if getattr(t, 'academy', None) else None) or "Baseline Tennis Center"
        city_disp = getattr(t, 'city', None) or "Mumbai"

        data.append({
            "id": t.id,
            "name": t.name,
            "slug": t.url_slug,
            "surface": getattr(t, 'surface', None) or "Hard",
            "venue": venue_disp,
            "city": city_disp,
            "status": t.status,
            "is_live": t.status in ("in_progress", "live"),
            "dates": dates_disp,
            "entryFee": entry_fee_disp,
            "categoriesCount": len(t.categories) if t.categories else 0,
            "registeredCount": reg_count,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })

    return jsonify({
        "success": True,
        "count": len(data),
        "tournaments": data
    }), 200


@api_bp.route('/tournaments', methods=['POST'])
@jwt_required()
def create_tournament_api():
    """
    Mobile tournament creation endpoint for organizers.
    Enforces RBAC: allows admin, superadmin, or automatically activates
    regular player into organizer upon hosting their first event.
    """
    from flask_jwt_extended import get_jwt_identity
    from app.services.utils.validation import validate_name
    from slugify import slugify

    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id)) if current_user_id and str(current_user_id).isdigit() else None
    if not user:
        return jsonify({"success": False, "message": "User not authenticated"}), 401

    # If regular player is hosting, promote to admin role
    if user.role not in ('admin', 'superadmin'):
        user.role = 'admin'
        db.session.add(user)

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name or len(name) < 3:
        return jsonify({"success": False, "message": "Tournament name must be at least 3 characters"}), 400

    ok, clean_name = validate_name(name, min_len=3, max_len=100, field_name="Tournament Name")
    if not ok:
        return jsonify({"success": False, "message": clean_name}), 400

    venue = (data.get('venue') or data.get('venue_name') or 'Baseline Tennis Center').strip()
    city = (data.get('city') or 'Mumbai').strip()
    surface = data.get('surface') or 'Hard'
    description = (data.get('description') or '').strip()
    num_courts = int(data.get('num_courts') or 2)

    start_date = None
    end_date = None
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if not start_date:
        start_date = datetime.utcnow().date()
    if not end_date or end_date < start_date:
        end_date = start_date + timedelta(days=2)

    url_slug = slugify(clean_name)
    existing = Tournament.query.filter_by(url_slug=url_slug).first()
    if existing:
        url_slug = f"{url_slug}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    tournament = Tournament(
        user_id=user.id,
        creator_name=user.username or user.email,
        name=clean_name,
        url_slug=url_slug,
        description=description,
        court_names=venue,
        has_categories=True,
        start_date=start_date,
        end_date=end_date,
        num_courts=num_courts,
        court_operating_start="09:00",
        court_operating_end="19:00",
        status="upcoming",
    )
    db.session.add(tournament)
    db.session.flush()

    # Automatically add a default Category so registrations & schedule work out of the box
    default_cat = Category(
        tournament_id=tournament.id,
        name="Men's Singles Open",
        format="single_elimination",
        entry_fee=500.0,
        max_participants=32,
        status="registration_open"
    )
    db.session.add(default_cat)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Tournament created successfully!",
        "tournament": {
            "id": tournament.id,
            "name": tournament.name,
            "slug": tournament.url_slug,
            "venue": venue,
            "city": city,
            "surface": surface,
            "status": tournament.status,
            "dates": f"{start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}",
            "categoriesCount": 1,
            "registeredCount": 0
        }
    }), 201


@api_bp.route('/tournaments/<slug>', methods=['GET'])
def get_tournament_by_slug(slug):
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    return jsonify({
        "success": True,
        "tournament": tournament_schema.dump(tournament)
    }), 200


@api_bp.route('/tournaments/<slug>/categories/<int:category_id>', methods=['GET'])
def get_category_details(slug, category_id):
    category = Category.query.get_or_404(category_id)
    return jsonify({
        "success": True,
        "category": category_schema.dump(category)
    }), 200


@api_bp.route('/tournaments/<slug>/order-of-play', methods=['GET'])
def get_order_of_play_api(slug):
    """
    Mobile Order of Play endpoint — structured court schedules,
    real-time match states, Not Before flags, and lock versions.
    """
    date_param = request.args.get('date')
    filter_date = None
    if date_param:
        try:
            filter_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            pass

    oop_data = get_order_of_play(slug, filter_date=filter_date)
    tournament = oop_data.get("tournament")
    courts_dict = oop_data.get("courts", {})

    court_filter = request.args.get('court')
    if court_filter and court_filter in courts_dict:
        courts_dict = {court_filter: courts_dict[court_filter]}

    serialized_courts = []
    for court_name, matches_list in courts_dict.items():
        court_matches = []
        for item in matches_list:
            m = item.get("match")
            court_matches.append({
                "id": m.id,
                "round": m.round,
                "round_name": item.get("round_name", f"Round {m.round}"),
                "match_number": m.match_number,
                "category_id": item.get("category_id"),
                "category_name": item.get("category_name"),
                "time": item.get("time"),
                "time_display": item.get("time_display"),
                "is_not_before": item.get("is_not_before", False),
                "is_locked": item.get("is_locked", False),
                "session": item.get("session", "day"),
                "status": m.status,
                "score1": m.score1,
                "score2": m.score2,
                "lock_version": m.lock_version or 1,
                "participant1": {
                    "id": m.participant1_id,
                    "name": item.get("p1", "TBD"),
                    "player_id": item.get("p1_player_id")
                } if m.participant1_id else None,
                "participant2": {
                    "id": m.participant2_id,
                    "name": item.get("p2", "TBD"),
                    "player_id": item.get("p2_player_id")
                } if m.participant2_id else None,
                "winner_id": m.winner_id
            })

        serialized_courts.append({
            "court_name": court_name,
            "match_count": len(court_matches),
            "matches": court_matches
        })

    return jsonify({
        "success": True,
        "tournament": {
            "id": tournament.id,
            "name": tournament.name,
            "slug": tournament.url_slug,
            "start_date": tournament.start_date.isoformat() if tournament.start_date else None,
            "end_date": tournament.end_date.isoformat() if tournament.end_date else None,
        },
        "active_date": oop_data.get("active_date").isoformat() if oop_data.get("active_date") else None,
        "all_courts": oop_data.get("all_courts", list(courts_dict.keys())),
        "schedule": serialized_courts,
        "courts": serialized_courts
    }), 200


@api_bp.route('/categories/<int:category_id>/standings', methods=['GET'])
def get_category_standings(category_id):
    """
    Mobile Standings & Rankings endpoint — group stage points tables
    and category participant rankings.
    """
    category = Category.query.get_or_404(category_id)

    # Recalculate group stats if category is group stage or round robin
    if category.has_group_stage or category.format in ['group_stage', 'round_robin']:
        try:
            recalculate_all_group_stats(category.id)
        except Exception:
            pass

    groups_data = []
    groups = Group.query.filter_by(category_id=category.id).order_by(Group.name).all()

    for grp in groups:
        participants = Participant.query.filter_by(
            category_id=category.id,
            group_id=grp.id
        ).order_by(
            Participant.group_points.desc(),
            Participant.group_wins.desc()
        ).all()

        grp_standings = []
        for rank, p in enumerate(participants, start=1):
            grp_standings.append({
                "rank": rank,
                "participant_id": p.id,
                "name": p.name,
                "seed": p.manual_seed,
                "played": (p.group_wins or 0) + (p.group_losses or 0),
                "won": p.group_wins or 0,
                "lost": p.group_losses or 0,
                "points": p.group_points or 0,
                "final_rank": p.final_rank
            })

        groups_data.append({
            "group_id": grp.id,
            "name": grp.name,
            "standings": grp_standings
        })

    # Overall category participants / seeds
    all_participants = Participant.query.filter_by(category_id=category.id).order_by(
        Participant.final_rank.asc().nullslast(),
        Participant.manual_seed.asc().nullslast()
    ).all()

    overall_standings = []
    for p in all_participants:
        overall_standings.append({
            "id": p.id,
            "name": p.name,
            "seed": p.manual_seed,
            "final_rank": p.final_rank,
            "wins": p.group_wins or 0,
            "losses": p.group_losses or 0,
            "points": p.group_points or 0
        })

    return jsonify({
        "success": True,
        "category": {
            "id": category.id,
            "name": category.name,
            "format": category.format,
            "has_group_stage": category.has_group_stage,
            "draw_published": category.draw_published
        },
        "groups": groups_data,
        "participants": overall_standings
    }), 200


@api_bp.route('/categories/<int:category_id>/toggle-publish', methods=['POST'])
@jwt_required()
def toggle_category_publish(category_id):
    """Publish or unpublish draws for a category, triggering in-app alerts to participants."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    category = Category.query.get_or_404(category_id)
    tournament = category.tournament

    # Check permission
    is_staff = False
    staff = TournamentStaff.query.filter_by(tournament_id=tournament.id, user_id=user.id).first()
    if staff and staff.role in ('manager', 'official', 'tournament_admin'):
        is_staff = True

    if user.role != 'superadmin' and tournament.user_id != user.id and not is_staff:
        return jsonify({"success": False, "message": "Forbidden: You cannot publish this draw"}), 403

    category.draw_published = not category.draw_published

    # If published, push in-app alerts to all approved registrants
    if category.draw_published:
        registrations = Registration.query.filter_by(
            category_id=category.id,
            status='approved'
        ).all()
        for reg in registrations:
            notif = InAppNotification(
                user_id=reg.user_id,
                title="Draws Published! 🏆",
                body=f"Draws for {category.name} in {tournament.name} are now live. View your schedule on Baseline.",
                notification_type="draw_published",
                reference_type="category",
                reference_id=category.id
            )
            db.session.add(notif)

    db.session.commit()

    return jsonify({
        "success": True,
        "category_id": category.id,
        "draw_published": category.draw_published,
        "message": f"Draw {'published' if category.draw_published else 'unpublished'} successfully"
    }), 200


@api_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """List genuine ranked players from the registry for mobile leaderboard."""
    from app.domain.models import Player
    from sqlalchemy import desc

    category = request.args.get('category')
    gender = request.args.get('gender')
    limit = min(int(request.args.get('limit', 50)), 100)

    # Leaderboard Qualification Filter:
    # A player must have earned ranking points (> 0) OR have registered in a tournament/match.
    from app.domain.models import Participant
    registered_p1 = db.session.query(Participant.player_id).filter(Participant.player_id.isnot(None))
    registered_p2 = db.session.query(Participant.player2_id).filter(Participant.player2_id.isnot(None))

    qualification_filter = db.or_(
        Player.total_points > 0,
        Player.matches_played > 0,
        Player.id.in_(registered_p1),
        Player.id.in_(registered_p2)
    )

    query = Player.query.filter(
        qualification_filter,
        ~Player.name.ilike('Player %'),
        ~Player.name.ilike('Player_%'),
        ~Player.name.ilike('Dummy%'),
        ~Player.name.ilike('Test%'),
        ~Player.name.ilike('Sample%'),
        ~Player.name.ilike('TBD%')
    )
    if category and category != 'All':
        query = query.filter_by(age_category=category)
    if gender and gender != 'All':
        query = query.filter_by(gender=gender)

    players = query.order_by(desc(Player.total_points)).limit(limit).all()

    rankings = []
    for idx, p in enumerate(players, start=1):
        total_m = p.matches_played or 0
        won_m = p.matches_won or 0
        win_rate = round((won_m / total_m * 100), 1) if total_m > 0 else 0.0
        rankings.append({
            "rank": idx,
            "id": p.id,
            "name": p.name,
            "points": int(p.total_points or 0),
            "age_category": p.age_category,
            "gender": p.gender,
            "academy": p.academy or "Independent",
            "matches_played": total_m,
            "matches_won": won_m,
            "win_rate": win_rate
        })

    return jsonify({
        "success": True,
        "count": len(rankings),
        "rankings": rankings
    }), 200


@api_bp.route('/announcements', methods=['GET'])
def get_announcements():
    """List genuine announcements from registered academies & platform notices."""
    from app.domain.models import AcademyAnnouncement
    announcements = AcademyAnnouncement.query.order_by(
        AcademyAnnouncement.created_at.desc()
    ).limit(20).all()

    data = []
    for a in announcements:
        data.append({
            "id": a.id,
            "title": a.title,
            "desc": a.content,
            "date": a.created_at.strftime("%d %b %Y") if a.created_at else "",
            "academy_id": a.academy_id,
            "academy_name": a.academy.name if a.academy else "Baseline Society"
        })

    return jsonify({
        "success": True,
        "count": len(data),
        "announcements": data
    }), 200

