
with open('app/routes/player.py', 'r') as f:
    content = f.read()

route_code = """
@player_bp.route('/admin/players')
@login_required
@role_required('admin', 'superadmin')
def admin_players():
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        players = Player.query.filter(
            db.or_(
                Player.name.ilike(f'%{search_query}%'),
                Player.registration_no.ilike(f'%{search_query}%')
            )
        ).all()
    else:
        players = Player.query.all()
        
    return render_template('admin/players.html', players=players, search_query=search_query)
"""

if 'def admin_players():' not in content:
    content += "\n" + route_code
    with open('app/routes/player.py', 'w') as f:
        f.write(content)
    print("admin_players route added.")
else:
    print("Route already exists.")
