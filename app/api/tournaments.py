from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from . import api_bp
from app.domain.models import (
    db, Tournament, Category, Participant, Group,
    Registration, TournamentStaff, User
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

    format_status = (data.get('format_status') or 'NOT_DECIDED').strip().upper()
    if format_status not in ['NOT_DECIDED', 'FINALIZED']:
        format_status = 'NOT_DECIDED'

    registration_status = (data.get('registration_status') or 'DRAFT').strip().upper()
    if registration_status not in ['DRAFT', 'UPCOMING', 'OPEN', 'CLOSED']:
        registration_status = 'DRAFT'

    registration_opens_at = None
    if data.get('registration_opens_at'):
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                registration_opens_at = datetime.strptime(data.get('registration_opens_at'), fmt)
                break
            except ValueError:
                pass

    registration_closes_at = None
    if data.get('registration_closes_at'):
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                registration_closes_at = datetime.strptime(data.get('registration_closes_at'), fmt)
                break
            except ValueError:
                pass

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
        format_status=format_status,
        registration_status=registration_status,
        registration_opens_at=registration_opens_at,
        registration_closes_at=registration_closes_at,
        is_published=data.get('is_published', True),
    )
    db.session.add(tournament)
    db.session.flush()

    # Automatically add a default Category if requested or default
    cat_format = data.get('format')
    if not cat_format or format_status == 'NOT_DECIDED':
        cat_format = None

    default_cat = Category(
        tournament_id=tournament.id,
        name=data.get('category_name') or "Men's Singles Open",
        format=cat_format,
        format_status=format_status,
        entry_fee=float(data.get('entry_fee') or 500.0),
        max_participants=int(data.get('max_participants') or 32),
        registration_status="OPEN",
        is_registration_open=True,
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
        try:
            from app.services.notification_service import notify_draw_published
            notify_draw_published(category)
        except Exception:
            pass

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

    category = request.args.get('category')
    gender = request.args.get('gender')
    limit = min(int(request.args.get('limit', 50)), 100)

    from app.services.leaderboard import get_qualified_leaderboard_query

    players = get_qualified_leaderboard_query(
        category_filter=category,
        gender_filter=gender
    ).limit(limit).all()

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


# ---------------------------------------------------------------------------
# Format Finalization & Category Registration APIs
# ---------------------------------------------------------------------------

@api_bp.route('/tournaments/<slug>/categories/<int:category_id>/format', methods=['POST'])
@jwt_required()
def finalize_category_format_api(slug, category_id):
    """Finalize or modify category format without deleting existing participants."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    if user.role != 'superadmin' and tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden: Only organizers can finalize format"}), 403

    category = Category.query.filter_by(id=category_id, tournament_id=tournament.id).first_or_404()
    data = request.get_json() or {}
    new_format = data.get('format')
    if not new_format:
        return jsonify({"success": False, "message": "Format is required"}), 400

    old_format = category.format
    category.format = new_format
    category.format_status = "FINALIZED"
    if 'scoring_format' in data:
        category.scoring_format = data['scoring_format']
    if 'num_sets' in data:
        category.num_sets = int(data['num_sets'])
    if 'games_per_set' in data:
        category.games_per_set = int(data['games_per_set'])

    db.session.commit()

    from app.services.utils.audit import log_audit
    log_audit(
        action_type="FINALIZE_FORMAT",
        target_id=category.id,
        target_name=f"{tournament.name} - {category.name}",
        reason="Format finalized via API",
        details={"old_format": old_format, "new_format": new_format, "participants_count": len(category.participants)},
        user_id=user.id
    )

    return jsonify({
        "success": True,
        "message": f"Format finalized as {new_format}",
        "category": {
            "id": category.id,
            "format": category.format,
            "format_status": category.format_status,
            "participants_count": len(category.participants)
        }
    }), 200


@api_bp.route('/tournaments/<slug>/categories/<int:category_id>/registration-status', methods=['PATCH'])
@jwt_required()
def toggle_category_registration_api(slug, category_id):
    """Close or open an individual category registration."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    if user.role != 'superadmin' and tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    category = Category.query.filter_by(id=category_id, tournament_id=tournament.id).first_or_404()
    data = request.get_json() or {}
    status = (data.get('status') or '').strip().upper()
    if status not in ['OPEN', 'CLOSED']:
        category.is_registration_open = not category.is_registration_open
        category.registration_status = "OPEN" if category.is_registration_open else "CLOSED"
    else:
        category.registration_status = status
        category.is_registration_open = (status == "OPEN")

    db.session.commit()
    return jsonify({
        "success": True,
        "category_id": category.id,
        "registration_status": category.registration_status,
        "is_registration_open": category.is_registration_open
    }), 200


# ---------------------------------------------------------------------------
# Bulk Import APIs
# ---------------------------------------------------------------------------

@api_bp.route('/tournaments/<slug>/import/template', methods=['GET'])
@jwt_required()
def download_api_csv_template(slug):
    """Download CSV template via API."""
    from app.services.bulk_import_service import generate_csv_template
    from flask import Response
    return Response(
        generate_csv_template(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Template_{slug}.csv"}
    )


@api_bp.route('/tournaments/<slug>/import/upload', methods=['POST'])
@jwt_required()
def api_bulk_import_upload(slug):
    """Upload CSV for validation and preview."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if user.role != 'superadmin' and tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden: Only tournament organizers can import participants"}), 403

    if 'file' not in request.files and 'csv_file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files.get('file') or request.files.get('csv_file')
    if not file or not file.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400

    file_bytes = file.read()
    from app.services.bulk_import_service import validate_and_parse_csv
    try:
        results = validate_and_parse_csv(
            tournament=tournament,
            file_bytes=file_bytes,
            original_filename=file.filename,
            organizer_id=user.id
        )
        return jsonify({
            "success": True,
            "batch_id": results["batch_id"],
            "total_rows": results["total_rows"],
            "valid_count": results["valid_count"],
            "invalid_count": results["invalid_count"],
            "duplicate_count": results["duplicate_count"],
            "preview_valid": results["preview_valid"],
            "preview_errors": results["preview_errors"],
            "valid_rows": results["valid_rows"]
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 400


@api_bp.route('/tournaments/<slug>/import/confirm', methods=['POST'])
@jwt_required()
def api_bulk_import_confirm(slug):
    """Confirm and execute import batch."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if user.role != 'superadmin' and tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    data = request.get_json() or {}
    batch_id = data.get('batch_id')
    if not batch_id:
        return jsonify({"success": False, "message": "batch_id is required"}), 400

    from app.domain.models import ParticipantImportBatch
    from app.services.bulk_import_service import execute_import_batch

    batch = ParticipantImportBatch.query.get_or_404(batch_id)
    if batch.tournament_id != tournament.id:
        return jsonify({"success": False, "message": "Unauthorized cross-tournament batch"}), 403

    ok, message, imported_count = execute_import_batch(batch.id, user.id, valid_rows=data.get('valid_rows'))
    return jsonify({
        "success": ok,
        "message": message,
        "imported_count": imported_count,
        "batch_id": batch.id
    }), (200 if ok else 400)


@api_bp.route('/tournaments/<slug>/import/<int:batch_id>/errors', methods=['GET'])
@jwt_required()
def api_bulk_import_errors(slug, batch_id):
    """Download error CSV report for a batch."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if user.role != 'superadmin' and tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    from app.domain.models import ParticipantImportBatch
    from app.services.bulk_import_service import generate_error_csv_report
    from flask import Response

    batch = ParticipantImportBatch.query.get_or_404(batch_id)
    if batch.tournament_id != tournament.id:
        return jsonify({"success": False, "message": "Cross-tournament error access forbidden"}), 403

    return Response(
        generate_error_csv_report(batch),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Errors_Batch_{batch.id}.csv"}
    )


@api_bp.route('/tournaments/<slug>/import/history', methods=['GET'])
@jwt_required()
def api_bulk_import_history(slug):
    """List previous import batches for tournament."""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()

    if user.role != 'superadmin' and tournament.user_id != user.id:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    from app.domain.models import ParticipantImportBatch
    batches = ParticipantImportBatch.query.filter_by(tournament_id=tournament.id).order_by(
        ParticipantImportBatch.created_at.desc()
    ).all()

    return jsonify({
        "success": True,
        "history": [
            {
                "id": b.id,
                "filename": b.filename,
                "total_rows": b.total_rows,
                "valid_rows": b.valid_rows,
                "invalid_rows": b.invalid_rows,
                "duplicate_rows": b.duplicate_rows,
                "imported_rows": b.imported_rows,
                "status": b.status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "completed_at": b.completed_at.isoformat() if b.completed_at else None,
            }
            for b in batches
        ]
    }), 200


