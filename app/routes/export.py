from flask import Blueprint, render_template, make_response, abort
from app.models import Tournament, Category
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
    
    # Group matches by round
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
    response.headers['Content-Disposition'] = f'attachment; filename={tournament.name}_{category.name}_Bracket.pdf'
    
    return response
