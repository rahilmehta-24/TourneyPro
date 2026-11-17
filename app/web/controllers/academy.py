from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
import csv
from datetime import datetime
from app import db
from app.domain.models import Academy, AcademyMember, AcademyAnnouncement, AcademyApplication, Tournament, User
from app.web.controllers.auth import login_required, get_current_user, check_academy_access
from app.services.academy_service import (
    submit_academy_application,
    add_academy_member,
    transfer_user_academy_membership,
    leave_academy_membership,
    get_user_active_academy_membership,
)
from app.services.rbac_service import has_permission
from app.domain.constants import PERM_ACADEMY_MEMBERS_MANAGE, PERM_PLATFORM_ACADEMIES_VERIFY

academy_bp = Blueprint('academy', __name__, url_prefix='/academies')


@academy_bp.route('/')
def index():
    """List all verified active academies."""
    academies = Academy.query.filter_by(status='ACTIVE').order_by(Academy.created_at.desc()).all()
    current_user = get_current_user()
    user_app = None
    if current_user:
        user_app = AcademyApplication.query.filter_by(
            applicant_id=current_user.id
        ).order_by(AcademyApplication.created_at.desc()).first()

    return render_template('academy/index.html', academies=academies, user_application=user_app)


@academy_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    """Submit a formal academy verification application."""
    current_user = get_current_user()

    # Check if user already owns an active academy
    existing_owned = Academy.query.filter_by(owner_id=current_user.id, status='ACTIVE').first()
    if existing_owned:
        flash(f'You already own an active verified academy: {existing_owned.name}', 'info')
        return redirect(url_for('academy.dashboard', slug=existing_owned.url_slug))

    # Check existing pending application
    pending_app = AcademyApplication.query.filter_by(
        applicant_id=current_user.id,
        status='PENDING'
    ).first()
    if pending_app:
        flash('You have an academy verification application pending platform review.', 'info')
        return redirect(url_for('academy.application_status'))

    if request.method == 'POST':
        data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'address': request.form.get('address'),
            'city': request.form.get('city'),
            'state': request.form.get('state'),
            'country': request.form.get('country'),
            'contact_email': request.form.get('contact_email'),
            'contact_phone': request.form.get('contact_phone'),
            'sports_offered': request.form.get('sports_offered'),
            'website_url': request.form.get('website_url'),
        }
        try:
            app_record = submit_academy_application(current_user.id, data)
            flash('Your academy application has been submitted for platform superadmin review!', 'success')
            return redirect(url_for('academy.application_status'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('academy/apply.html', form_data=data)

    return render_template('academy/apply.html', form_data={'contact_email': current_user.email})


@academy_bp.route('/application-status')
@login_required
def application_status():
    """View status of current user's academy application."""
    current_user = get_current_user()
    latest_app = AcademyApplication.query.filter_by(
        applicant_id=current_user.id
    ).order_by(AcademyApplication.created_at.desc()).first()

    return render_template('academy/application_status.html', application=latest_app)


@academy_bp.route('/<slug>')
def dashboard(slug):
    """Academy Dashboard (Public view for verified active academy)."""
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()

    current_user = get_current_user()
    # If not active, only superadmin or owner can view
    if academy.status != 'ACTIVE':
        if not current_user or (current_user.role != 'superadmin' and academy.owner_id != current_user.id):
            abort(404)

    is_member = False
    member_role = None
    if current_user:
        membership = AcademyMember.query.filter_by(
            academy_id=academy.id,
            user_id=current_user.id,
            membership_status='ACTIVE'
        ).first()
        if membership:
            is_member = True
            member_role = membership.role

    announcements = AcademyAnnouncement.query.filter_by(
        academy_id=academy.id
    ).order_by(AcademyAnnouncement.created_at.desc()).limit(10).all()

    tournaments = Tournament.query.filter_by(
        academy_id=academy.id
    ).order_by(Tournament.created_at.desc()).all()

    active_membership_elsewhere = None
    if current_user and not is_member:
        active_membership_elsewhere = get_user_active_academy_membership(current_user.id)

    return render_template(
        'academy/dashboard.html',
        academy=academy,
        is_member=is_member,
        member_role=member_role,
        announcements=announcements,
        tournaments=tournaments,
        active_membership_elsewhere=active_membership_elsewhere
    )


@academy_bp.route('/<slug>/join', methods=['GET', 'POST'])
@login_required
def join(slug):
    """Enroll into an academy under strict Single Active Academy Membership."""
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug, status='ACTIVE').first_or_404()

    existing_membership = AcademyMember.query.filter_by(
        academy_id=academy.id,
        user_id=current_user.id,
        membership_status='ACTIVE'
    ).first()

    if existing_membership:
        flash('You are already an active member of this academy.', 'info')
        return redirect(url_for('academy.dashboard', slug=slug))

    other_membership = get_user_active_academy_membership(current_user.id)

    if request.method == 'POST':
        try:
            add_academy_member(academy.id, current_user.id, role='member')
            flash(f'You have successfully joined {academy.name}!', 'success')
            return redirect(url_for('academy.dashboard', slug=slug))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template(
                'academy/join.html',
                academy=academy,
                current_membership=other_membership
            )

    return render_template(
        'academy/join.html',
        academy=academy,
        current_membership=other_membership
    )


@academy_bp.route('/<slug>/transfer', methods=['POST'])
@login_required
def transfer(slug):
    """Transfer active academy membership from previous academy to this academy."""
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug, status='ACTIVE').first_or_404()

    try:
        transfer_user_academy_membership(
            user_id=current_user.id,
            target_academy_id=academy.id,
            acting_user=current_user,
            reason="User self-service transfer"
        )
        flash(f'Successfully transferred your active membership to {academy.name}!', 'success')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('academy.dashboard', slug=slug))


