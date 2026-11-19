"""Create All-Formats Tournament Script for TourneyPro.

Creates a premier tournament with ALL 6 supported formats:
1. single_elimination: Men's Open Singles (16 players)
2. doubles_elimination: Men's Open Doubles (8 pairs = 16 players)
3. double_elimination: Boys U-18 Championship (8 players)
4. round_robin: Masters 35+ Singles League (5 players)
5. doubles_round_robin: Mixed Doubles Pro Trophy (4 pairs = 8 players)
6. group_stage: Women's Championship Trophy (16 players, 4 groups of 4)

Created by: superadmin (User ID 1)
Includes:
- Full realistic tennis player profiles (names, DOB, emails, phone, nationality, bio)
- Registrations with fees, UPI transaction IDs, approved statuses
- Participants with seeds, check-ins, payment statuses
- Full bracket & fixture generation for all 6 formats
- Actual played matches with realistic tennis scores and winner progressions
- Standings updates for Round Robin and Group Stage
- Full Order of Play scheduling across 8 courts
- Published draws
"""

import sys
import random
from datetime import date, datetime
from app import create_app
from app.domain.models import (
    db,
    User,
    Tournament,
    Category,
    Player,
    Participant,
    Registration,
    Group,
    Match,
    TournamentSettings,
)
from app.services.format_engine import get_format
from app.services.leaderboard import update_live_player_stats, recalculate_all_group_stats
from app.services.utils.scheduler import auto_schedule_tournament

