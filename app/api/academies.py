"""
REST API Endpoints for Academies and Platform Verification
The Baseline Society
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.api import api_bp
from app.domain.models import Academy, AcademyApplication, User
from app.services.academy_service import (
    submit_academy_application,
    review_academy_application,
    add_academy_member,
    transfer_user_academy_membership,
    leave_academy_membership,
)
from app.services.rbac_service import has_permission
from app.domain.constants import PERM_PLATFORM_ACADEMIES_VERIFY, PERM_PLATFORM_ACADEMIES_VIEW


def _serialize_academy(academy: Academy) -> dict:
    return {
        "id": academy.id,
        "name": academy.name,
        "url_slug": academy.url_slug,
        "description": academy.description,
        "status": academy.status,
        "city": academy.city,
        "state": academy.state,
        "country": academy.country,
        "sports_offered": academy.sports_offered,
        "website_url": academy.website_url,
        "owner_id": academy.owner_id,
        "created_at": academy.created_at.isoformat() if academy.created_at else None,
    }


def _serialize_application(app_rec: AcademyApplication) -> dict:
    return {
        "id": app_rec.id,
        "applicant_id": app_rec.applicant_id,
        "applicant_username": app_rec.applicant.username if app_rec.applicant else None,
        "name": app_rec.name,
        "description": app_rec.description,
        "address": app_rec.address,
        "city": app_rec.city,
        "state": app_rec.state,
        "country": app_rec.country,
        "contact_email": app_rec.contact_email,
        "contact_phone": app_rec.contact_phone,
        "sports_offered": app_rec.sports_offered,
        "website_url": app_rec.website_url,
        "status": app_rec.status,
        "reviewed_by_id": app_rec.reviewed_by_id,
        "reviewed_at": app_rec.reviewed_at.isoformat() if app_rec.reviewed_at else None,
        "rejection_reason": app_rec.rejection_reason,
        "academy_id": app_rec.academy_id,
        "created_at": app_rec.created_at.isoformat() if app_rec.created_at else None,
    }


@api_bp.route('/academies', methods=['GET'])
def list_academies():
    """Returns all verified active academies."""
    academies = Academy.query.filter_by(status='ACTIVE').order_by(Academy.created_at.desc()).all()
    return jsonify([_serialize_academy(a) for a in academies]), 200


@api_bp.route('/academies/<int:academy_id>', methods=['GET'])
def get_academy(academy_id: int):
    """Retrieve details for a single verified active academy."""
    academy = db.session.get(Academy, academy_id)
    if not academy or academy.status != 'ACTIVE':
        return jsonify({"error": "Academy not found or not active"}), 404
    return jsonify(_serialize_academy(academy)), 200


@api_bp.route('/academies/apply', methods=['POST'])
@jwt_required()
def apply_academy():
    """Submit a formal academy verification application."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    try:
        app_rec = submit_academy_application(user_id, data)
        return jsonify({
            "message": "Academy verification application submitted successfully.",
            "application": _serialize_application(app_rec)
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route('/academies/my-application', methods=['GET'])
@jwt_required()
def get_my_application():
    """Fetch the authenticated user's latest academy application."""
    user_id = int(get_jwt_identity())
    app_rec = AcademyApplication.query.filter_by(
        applicant_id=user_id
    ).order_by(AcademyApplication.created_at.desc()).first()

    if not app_rec:
        return jsonify({"application": None}), 200

    return jsonify({"application": _serialize_application(app_rec)}), 200


@api_bp.route('/admin/academies/applications', methods=['GET'])
@jwt_required()
def platform_list_applications():
    """Platform Superadmin / Support view of all academy verification applications."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user or not has_permission(user, PERM_PLATFORM_ACADEMIES_VIEW):
        return jsonify({"error": "Forbidden"}), 403

    status_filter = request.args.get('status')
    query = AcademyApplication.query
    if status_filter:
        query = query.filter_by(status=status_filter.upper())
    applications = query.order_by(AcademyApplication.created_at.desc()).all()

    return jsonify([_serialize_application(a) for a in applications]), 200


@api_bp.route('/admin/academies/applications/<int:app_id>/review', methods=['POST'])
@jwt_required()
def platform_review_application(app_id: int):
    """Platform Superadmin verifies or rejects an application."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user or not has_permission(user, PERM_PLATFORM_ACADEMIES_VERIFY):
        return jsonify({"error": "Forbidden: Superadmin permission required to verify academies."}), 403

    data = request.get_json() or {}
    decision = data.get("decision", "").strip().upper()
    rejection_reason = data.get("rejection_reason", "").strip()

    try:
        app_rec, academy = review_academy_application(
            application_id=app_id,
            reviewer_user=user,
            decision=decision,
            rejection_reason=rejection_reason
        )
        resp = {
            "message": f"Application {decision.lower()} successfully.",
            "application": _serialize_application(app_rec)
        }
        if academy:
            resp["academy"] = _serialize_academy(academy)
        return jsonify(resp), 200
    except (ValueError, PermissionError) as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route('/academies/<int:academy_id>/join', methods=['POST'])
@jwt_required()
def join_academy(academy_id: int):
    """Join an active academy under Single Active Academy Membership."""
    user_id = int(get_jwt_identity())
    try:
        member = add_academy_member(academy_id=academy_id, user_id=user_id, role="member")
        return jsonify({
            "message": "Successfully joined academy.",
            "membership_id": member.id,
            "academy_id": member.academy_id,
            "role": member.role,
            "status": member.membership_status
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route('/academies/<int:academy_id>/transfer', methods=['POST'])
@jwt_required()
def transfer_academy(academy_id: int):
    """Transfer active academy membership."""
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    reason = data.get("reason", "API requested transfer")
    try:
        member = transfer_user_academy_membership(
            user_id=user_id,
            target_academy_id=academy_id,
            reason=reason
        )
        return jsonify({
            "message": "Membership successfully transferred.",
            "membership_id": member.id,
            "academy_id": member.academy_id,
            "status": member.membership_status
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@api_bp.route('/academies/<int:academy_id>/leave', methods=['POST'])
@jwt_required()
def leave_academy(academy_id: int):
    """Leave current active academy."""
    user_id = int(get_jwt_identity())
    try:
        leave_academy_membership(user_id=user_id, academy_id=academy_id)
        return jsonify({"message": "Successfully left academy."}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
