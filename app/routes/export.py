import csv
import io
from flask import Blueprint, render_template, make_response, abort
from app.models import Tournament, Category, Match, Group
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO

export_bp = Blueprint('export', __name__)

@export_bp.route('/tournaments/<slug>/category/<int:category_id>/export_pdf')
def export_category_pdf(slug, category_id):
    slug = slug.strip()  # Clean slug
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)

    # Verify category belongs to tournament
    if category.tournament_id != tournament.id:
        abort(404)

    if category.format in ['round_robin', 'group_stage']:
        # Fetch group standings and matches for round robin
        groups_data = []
        if category.format == 'group_stage':
            groups = Group.query.filter_by(category_id=category.id).order_by(Group.name).all()
            for group in groups:
                standings = group.get_standings()
                group_matches = Match.query.filter_by(group_id=group.id).order_by(Match.round, Match.match_number).all()
                groups_data.append({
                    'name': group.name,
                    'standings': standings,
                    'matches': group_matches
                })
        else:
            # Round robin is just one big group effectively
            standings = category.get_standings()
            matches = Match.query.filter_by(category_id=category.id).order_by(Match.round, Match.match_number).all()
            groups_data.append({
                'name': 'Round Robin',
                'standings': standings,
                'matches': matches
            })
            
        html_out = render_template('export/round_robin_pdf.html',
                             tournament=tournament,
                             category=category,
                             groups_data=groups_data,
                             now=datetime.now())
    else:
        # Group matches by round for bracket
        rounds = {}
        for match in category.matches:
            if match.round not in rounds:
                rounds[match.round] = []
            rounds[match.round].append(match)

        # Sort matches within rounds
        for r in rounds:
            rounds[r].sort(key=lambda x: x.match_number)

        # Render HTML for PDF
        html_out = render_template('export/bracket_pdf.html',
                                 tournament=tournament,
                                 category=category,
                                 rounds=rounds,
                                 now=datetime.now())

    # Generate PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_out, dest=pdf_buffer)

    if pisa_status.err:
        return 'PDF generation error', 500

    pdf_buffer.seek(0)

    # Create response
    response = make_response(pdf_buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{tournament.name}_{category.name}_Report.pdf"'

    return response

@export_bp.route('/tournaments/<slug>/category/<int:category_id>/export_matches_csv')
def export_matches_csv(slug, category_id):
    slug = slug.strip()
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    if category.tournament_id != tournament.id:
        abort(404)
        
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Matches Export
    writer.writerow(['Round', 'Match Number', 'Status', 'Player 1', 'Player 2', 'Score', 'Winner'])
    
    matches = Match.query.filter_by(category_id=category.id).order_by(Match.round, Match.match_number).all()
    for match in matches:
        p1_name = match.participant1.name if match.participant1 else 'TBD'
        p2_name = match.participant2.name if match.participant2 else 'TBD'
        
        # Combine score
        score = ""
        if match.score1 or match.score2:
            score = f"{match.score1 or '0'} - {match.score2 or '0'}"
            
        winner_name = ''
        if match.winner_id:
            if match.winner_id == match.participant1_id:
                winner_name = p1_name
            elif match.winner_id == match.participant2_id:
                winner_name = p2_name
                
        writer.writerow([match.round, match.match_number, match.status, p1_name, p2_name, score, winner_name])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=\"{tournament.name}_{category.name}_Matches.csv\""
    output.headers["Content-type"] = "text/csv"
    return output

@export_bp.route('/tournaments/<slug>/category/<int:category_id>/export_standings_csv')
def export_standings_csv(slug, category_id):
    slug = slug.strip()
    tournament = Tournament.query.filter_by(url_slug=slug).first_or_404()
    category = Category.query.get_or_404(category_id)
    
    if category.tournament_id != tournament.id:
        abort(404)
        
    if category.format not in ['round_robin', 'group_stage']:
        abort(400, "Standings export is only available for Round Robin and Group Stage formats.")
        
    si = io.StringIO()
    writer = csv.writer(si)
    
    groups_data = []
    if category.format == 'group_stage':
        groups = Group.query.filter_by(category_id=category.id).order_by(Group.name).all()
        for group in groups:
            groups_data.append({
                'name': group.name,
                'standings': group.get_standings()
            })
    else:
        groups_data.append({
            'name': 'Standings',
            'standings': category.get_standings()
        })
        
    for group in groups_data:
        writer.writerow([f"--- {group['name']} ---"])
        writer.writerow(['Rank', 'Player', 'Played', 'Won', 'Lost', 'Points For', 'Points Against', 'Points Diff'])
        
        for idx, p in enumerate(group['standings']):
            writer.writerow([
                idx + 1,
                p.name,
                p.matches_played,
                p.matches_won,
                p.matches_lost,
                p.points_for,
                p.points_against,
                p.points_difference
            ])
        writer.writerow([])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=\"{tournament.name}_{category.name}_Standings.csv\""
    output.headers["Content-type"] = "text/csv"
    return output