def create_all_formats_tournament():
    app = create_app()
    with app.app_context():
        # 1. Fetch Superadmin
        superadmin = User.query.filter_by(role="superadmin").first()
        if not superadmin:
            print("ERROR: Superadmin user not found!")
            sys.exit(1)

        print(f"Using Superadmin: {superadmin.username} (ID: {superadmin.id}, Email: {superadmin.email})")

        slug = "apex-world-tour-championship-2026"

        # Check existing tournament and clean up if previously run
        existing = Tournament.query.filter_by(url_slug=slug).first()
        if existing:
            print(f"Cleaning up existing tournament '{slug}'...")
            db.session.delete(existing)
            db.session.commit()

        # 2. Create Tournament
        start_date = date(2026, 11, 20)
        end_date = date(2026, 11, 29)

        tournament = Tournament(
            name="Apex World Tour Championship 2026",
            url_slug=slug,
            user_id=superadmin.id,
            creator_name=superadmin.username,
            description=(
                "The premier all-format championship featuring Single Elimination, Doubles Knockout, "
                "Double Elimination, Round Robin Leagues, Doubles Round Robin, and Group Stage World Tour formats."
            ),
            game_info="Grand National Tennis Arena, Center Court & Courts 1-7",
            status="in_progress",
            has_categories=True,
            start_date=start_date,
            end_date=end_date,
            num_courts=8,
            court_names="Center Court, Court 1, Court 2, Court 3, Court 4, Court 5, Court 6, Court 7",
            court_operating_start="08:00",
            court_operating_end="20:00",
            avg_match_duration=75,
            court_buffer_minutes=15,
            min_rest_minutes=45,
            max_matches_per_player_day=3,
            payment_upi_id="apex.masters@upi",
            started_at=datetime(2026, 11, 20, 8, 0, 0),
        )
        db.session.add(tournament)
        db.session.flush()

        settings = TournamentSettings(
            tournament_id=tournament.id,
            allow_self_registration=True,
            require_check_in=True,
            allow_match_attachments=True,
            hide_seeds=False,
            quick_advance=True,
        )
        db.session.add(settings)
        db.session.flush()

        print(f"Created Tournament: '{tournament.name}' (ID: {tournament.id})")

        # 3. Create Player Profiles
        player_cache = {}

        def get_or_create_player(name, gender, age_cat, nationality, email, mobile, dob_year):
            p = Player.query.filter_by(name=name).first()
            if not p:
                p = Player(
                    name=name,
                    gender=gender,
                    age_category=age_cat,
                    nationality=nationality,
                    email=email,
                    contact_number=mobile,
                    dob=date(dob_year, random.randint(1, 12), random.randint(1, 28)),
                    current_status="Active",
                    primary_sport="Tennis",
                    skill_level="Professional",
                    profile_status="complete",
                )
                db.session.add(p)
                db.session.flush()
            player_cache[name] = p
            return p

        # Men's Open Players
        singles_men_data = [
            ("Carlos Alcaraz", "Spain", 2003),
            ("Jannik Sinner", "Italy", 2001),
            ("Novak Djokovic", "Serbia", 1987),
            ("Daniil Medvedev", "Monaco", 1996),
            ("Alexander Zverev", "Germany", 1997),
            ("Stefanos Tsitsipas", "Greece", 1998),
            ("Casper Ruud", "Norway", 1998),
            ("Holger Rune", "Denmark", 2003),
            ("Taylor Fritz", "USA", 1997),
            ("Alex de Minaur", "Australia", 1999),
            ("Grigor Dimitrov", "Bulgaria", 1991),
            ("Hubert Hurkacz", "Poland", 1997),
            ("Tommy Paul", "USA", 1997),
            ("Ben Shelton", "USA", 2002),
            ("Frances Tiafoe", "USA", 1998),
            ("Sebastian Korda", "USA", 2000),
        ]
        for idx, (name, nat, yr) in enumerate(singles_men_data):
            em = f"{name.lower().replace(' ', '.')}@atptour.com"
            mob = f"+91 98110{1000 + idx:04d}"
            get_or_create_player(name, "Male", "Open", nat, em, mob, yr)

        # Men's Doubles Players
        doubles_men_pairs = [
            (("Rohan Bopanna", "India", 1980), ("Matthew Ebden", "Australia", 1987)),
            (("Rajeev Ram", "USA", 1984), ("Joe Salisbury", "Great Britain", 1992)),
            (("Marcel Granollers", "Spain", 1986), ("Horacio Zeballos", "Argentina", 1985)),
            (("Wesley Koolhof", "Netherlands", 1989), ("Nikola Mektic", "Croatia", 1988)),
            (("Kevin Krawietz", "Germany", 1992), ("Tim Puetz", "Germany", 1987)),
            (("Simone Bolelli", "Italy", 1985), ("Andrea Vavassori", "Italy", 1995)),
            (("Max Purcell", "Australia", 1998), ("Jordan Thompson", "Australia", 1994)),
            (("Harri Heliovaara", "Finland", 1989), ("Henry Patten", "Great Britain", 1995)),
        ]
        d_idx = 0
        for p1_tuple, p2_tuple in doubles_men_pairs:
            for p_tuple in (p1_tuple, p2_tuple):
                name, nat, yr = p_tuple
                em = f"{name.lower().replace(' ', '.')}@atptour.com"
                mob = f"+91 98220{2000 + d_idx:04d}"
                get_or_create_player(name, "Male", "Open", nat, em, mob, yr)
                d_idx += 1

        # Junior U-18 Players
        u18_players_data = [
            ("Aryan Shah", "India", 2008),
            ("Manas Dhamne", "India", 2008),
            ("Yuvan Nandal", "India", 2009),
            ("Rethin Pranav", "India", 2008),
            ("Kriish Tyagi", "India", 2009),
            ("Rushil Khosla", "India", 2008),
            ("Daksh Prasad", "India", 2009),
            ("Vansh Nandal", "India", 2009),
        ]
        for idx, (name, nat, yr) in enumerate(u18_players_data):
            em = f"{name.lower().replace(' ', '.')}@itftennis.com"
            mob = f"+91 98330{3000 + idx:04d}"
            get_or_create_player(name, "Male", "U18", nat, em, mob, yr)

        # Masters 35+ Players
        masters_players_data = [
            ("Somdev Devvarman", "India", 1985),
            ("Yuki Bhambri", "India", 1988),
            ("Ramkumar Ramanathan", "India", 1989),
            ("Saketh Myneni", "India", 1987),
            ("Jeevan Nedunchezhiyan", "India", 1988),
        ]
        for idx, (name, nat, yr) in enumerate(masters_players_data):
            em = f"{name.lower().replace(' ', '.')}@aitatennis.com"
            mob = f"+91 98440{4000 + idx:04d}"
            get_or_create_player(name, "Male", "Open", nat, em, mob, yr)

        # Mixed Doubles Players
        mixed_doubles_pairs = [
            (("Sania Mirza", "India", 1986, "Female"), ("Mahesh Bhupathi", "India", 1974, "Male")),
            (("Ankita Raina", "India", 1993, "Female"), ("Rohan Bopanna", "India", 1980, "Male")),
            (("Karman Kaur Thandi", "India", 1998, "Female"), ("Leander Paes", "India", 1973, "Male")),
            (("Rutuja Bhosale", "India", 1996, "Female"), ("Purav Raja", "India", 1985, "Male")),
        ]
        mxd_idx = 0
        for p1_info, p2_info in mixed_doubles_pairs:
            for name, nat, yr, g in (p1_info, p2_info):
                em = f"{name.lower().replace(' ', '.')}@itftennis.com"
                mob = f"+91 98550{5000 + mxd_idx:04d}"
                get_or_create_player(name, g, "Open", nat, em, mob, yr)
                mxd_idx += 1

        # Women's Open Players
        womens_players_data = [
            ("Iga Swiatek", "Poland", 2001),
            ("Aryna Sabalenka", "Belarus", 1998),
            ("Coco Gauff", "USA", 2004),
            ("Elena Rybakina", "Kazakhstan", 1999),
            ("Jessica Pegula", "USA", 1994),
            ("Marketa Vondrousova", "Czech Republic", 1999),
            ("Ons Jabeur", "Tunisia", 1994),
            ("Maria Sakkari", "Greece", 1995),
            ("Qinwen Zheng", "China", 2002),
            ("Jelena Ostapenko", "Latvia", 1997),
            ("Daria Kasatkina", "Australia", 1997),
            ("Barbora Krejcikova", "Czech Republic", 1995),
            ("Danielle Collins", "USA", 1993),
            ("Madison Keys", "USA", 1995),
            ("Paula Badosa", "Spain", 1997),
            ("Emma Navarro", "USA", 2001),
        ]
        for idx, (name, nat, yr) in enumerate(womens_players_data):
            em = f"{name.lower().replace(' ', '.')}@wtatour.com"
            mob = f"+91 98660{6000 + idx:04d}"
            get_or_create_player(name, "Female", "Open", nat, em, mob, yr)

        db.session.commit()
        print(f"Total Players available: {len(player_cache)}")

        # -------------------------------------------------------------
        # Helper: Enroll participant & registration
        # -------------------------------------------------------------
        def enroll_entry(cat, player1, player2=None, partner_display=None, seed=None, group_obj=None):
            disp_name = player1.name if not partner_display else f"{player1.name} / {partner_display}"
            p_mob = player1.contact_number
            p_em = player1.email
            p2_mob = player2.contact_number if player2 else None

            participant = Participant(
                tournament_id=tournament.id,
                category_id=cat.id,
                group_id=group_obj.id if group_obj else None,
                player_id=player1.id,
                player2_id=player2.id if player2 else None,
                partner_name=partner_display,
                partner_mobile=p2_mob,
                name=disp_name,
                email=p_em,
                mobile=p_mob,
                gender=player1.gender,
                dob=player1.dob,
                manual_seed=seed,
                checked_in=True,
                payment_status="paid",
                payment_method="online",
            )
            db.session.add(participant)
            db.session.flush()

            reg = Registration(
                tournament_id=tournament.id,
                category_id=cat.id,
                user_id=superadmin.id,
                player_id=player1.id,
                player2_id=player2.id if player2 else None,
                partner_name=partner_display,
                partner_mobile=p2_mob,
                amount_due=cat.entry_fee,
                payment_method="online",
                payment_status="paid",
                transaction_id=f"UPI-TXN-{random.randint(10000000, 99999999)}",
                status="approved",
            )
            db.session.add(reg)
            return participant

        # =============================================================
        # FORMAT 1: Single Elimination (Men's Open Singles)
        # =============================================================
        print("\n--- [1/6] Single Elimination: Men's Open Singles ---")
        cat1 = Category(
            tournament_id=tournament.id,
            name="Men's Open Singles (Knockout)",
            gender="Mens",
            age_category="Open",
            format="single_elimination",
            entry_fee=1000.0,
            status="setup",
            num_sets=3,
            games_per_set=6,
            draw_published=True,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(cat1)
        db.session.flush()

        cat1_participants = []
        for idx, (p_name, _, _) in enumerate(singles_men_data):
            p_obj = player_cache[p_name]
            seed_val = (idx + 1) if idx < 4 else None  # Seeds 1 to 4
            part = enroll_entry(cat1, p_obj, seed=seed_val)
            cat1_participants.append(part)

        db.session.commit()

        # Generate draw
        fmt1 = get_format("single_elimination")
        matches1 = fmt1.generate(cat1, cat1_participants)
        for m_data in matches1:
            m_data['category_id'] = cat1.id
            m = Match(**m_data, tournament_id=tournament.id)
            db.session.add(m)
        cat1.status = "in_progress"
        cat1.started_at = datetime.utcnow()
        db.session.commit()

        # Play 6 of the 8 Round 1 (R16) matches with realistic scores
        r1_matches1 = Match.query.filter_by(category_id=cat1.id, round=1).order_by(Match.match_number).all()
        tennis_scores = [
            ("6-4, 6-3", "4-6, 3-6", 1),
            ("6-2, 6-2", "2-6, 2-6", 1),
            ("6-3, 7-5", "3-6, 5-7", 1),
            ("7-6(4), 6-4", "6-7(4), 4-6", 1),
            ("6-4, 4-6, 6-3", "4-6, 6-4, 3-6", 1),
            ("6-3, 6-4", "3-6, 4-6", 1),
        ]
        for idx, (s1, s2, win_choice) in enumerate(tennis_scores):
            m = r1_matches1[idx]
            if m.participant1_id and m.participant2_id:
                winner_id = m.participant1_id if win_choice == 1 else m.participant2_id
                m.score1 = s1
                m.score2 = s2
                m.winner_id = winner_id
                m.status = "completed"
                m.completed_at = datetime.utcnow()
                update_live_player_stats(m)
                fmt1.advance_match(m, cat1, winner_id)
        db.session.commit()
        print(f"  Single Elimination: {len(cat1_participants)} players, {len(r1_matches1)} R1 matches, 6 completed & advanced to QF.")

        # =============================================================
        # FORMAT 2: Doubles Elimination (Men's Open Doubles)
        # =============================================================
        print("\n--- [2/6] Doubles Elimination: Men's Open Doubles ---")
        cat2 = Category(
            tournament_id=tournament.id,
            name="Men's Open Doubles (Knockout)",
            gender="Mens",
            age_category="Open",
            format="doubles_elimination",
            entry_fee=1500.0,
            status="setup",
            num_sets=3,
            games_per_set=6,
            draw_published=True,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(cat2)
        db.session.flush()

        cat2_participants = []
        for idx, (p1_info, p2_info) in enumerate(doubles_men_pairs):
            p1_obj = player_cache[p1_info[0]]
            p2_obj = player_cache[p2_info[0]]
            seed_val = (idx + 1) if idx < 4 else None
            part = enroll_entry(cat2, p1_obj, p2_obj, partner_display=p2_info[0], seed=seed_val)
            cat2_participants.append(part)

        db.session.commit()

        fmt2 = get_format("doubles_elimination")
        matches2 = fmt2.generate(cat2, cat2_participants)
        for m_data in matches2:
            m_data['category_id'] = cat2.id
            m = Match(**m_data, tournament_id=tournament.id)
            db.session.add(m)
        cat2.status = "in_progress"
        cat2.started_at = datetime.utcnow()
        db.session.commit()

        # Play 2 QF matches
        qf_matches2 = Match.query.filter_by(category_id=cat2.id, round=1).order_by(Match.match_number).all()
        qf_scores = [
            ("6-3, 6-4", "3-6, 4-6", 1),
            ("7-6(5), 4-6, 10-6", "6-7(5), 6-4, 6-10", 1),
        ]
        for idx, (s1, s2, win_choice) in enumerate(qf_scores):
            m = qf_matches2[idx]
            if m.participant1_id and m.participant2_id:
                winner_id = m.participant1_id if win_choice == 1 else m.participant2_id
                m.score1 = s1
                m.score2 = s2
                m.winner_id = winner_id
                m.status = "completed"
                m.completed_at = datetime.utcnow()
                update_live_player_stats(m)
                fmt2.advance_match(m, cat2, winner_id)
        db.session.commit()
        print(f"  Doubles Elimination: {len(cat2_participants)} pairs, 2 QF matches completed & advanced to SF.")

        # =============================================================
        # FORMAT 3: Double Elimination (Boys U-18 Championship)
        # =============================================================
        print("\n--- [3/6] Double Elimination: Boys U-18 Championship ---")
        cat3 = Category(
            tournament_id=tournament.id,
            name="Boys U-18 Championship (Double Elimination)",
            gender="Boys",
            age_category="U18",
            format="double_elimination",
            entry_fee=800.0,
            status="setup",
            num_sets=3,
            games_per_set=6,
            draw_published=True,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(cat3)
        db.session.flush()

        cat3_participants = []
        for idx, (p_name, _, _) in enumerate(u18_players_data):
            p_obj = player_cache[p_name]
            seed_val = (idx + 1) if idx < 4 else None
            part = enroll_entry(cat3, p_obj, seed=seed_val)
            cat3_participants.append(part)

        db.session.commit()

        fmt3 = get_format("double_elimination")
        matches3 = fmt3.generate(cat3, cat3_participants)
        for m_data in matches3:
            m_data['category_id'] = cat3.id
            m = Match(**m_data, tournament_id=tournament.id)
            db.session.add(m)
        cat3.status = "in_progress"
        cat3.started_at = datetime.utcnow()
        db.session.commit()

        # Complete 3 matches in Winners Bracket Round 1 so winners advance and losers drop down to Losers Bracket
        w_r1_matches3 = Match.query.filter_by(category_id=cat3.id, bracket_type="winners", round=1).order_by(Match.match_number).all()
        de_scores = [
            ("6-4, 6-2", "4-6, 2-6", 1),
            ("7-5, 6-3", "5-7, 3-6", 1),
            ("6-3, 4-6, 6-4", "3-6, 6-4, 4-6", 1),
        ]
        for idx, (s1, s2, win_choice) in enumerate(de_scores):
            if idx < len(w_r1_matches3):
                m = w_r1_matches3[idx]
                if m.participant1_id and m.participant2_id:
                    winner_id = m.participant1_id if win_choice == 1 else m.participant2_id
                    m.score1 = s1
                    m.score2 = s2
                    m.winner_id = winner_id
                    m.status = "completed"
                    m.completed_at = datetime.utcnow()
                    update_live_player_stats(m)
                    fmt3.advance_match(m, cat3, winner_id)
        db.session.commit()
        print(f"  Double Elimination: {len(cat3_participants)} players, 3 Winners R1 completed with losers moved to Losers Bracket.")

        # =============================================================
        # FORMAT 4: Round Robin (Masters 35+ Singles League)
        # =============================================================
        print("\n--- [4/6] Round Robin: Masters 35+ Singles League ---")
        cat4 = Category(
            tournament_id=tournament.id,
            name="Masters 35+ Singles League (Round Robin)",
            gender="Mens",
            age_category="Open",
            format="round_robin",
            entry_fee=750.0,
            status="setup",
            num_sets=1,
            games_per_set=6,
            draw_published=True,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(cat4)
        db.session.flush()

        cat4_participants = []
        for idx, (p_name, _, _) in enumerate(masters_players_data):
            p_obj = player_cache[p_name]
            part = enroll_entry(cat4, p_obj, seed=(idx + 1))
            cat4_participants.append(part)

        db.session.commit()

        fmt4 = get_format("round_robin")
        matches4 = fmt4.generate(cat4, cat4_participants)
        for m_data in matches4:
            m_data['category_id'] = cat4.id
            m = Match(**m_data, tournament_id=tournament.id)
            db.session.add(m)
        cat4.status = "in_progress"
        cat4.started_at = datetime.utcnow()
        db.session.commit()

        # Complete 4 round-robin matches
        rr_matches4 = Match.query.filter_by(category_id=cat4.id).order_by(Match.id).all()
        rr_scores = [
            ("6-4, 6-3", "4-6, 3-6", 1),
            ("7-6(3), 6-4", "6-7(3), 4-6", 2),
            ("6-2, 6-1", "2-6, 1-6", 1),
            ("6-3, 3-6, 6-4", "3-6, 6-3, 4-6", 1),
        ]
        for idx, (s1, s2, win_choice) in enumerate(rr_scores):
            if idx < len(rr_matches4):
                m = rr_matches4[idx]
                if m.participant1_id and m.participant2_id:
                    winner_id = m.participant1_id if win_choice == 1 else m.participant2_id
                    m.score1 = s1
                    m.score2 = s2
                    m.winner_id = winner_id
                    m.status = "completed"
                    m.completed_at = datetime.utcnow()
                    update_live_player_stats(m)
                    fmt4.advance_match(m, cat4, winner_id)
        db.session.commit()
        recalculate_all_group_stats(cat4.id)
        print(f"  Round Robin: {len(cat4_participants)} players, {len(rr_matches4)} fixtures, 4 matches completed with live standings.")

        # =============================================================
        # FORMAT 5: Doubles Round Robin (Mixed Doubles Pro Trophy)
        # =============================================================
        print("\n--- [5/6] Doubles Round Robin: Mixed Doubles Pro Trophy ---")
        cat5 = Category(
            tournament_id=tournament.id,
            name="Mixed Doubles Pro Trophy (Doubles Round Robin)",
            gender="Mixed",
            age_category="Open",
            format="doubles_round_robin",
            entry_fee=1200.0,
            status="setup",
            num_sets=1,
            games_per_set=6,
            draw_published=True,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(cat5)
        db.session.flush()

        cat5_participants = []
        for idx, (p1_info, p2_info) in enumerate(mixed_doubles_pairs):
            p1_obj = player_cache[p1_info[0]]
            p2_obj = player_cache[p2_info[0]]
            part = enroll_entry(cat5, p1_obj, p2_obj, partner_display=p2_info[0], seed=(idx + 1))
            cat5_participants.append(part)

        db.session.commit()

        fmt5 = get_format("doubles_round_robin")
        matches5 = fmt5.generate(cat5, cat5_participants)
        for m_data in matches5:
            m_data['category_id'] = cat5.id
            m = Match(**m_data, tournament_id=tournament.id)
            db.session.add(m)
        cat5.status = "in_progress"
        cat5.started_at = datetime.utcnow()
        db.session.commit()

        # Complete 3 matches
        drr_matches5 = Match.query.filter_by(category_id=cat5.id).order_by(Match.id).all()
        drr_scores = [
            ("6-3, 6-4", "3-6, 4-6", 1),
            ("7-5, 6-2", "5-7, 2-6", 2),
            ("6-4, 4-6, 10-7", "4-6, 6-4, 7-10", 1),
        ]
        for idx, (s1, s2, win_choice) in enumerate(drr_scores):
            if idx < len(drr_matches5):
                m = drr_matches5[idx]
                if m.participant1_id and m.participant2_id:
                    winner_id = m.participant1_id if win_choice == 1 else m.participant2_id
                    m.score1 = s1
                    m.score2 = s2
                    m.winner_id = winner_id
                    m.status = "completed"
                    m.completed_at = datetime.utcnow()
                    update_live_player_stats(m)
                    fmt5.advance_match(m, cat5, winner_id)
        db.session.commit()
        recalculate_all_group_stats(cat5.id)
        print(f"  Doubles Round Robin: {len(cat5_participants)} pairs, {len(drr_matches5)} fixtures, 3 completed with live standings.")

        # =============================================================
        # FORMAT 6: Group Stage (Women's Championship Trophy)
        # =============================================================
        print("\n--- [6/6] Group Stage + Knockout: Women's Championship Trophy ---")
        cat6 = Category(
            tournament_id=tournament.id,
            name="Women's Championship Trophy (Group Stage + Knockout)",
            gender="Womens",
            age_category="Open",
            format="group_stage",
            entry_fee=1000.0,
            status="setup",
            has_group_stage=True,
            num_groups=4,
            teams_per_group=4,
            qualifiers_per_group=2,
            total_games=7,
            scoring_format="games",
            draw_published=True,
            start_date=start_date,
            end_date=end_date,
        )
        db.session.add(cat6)
        db.session.flush()

        # Create 4 Groups: Group A, Group B, Group C, Group D
        group_letters = ["A", "B", "C", "D"]
        group_objs = []
        for g_idx, letter in enumerate(group_letters):
            grp = Group(
                category_id=cat6.id,
                name=f"Group {letter}",
                assigned_courts=f"Court {g_idx + 1}",
                start_time="09:00" if g_idx < 2 else "13:30",
            )
            db.session.add(grp)
            db.session.flush()
            group_objs.append(grp)

        # Distribute 16 players: 4 per group
        cat6_participants = []
        for idx, (p_name, _, _) in enumerate(womens_players_data):
            p_obj = player_cache[p_name]
            grp = group_objs[idx // 4]
            seed_val = (idx % 4) + 1 if (idx % 4) < 2 else None  # Top 2 seeds in each group
            part = enroll_entry(cat6, p_obj, seed=seed_val, group_obj=grp)
            cat6_participants.append(part)

        db.session.commit()

        fmt6 = get_format("group_stage")
        matches6 = fmt6.generate(cat6, cat6_participants)
        for m_data in matches6:
            sub_rubbers = m_data.pop('sub_matches', None)
            m_data['category_id'] = cat6.id
            m = Match(**m_data, tournament_id=tournament.id)
            db.session.add(m)
            if sub_rubbers:
                db.session.flush()
                for s_data in sub_rubbers:
                    s_data['parent_match_id'] = m.id
                    s_data['category_id'] = cat6.id
                    s_data['match_type'] = 'group_stage'
                    s_match = Match(**s_data, tournament_id=tournament.id)
                    db.session.add(s_match)
        cat6.status = "in_progress"
        cat6.started_at = datetime.utcnow()
        db.session.commit()

        # Complete 2 matches per group = 8 group matches completed
        gs_matches6 = Match.query.filter_by(category_id=cat6.id, parent_match_id=None).order_by(Match.group_id, Match.match_number).all()
        # Group matches:
        gs_scores = [
            ("6-4", "4-6", 1),
            ("6-2", "2-6", 1),
            ("7-5", "5-7", 1),
            ("6-3", "3-6", 1),
            ("6-1", "1-6", 1),
            ("7-6(4)", "6-7(4)", 1),
            ("6-4", "4-6", 1),
            ("6-3", "3-6", 1),
        ]
        # Complete first 2 matches from each group
        matches_per_grp_completed = {g.id: 0 for g in group_objs}
        score_idx = 0
        for m in gs_matches6:
            if m.group_id and matches_per_grp_completed[m.group_id] < 2:
                if m.participant1_id and m.participant2_id:
                    s1, s2, win_choice = gs_scores[score_idx % len(gs_scores)]
                    score_idx += 1
                    winner_id = m.participant1_id if win_choice == 1 else m.participant2_id
                    m.score1 = s1
                    m.score2 = s2
                    m.winner_id = winner_id
                    m.status = "completed"
                    m.completed_at = datetime.utcnow()
                    update_live_player_stats(m)
                    fmt6.advance_match(m, cat6, winner_id)
                    matches_per_grp_completed[m.group_id] += 1
        db.session.commit()
        recalculate_all_group_stats(cat6.id)
        print("  Group Stage: 4 groups of 4 (16 players), 8 group matches completed with live points & standings.")

        # =============================================================
        # 4. Auto-Schedule All Tournament Matches Across Courts
        # =============================================================
        print("\n--- Auto-scheduling Tournament Matches ---")
        try:
            sched_result = auto_schedule_tournament(tournament.id)
            print(f"Scheduling completed: {sched_result}")
        except Exception as e:
            print(f"Scheduling notice: {e}")

        db.session.commit()

        # 5. Summary Report
        print("\n" + "=" * 70)
        print("TOURNAMENT GENERATION COMPLETE!")
        print("=" * 70)
        print(f"Tournament:    {tournament.name}")
        print(f"Slug:          {tournament.url_slug}")
        print(f"Created By:    {superadmin.username} (Role: {superadmin.role})")
        print(f"URL:           /tournaments/{tournament.url_slug}")
        print(f"Order of Play: /tournaments/{tournament.url_slug}/schedule")
        print("Total Categories Created: 6 (Covering ALL Supported Formats):")
        
        all_cats = Category.query.filter_by(tournament_id=tournament.id).all()
        for idx, cat in enumerate(all_cats):
            p_count = Participant.query.filter_by(category_id=cat.id).count()
            m_count = Match.query.filter_by(category_id=cat.id, parent_match_id=None).count()
            comp_count = Match.query.filter_by(category_id=cat.id, parent_match_id=None, status="completed").count()
            print(f"  {idx + 1}. {cat.name} [{cat.format}]")
            print(f"     Participants: {p_count} | Fixtures: {m_count} | Completed Matches: {comp_count}")

        print("=" * 70)

if __name__ == "__main__":
    create_all_formats_tournament()