@academy_bp.route('/<slug>/leave', methods=['POST'])
@login_required
def leave(slug):
    """Leave current active academy."""
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()

    try:
        leave_academy_membership(current_user.id, academy.id)
        flash(f'You have left {academy.name}.', 'info')
    except ValueError as e:
        flash(str(e), 'error')

    return redirect(url_for('academy.index'))


@academy_bp.route('/<slug>/members', methods=['GET', 'POST'])
@login_required
def members(slug):
    """Manage members (Academy Admin/Owner or Superadmin)."""
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()
    current_user = get_current_user()

    scope = {'academy_id': academy.id, 'academy': academy}
    if not has_permission(current_user, PERM_ACADEMY_MEMBERS_MANAGE, scope=scope):
        abort(403)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_manual':
            email = (request.form.get('email') or '').strip().lower()
            role = request.form.get('role', 'member')
            user = User.query.filter_by(email=email).first()
            if not user:
                flash('User with that email not found. They must register first.', 'error')
            else:
                try:
                    add_academy_member(academy.id, user.id, role=role, acting_user=current_user)
                    flash(f'Added {user.username} to {academy.name}.', 'success')
                except ValueError as e:
                    flash(str(e), 'error')

        elif action == 'upload_csv':
            if 'csv_file' not in request.files:
                flash('No file uploaded.', 'error')
            else:
                file = request.files['csv_file']
                if file.filename != '':
                    content = file.read().decode('utf-8').splitlines()
                    reader = csv.reader(content)
                    added = 0
                    not_found = 0
                    conflicts = 0
                    for idx, row in enumerate(reader):
                        if idx == 0:
                            continue  # Skip header
                        if len(row) > 0:
                            email = row[0].strip().lower()
                            user = User.query.filter_by(email=email).first()
                            if not user:
                                not_found += 1
                                continue
                            try:
                                add_academy_member(academy.id, user.id, role='member', acting_user=current_user)
                                added += 1
                            except ValueError:
                                conflicts += 1

                    msg = f'Successfully added {added} members.'
                    if not_found:
                        msg += f' {not_found} emails not found.'
                    if conflicts:
                        msg += f' {conflicts} users skipped because they have active memberships in other academies.'
                    flash(msg, 'info')

        return redirect(url_for('academy.members', slug=slug))

    memberships = AcademyMember.query.filter_by(
        academy_id=academy.id,
        membership_status='ACTIVE'
    ).all()
    return render_template('academy/members.html', academy=academy, memberships=memberships)


@academy_bp.route('/<slug>/announcements', methods=['POST'])
@login_required
def post_announcement(slug):
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()

    scope = {'academy_id': academy.id, 'academy': academy}
    if not has_permission(current_user, PERM_ACADEMY_MEMBERS_MANAGE, scope=scope):
        abort(403)

    title = request.form.get('title')
    content = request.form.get('content')

    if title and content:
        announcement = AcademyAnnouncement(
            academy_id=academy.id,
            author_id=current_user.id,
            title=title,
            content=content
        )
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement posted.', 'success')

    return redirect(url_for('academy.dashboard', slug=slug))
