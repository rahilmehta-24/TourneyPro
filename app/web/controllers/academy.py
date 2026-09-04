from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from werkzeug.utils import secure_filename
import os
import csv
from app import db
from app.domain.models import Academy, AcademyMember, AcademyAnnouncement, Tournament, User, Player
from app.web.controllers.auth import login_required, get_current_user

academy_bp = Blueprint('academy', __name__, url_prefix='/academies')

@academy_bp.route('/')
def index():
    """List all academies"""
    academies = Academy.query.order_by(Academy.created_at.desc()).all()
    return render_template('academy/index.html', academies=academies)

@academy_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new academy (Admin/Superadmin only)"""
    current_user = get_current_user()
    if current_user.role not in ['admin', 'superadmin']:
        flash('Only administrators can create an academy.', 'error')
        return redirect(url_for('academy.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Generate slug
        import re
        base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        slug = base_slug
        counter = 1
        while Academy.query.filter_by(url_slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
            
        academy = Academy(
            name=name,
            url_slug=slug,
            description=description,
            owner_id=current_user.id
        )
        db.session.add(academy)
        db.session.flush() # to get academy.id
        
        # Add owner as admin member
        member = AcademyMember(
            academy_id=academy.id,
            user_id=current_user.id,
            role='admin'
        )
        db.session.add(member)
        db.session.commit()
        
        flash('Academy created successfully!', 'success')
        return redirect(url_for('academy.dashboard', slug=academy.url_slug))
        
    return render_template('academy/create.html')

@academy_bp.route('/<slug>')
def dashboard(slug):
    """Academy Dashboard (Public view, enriched for members)"""
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()
    
    current_user = get_current_user()
    is_member = False
    member_role = None
    if current_user:
        membership = AcademyMember.query.filter_by(academy_id=academy.id, user_id=current_user.id).first()
        if membership:
            is_member = True
            member_role = membership.role
            
    announcements = AcademyAnnouncement.query.filter_by(academy_id=academy.id).order_by(AcademyAnnouncement.created_at.desc()).limit(10).all()
    tournaments = Tournament.query.filter_by(academy_id=academy.id).order_by(Tournament.created_at.desc()).all()
    
    return render_template('academy/dashboard.html', 
                           academy=academy, 
                           is_member=is_member, 
                           member_role=member_role,
                           announcements=announcements,
                           tournaments=tournaments)

@academy_bp.route('/<slug>/join', methods=['GET', 'POST'])
@login_required
def join(slug):
    """Form to join an academy"""
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()
    
    if AcademyMember.query.filter_by(academy_id=academy.id, user_id=current_user.id).first():
        flash('You are already a member of this academy.', 'info')
        return redirect(url_for('academy.dashboard', slug=slug))
        
    if request.method == 'POST':
        # Simple join, can be expanded to pending requests
        member = AcademyMember(
            academy_id=academy.id,
            user_id=current_user.id,
            role='member'
        )
        db.session.add(member)
        db.session.commit()
        flash(f'You have successfully joined {academy.name}!', 'success')
        return redirect(url_for('academy.dashboard', slug=slug))
        
    return render_template('academy/join.html', academy=academy)

@academy_bp.route('/<slug>/members', methods=['GET', 'POST'])
@login_required
def members(slug):
    """Manage members (Admin only)"""
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()
    
    membership = AcademyMember.query.filter_by(academy_id=academy.id, user_id=current_user.id).first()
    if not membership or membership.role != 'admin':
        flash('You do not have permission to manage members.', 'error')
        return redirect(url_for('academy.dashboard', slug=slug))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_manual':
            email = request.form.get('email')
            role = request.form.get('role', 'member')
            user = User.query.filter_by(email=email).first()
            if user:
                if not AcademyMember.query.filter_by(academy_id=academy.id, user_id=user.id).first():
                    new_member = AcademyMember(academy_id=academy.id, user_id=user.id, role=role)
                    db.session.add(new_member)
                    db.session.commit()
                    flash(f'Added {user.username} to academy.', 'success')
                else:
                    flash('User is already a member.', 'error')
            else:
                flash('User with that email not found. They must register first.', 'error')
                
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
                    for idx, row in enumerate(reader):
                        if idx == 0: continue # Skip header
                        if len(row) > 0:
                            email = row[0].strip()
                            user = User.query.filter_by(email=email).first()
                            if user and not AcademyMember.query.filter_by(academy_id=academy.id, user_id=user.id).first():
                                db.session.add(AcademyMember(academy_id=academy.id, user_id=user.id, role='member'))
                                added += 1
                            elif not user:
                                not_found += 1
                    db.session.commit()
                    flash(f'Successfully added {added} members. {not_found} emails not found in system.', 'success')
                    
        return redirect(url_for('academy.members', slug=slug))
        
    memberships = AcademyMember.query.filter_by(academy_id=academy.id).all()
    return render_template('academy/members.html', academy=academy, memberships=memberships)

@academy_bp.route('/<slug>/announcements', methods=['POST'])
@login_required
def post_announcement(slug):
    current_user = get_current_user()
    academy = Academy.query.filter_by(url_slug=slug).first_or_404()
    
    membership = AcademyMember.query.filter_by(academy_id=academy.id, user_id=current_user.id).first()
    if not membership or membership.role != 'admin':
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
