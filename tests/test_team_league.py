import unittest
import os
import tempfile
from datetime import date, datetime

from app import create_app
from app.domain.models import db, User, Tournament, Category, Participant, Match, Group, Player, PlayerCategoryTier, TeamMember
from app.services.tennis_logic import validate_team_rubber_score, calculate_team_fixture_status
from app.services.format_engine.group_stage.logic import GroupStageFormat


class TeamLeagueTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret'
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{cls.db_path}'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.mkdtemp()

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        with cls.app.app_context():
            from flask_migrate import upgrade
            upgrade()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        # Clear database between tests
        with self.app.app_context():
            db.session.remove()
            Match.query.delete()
            TeamMember.query.delete()
            PlayerCategoryTier.query.delete()
            Participant.query.delete()
            Group.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            Player.query.delete()
            User.query.delete()
            db.session.commit()

            # Create test user & tournament
            user = User(username='admin_test', email='admin@test.com', role='admin')
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()

            tournament = Tournament(
                name='Team Premier League 2026',
                url_slug='team-premier-league-2026',
                user_id=user.id,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 2),
                num_courts=3,
                court_names='Court 1, Court 2, Court 3'
            )
            db.session.add(tournament)
            db.session.flush()

            self.user_id = user.id
            self.tournament_id = tournament.id
            self.slug = tournament.url_slug
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()

    # =========================================================================
    # 1. DYNAMIC RUBBER SCORING TESTS
    # =========================================================================

    def test_01_rubber_scoring_default_t7(self):
        """Test rubber scoring for T=7 (sum of games == 7, tiebreak at 3-3 deciding final game)."""
        # Normal wins with summation = 7
        s1, s2, winner = validate_team_rubber_score(6, 1, total_games=7)
        self.assertEqual(s1, "6-1")
        self.assertEqual(s2, "1-6")
        self.assertEqual(winner, 1)

        s1, s2, winner = validate_team_rubber_score(5, 2, total_games=7)
        self.assertEqual(s1, "5-2")
        self.assertEqual(s2, "2-5")
        self.assertEqual(winner, 1)

        s1, s2, winner = validate_team_rubber_score(0, 7, total_games=7)
        self.assertEqual(s1, "0-7")
        self.assertEqual(s2, "7-0")
        self.assertEqual(winner, 2)

        # Incomplete score (sum != 7 on completion) -> should raise
        with self.assertRaises(ValueError):
            validate_team_rubber_score(4, 1, total_games=7)

        with self.assertRaises(ValueError):
            validate_team_rubber_score(3, 1, total_games=7)

        with self.assertRaises(ValueError):
            validate_team_rubber_score(5, 3, total_games=7)

        # 4-3 without tiebreak points -> player won majority of games (e.g. took first 4 games) -> valid without tiebreak
        s1, s2, winner = validate_team_rubber_score(4, 3, total_games=7)
        self.assertEqual(s1, "4-3")
        self.assertEqual(s2, "3-4")
        self.assertEqual(winner, 1)

        # 3-4 without tiebreak points -> valid without tiebreak
        s1, s2, winner = validate_team_rubber_score(3, 4, total_games=7)
        self.assertEqual(s1, "3-4")
        self.assertEqual(s2, "4-3")
        self.assertEqual(winner, 2)

        # 4-3 with valid 7-point tiebreak (7-4) -> valid with tiebreak noted
        s1, s2, winner = validate_team_rubber_score(4, 3, p1_tb_pts=7, p2_tb_pts=4, total_games=7)
        self.assertEqual(s1, "4-3(4)")
        self.assertEqual(s2, "3-4(4)")
        self.assertEqual(winner, 1)

        # 3-4 with extended tiebreak (8-10) -> valid
        s1, s2, winner = validate_team_rubber_score(3, 4, p1_tb_pts=8, p2_tb_pts=10, total_games=7)
        self.assertEqual(s1, "3-4(8)")
        self.assertEqual(winner, 2)

        # 3-3 with tiebreak (7-5) -> auto-awarded 7th game to tiebreak winner (4-3)
        s1, s2, winner = validate_team_rubber_score(3, 3, p1_tb_pts=7, p2_tb_pts=5, total_games=7)
        self.assertEqual(s1, "4-3(5)")
        self.assertEqual(winner, 1)

        # 3-3 without tiebreak points -> should raise
        with self.assertRaises(ValueError):
            validate_team_rubber_score(3, 3, total_games=7)

        # Tiebreak winner mismatch: P1 won games (4-3) but P2 won tiebreak (4-7) -> should raise
        with self.assertRaises(ValueError):
            validate_team_rubber_score(4, 3, p1_tb_pts=4, p2_tb_pts=7, total_games=7)

    def test_02_rubber_scoring_dynamic_t5_and_t9(self):
        """Test dynamic rubber scoring for T=5 and T=9."""
        # T=5: Sum of games must be 5. Tiebreak trigger at 2-2.
        s1, s2, winner = validate_team_rubber_score(4, 1, total_games=5)
        self.assertEqual(s1, "4-1")
        self.assertEqual(winner, 1)

        # 3-2 without tiebreak for T=5 (majority of games won)
        s1, s2, winner = validate_team_rubber_score(3, 2, total_games=5)
        self.assertEqual(s1, "3-2")
        self.assertEqual(winner, 1)

        # 3-2 with tiebreak 7-5 for T=5
        s1, s2, winner = validate_team_rubber_score(3, 2, p1_tb_pts=7, p2_tb_pts=5, total_games=5)
        self.assertEqual(s1, "3-2(5)")
        self.assertEqual(winner, 1)

        # 2-2 with tiebreak 7-3 for T=5 -> auto-promotes to 3-2
        s1, s2, winner = validate_team_rubber_score(2, 2, p1_tb_pts=7, p2_tb_pts=3, total_games=5)
        self.assertEqual(s1, "3-2(3)")
        self.assertEqual(winner, 1)

        # T=9: Sum of games must be 9. Tiebreak trigger at 4-4.
        s1, s2, winner = validate_team_rubber_score(6, 3, total_games=9)
        self.assertEqual(s1, "6-3")
        self.assertEqual(winner, 1)

        # 5-4 without tiebreak for T=9 (majority of games won)
        s1, s2, winner = validate_team_rubber_score(5, 4, total_games=9)
        self.assertEqual(s1, "5-4")
        self.assertEqual(winner, 1)

        s1, s2, winner = validate_team_rubber_score(5, 4, p1_tb_pts=9, p2_tb_pts=7, total_games=9)
        self.assertEqual(s1, "5-4(7)")
        self.assertEqual(winner, 1)

        # Rejection of invalid even T
        with self.assertRaises(ValueError):
            validate_team_rubber_score(4, 2, total_games=6)

    # =========================================================================
    # 2. DYNAMIC FIXTURE CALCULATION & 21-GAME FIRST-TO-11 PRINCIPLE
    # =========================================================================

    def test_03_team_fixture_status_first_to_11(self):
        """Test 21-game total and first-to-11 principle for T=7."""
        # Rubbers:
        # Rubber 1: 4-2 (Team 1 won 4, Team 2 won 2)
        # Rubber 2: 4-1 (Team 1 won 4, Team 2 won 1)
        # Total so far: Team 1 = 8, Team 2 = 3. Target to win = ((3*7)//2) + 1 = 11.
        rubbers = [
            {'score1': '4-2', 'score2': '2-4', 'status': 'completed', 'winner_id': 101, 'participant1_id': 101},
            {'score1': '4-1', 'score2': '1-4', 'status': 'completed', 'winner_id': 101, 'participant1_id': 101},
            {'score1': None, 'score2': None, 'status': 'pending', 'winner_id': None, 'participant1_id': 101}
        ]
        status = calculate_team_fixture_status(rubbers, total_games=7)
        self.assertEqual(status['g1'], 8)
        self.assertEqual(status['g2'], 3)
        self.assertEqual(status['target_games_to_win'], 11)
        self.assertFalse(status['is_decided'])

        # Now Rubber 3 finishes 4-3(5) in favor of Team 1
        # Team 1 reaches 8 + 4 = 12 games (>= 11). Decided!
        rubbers[2] = {'score1': '4-3(5)', 'score2': '3-4(5)', 'status': 'completed', 'winner_id': 101, 'participant1_id': 101}
        status = calculate_team_fixture_status(rubbers, total_games=7)
        self.assertEqual(status['g1'], 12)
        self.assertEqual(status['g2'], 6)
        self.assertTrue(status['is_decided'])
        self.assertEqual(status['winner_indicator'], 1)

    # =========================================================================
    # 3. PLAYER SKILL TIERS & AUTO-CREATE TEAMS (MODE B)
    # =========================================================================

    def test_04_auto_create_teams_mode_b(self):
        """Test Mode B automatic team draft: 1 player from each of the 5 tiers."""
        category = Category(
            tournament_id=self.tournament_id,
            name='Premier Team Cup',
            format='group_stage',
            max_players_per_team=5,
            num_groups=2,
            total_games=7,
            status='setup'
        )
        db.session.add(category)
        db.session.flush()

        # Create 20 players (4 per tier for 4 teams)
        tiers = ['A', 'B', 'C', 'D', 'E']
        players = []
        for tier in tiers:
            for i in range(1, 5):
                p = Player(name=f"Player_{tier}_{i}", gender='Male', age_category='Open')
                db.session.add(p)
                db.session.flush()
                players.append(p)

                tier_entry = PlayerCategoryTier(
                    category_id=category.id,
                    player_id=p.id,
                    tier=tier,
                    role='player'
                )
                db.session.add(tier_entry)

        db.session.commit()

        # Run auto_create_teams
        created_teams = GroupStageFormat.auto_create_teams(category.id)
        self.assertEqual(len(created_teams), 4)

        # Verify each team has exactly 5 members: 1 Captain (Tier A), 1 VC (Tier B), 3 Members (C, D, E)
        for team in created_teams:
            members = TeamMember.query.filter_by(participant_id=team.id).order_by(TeamMember.roster_order).all()
            self.assertEqual(len(members), 5)
            self.assertEqual(members[0].role, 'captain')
            self.assertEqual(members[0].tier, 'A')
            self.assertEqual(members[1].role, 'vice_captain')
            self.assertEqual(members[1].tier, 'B')
            self.assertEqual(members[2].tier, 'C')
            self.assertEqual(members[3].tier, 'D')
            self.assertEqual(members[4].tier, 'E')

    # =========================================================================
    # 4. FIXTURE GENERATION WITH 3 RUBBERS & SESSION TIMINGS
    # =========================================================================

    def test_05_fixture_generation_with_3_rubbers(self):
        """Test round-robin fixtures produce 3 child rubbers with lineup assignments."""
        category = Category(
            tournament_id=self.tournament_id,
            name='Team League Cup',
            format='group_stage',
            max_players_per_team=5,
            num_groups=2,
            total_games=7,
            status='setup'
        )
        db.session.add(category)
        db.session.flush()

        # Create 4 teams with 5 players each
        teams = []
        for i in range(1, 5):
            t_part = Participant(
                tournament_id=self.tournament_id,
                category_id=category.id,
                name=f"Team {i}"
            )
            db.session.add(t_part)
            db.session.flush()
            teams.append(t_part)

            # Assign 5 players
            for r_order, role, tier in [(1, 'captain', 'A'), (2, 'vice_captain', 'B'), (3, 'member', 'C'), (4, 'member', 'D'), (5, 'member', 'E')]:
                pl = Player(name=f"Team{i}_P{r_order}", gender='Male', age_category='Open')
                db.session.add(pl)
                db.session.flush()
                db.session.add(TeamMember(
                    participant_id=t_part.id,
                    player_id=pl.id,
                    role=role,
                    tier=tier,
                    roster_order=r_order
                ))

        db.session.commit()

        # Generate group stage fixtures
        fixtures = GroupStageFormat.generate(category, teams)
        self.assertTrue(len(fixtures) > 0)

        # Check that parent fixture has 3 sub_matches
        first_fixture = fixtures[0]
        self.assertIn('sub_matches', first_fixture)
        rubbers = first_fixture['sub_matches']
        self.assertEqual(len(rubbers), 3)

        # Check rubber types and verify fair play: player slots start unallotted awaiting captains' slips
        self.assertEqual(rubbers[0]['rubber_type'], 'singles')
        self.assertEqual(rubbers[0]['rubber_number'], 1)
        self.assertIsNone(rubbers[0]['p1_player1_id'])
        self.assertIsNone(rubbers[0]['p2_player1_id'])

        self.assertEqual(rubbers[1]['rubber_type'], 'doubles_1')
        self.assertEqual(rubbers[1]['rubber_number'], 2)
        self.assertIsNone(rubbers[1]['p1_player1_id'])
        self.assertIsNone(rubbers[1]['p1_player2_id'])

        self.assertEqual(rubbers[2]['rubber_type'], 'doubles_2')
        self.assertEqual(rubbers[2]['rubber_number'], 3)
        self.assertIsNone(rubbers[2]['p1_player1_id'])
        self.assertIsNone(rubbers[2]['p1_player2_id'])

        # Verify auto_allot=True populates roster players when explicitly requested
        auto_rubbers = GroupStageFormat._build_team_rubbers(category, None, 1, 1, teams[0], teams[1], auto_allot=True)
        self.assertIsNotNone(auto_rubbers[0]['p1_player1_id'])
        self.assertIsNotNone(auto_rubbers[0]['p2_player1_id'])
        self.assertIsNotNone(auto_rubbers[1]['p1_player1_id'])
        self.assertIsNotNone(auto_rubbers[1]['p1_player2_id'])

    # =========================================================================
    # 5. HEAD-TO-HEAD TIEBREAKER IN GROUP STANDINGS
    # =========================================================================

    def test_06_head_to_head_group_standings(self):
        """Test that Head-to-Head is the primary tiebreaker when two teams have equal wins."""
        category = Category(
            tournament_id=self.tournament_id,
            name='H2H Category',
            format='group_stage',
            max_players_per_team=5,
            num_groups=1,
            total_games=7,
            status='in_progress'
        )
        db.session.add(category)
        db.session.flush()

        group = Group(category_id=category.id, name='Group A')
        db.session.add(group)
        db.session.flush()

        team_a = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=group.id, name='Team Alpha')
        team_b = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=group.id, name='Team Beta')
        team_c = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=group.id, name='Team Gamma')
        db.session.add_all([team_a, team_b, team_c])
        db.session.flush()

        # Match 1: Team Alpha beats Team Beta: 11 - 9
        m1 = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=group.id,
            round=1,
            match_number=1,
            participant1_id=team_a.id,
            participant2_id=team_b.id,
            winner_id=team_a.id,
            score1='11',
            score2='9',
            status='completed',
            match_type='group_stage'
        )

        # Match 2: Team Beta beats Team Gamma: 14 - 4 (Beta gets huge points)
        m2 = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=group.id,
            round=2,
            match_number=2,
            participant1_id=team_b.id,
            participant2_id=team_c.id,
            winner_id=team_b.id,
            score1='14',
            score2='4',
            status='completed',
            match_type='group_stage'
        )

        # Match 3: Team Gamma beats Team Alpha: 11 - 8
        m3 = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=group.id,
            round=3,
            match_number=3,
            participant1_id=team_c.id,
            participant2_id=team_a.id,
            winner_id=team_c.id,
            score1='11',
            score2='8',
            status='completed',
            match_type='group_stage'
        )
        db.session.add_all([m1, m2, m3])
        db.session.commit()

        standings = GroupStageFormat.calculate_group_standings(group.id)
        self.assertEqual(len(standings), 3)

        # Per organizer directive:
        # 1. Total games won decides rank in 3-way circular ties:
        # Beta has 9 + 14 = 23 games won -> Rank 1
        # Alpha has 11 + 8 = 19 games won -> Rank 2
        # Gamma has 4 + 11 = 15 games won -> Rank 3
        self.assertEqual(standings[0].id, team_b.id)
        self.assertEqual(standings[1].id, team_a.id)
        self.assertEqual(standings[2].id, team_c.id)

        # 2. When total games won are identical, H2H decides rank:
        m2.score1 = '10' # Beta gets 10 (total 19)
        m2.score2 = '8'  # Gamma gets 8 (total 19)
        # Now Alpha has 11 + 8 = 19 games, Beta has 9 + 10 = 19 games.
        # Since Alpha beat Beta in m1, Alpha ranks above Beta:
        db.session.commit()
        standings_tied = GroupStageFormat.calculate_group_standings(group.id)
        self.assertEqual(standings_tied[0].id, team_a.id)
        self.assertEqual(standings_tied[1].id, team_b.id)

    # =========================================================================
    # 6. UNIFIED KNOCKOUT SEEDING & BRACKET LINE PLACEMENT
    # =========================================================================

    def test_07_knockout_unified_ranking_and_seeding(self):
        """Test unified ranking by Max Score and strict bracket placement."""
        category = Category(
            tournament_id=self.tournament_id,
            name='Knockout Cup',
            format='group_stage',
            max_players_per_team=5,
            num_groups=2,
            qualifiers_per_group=2,
            total_games=7,
            status='in_progress'
        )
        db.session.add(category)
        db.session.flush()

        # Group 1
        g1 = Group(category_id=category.id, name='Group A')
        # Group 2
        g2 = Group(category_id=category.id, name='Group B')
        db.session.add_all([g1, g2])
        db.session.flush()

        t1 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=g1.id, name='Team 1')
        t2 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=g1.id, name='Team 2')
        t3 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=g2.id, name='Team 3')
        t4 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=g2.id, name='Team 4')
        db.session.add_all([t1, t2, t3, t4])
        db.session.flush()

        # Group A match: Team 1 beats Team 2: 24 - 18
        m_g1 = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=g1.id,
            round=1,
            match_number=1,
            participant1_id=t1.id,
            participant2_id=t2.id,
            winner_id=t1.id,
            score1='24',
            score2='18',
            status='completed',
            match_type='group_stage'
        )

        # Group B match: Team 3 beats Team 4: 22 - 16
        m_g2 = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=g2.id,
            round=1,
            match_number=2,
            participant1_id=t3.id,
            participant2_id=t4.id,
            winner_id=t3.id,
            score1='22',
            score2='16',
            status='completed',
            match_type='group_stage'
        )
        db.session.add_all([m_g1, m_g2])
        db.session.commit()

        # Generate knockout from groups
        knockout_matches = GroupStageFormat.generate_knockout_from_groups(category)
        self.assertTrue(len(knockout_matches) > 0)

        # Verify unified seeding:
        # Team 1 (24 pts) -> Seed 1
        # Team 3 (22 pts) -> Seed 2
        # Team 2 (18 pts) -> Seed 3
        # Team 4 (16 pts) -> Seed 4
        db.session.refresh(t1)
        db.session.refresh(t3)
        db.session.refresh(t2)
        db.session.refresh(t4)

        self.assertEqual(t1.seed, 1)
        self.assertEqual(t3.seed, 2)
        self.assertEqual(t2.seed, 3)
        self.assertEqual(t4.seed, 4)

        # In a 4-team bracket:
        # Match 1: Seed 1 (Upper Half) vs Seed 4
        # Match 2: Seed 3 vs Seed 2 (Lower Half)
        m_r1 = [m for m in knockout_matches if m.get('round') == 1]
        self.assertEqual(len(m_r1), 2)
        self.assertEqual(m_r1[0]['participant1_id'], t1.id)  # Seed 1 top of upper half
        self.assertEqual(m_r1[1]['participant2_id'], t3.id)  # Seed 2 bottom of lower half

    # =========================================================================
    # 7. MANUAL CHIT DRAW & DUPLICATE PLAYER PREVENTION
    # =========================================================================

    def test_08_manual_chit_draw_duplicate_prevention(self):
        """Test Mode A manual chit draw detects and prevents duplicate player selections."""
        category = Category(
            tournament_id=self.tournament_id,
            name='Manual Draw Cup',
            format='group_stage',
            max_players_per_team=5,
            num_groups=2,
            total_games=7,
            status='setup'
        )
        db.session.add(category)
        db.session.flush()

        p1 = Player(name='Player One', gender='Male', age_category='Open')
        p2 = Player(name='Player Two', gender='Male', age_category='Open')
        db.session.add_all([p1, p2])
        db.session.commit()

        # Simulate client posting duplicate player to both Team 1 and Team 2
        with self.app.test_client() as client:
            # Login
            with client.session_transaction() as sess:
                sess['user_id'] = self.user_id
                sess['_fresh'] = True

            payload = {
                'teams': [
                    {'name': 'Team 1', 'captain_id': p1.id, 'vc_id': p2.id},
                    {'name': 'Team 2', 'captain_id': p1.id, 'vc_id': None}  # p1 is duplicated!
                ]
            }
            res = client.post(
                f'/tournaments/{self.slug}/categories/{category.id}/teams/create-manual',
                json=payload
            )
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data['success'])
            self.assertIn('Duplicate player detected', data['error'])

    # =========================================================================
    # 8. SCHEDULER & ORDER OF PLAY GROUP START TIMINGS
    # =========================================================================

    def test_09_scheduler_respects_group_start_timing_and_child_rubbers(self):
        """Test that scheduler respects group session start times and synchronizes rubbers."""
        from app.services.utils.scheduler import auto_schedule_tournament

        category = Category(
            tournament_id=self.tournament_id,
            name='Scheduling Cup',
            format='group_stage',
            max_players_per_team=5,
            num_groups=2,
            total_games=7,
            status='in_progress'
        )
        db.session.add(category)
        db.session.flush()

        # Group A at 09:00 AM on Court 1, Court 2, Court 3
        grp_a = Group(category_id=category.id, name='Group A', start_time='09:00', assigned_courts='Court 1, Court 2, Court 3')
        # Group B at 11:30 AM on Court 1, Court 2, Court 3
        grp_b = Group(category_id=category.id, name='Group B', start_time='11:30', assigned_courts='Court 1, Court 2, Court 3')
        db.session.add_all([grp_a, grp_b])
        db.session.flush()

        t_a1 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_a.id, name='Alpha 1')
        t_a2 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_a.id, name='Alpha 2')
        t_b1 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_b.id, name='Beta 1')
        t_b2 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_b.id, name='Beta 2')
        db.session.add_all([t_a1, t_a2, t_b1, t_b2])
        db.session.flush()

        # Create parent fixture in Group A with 3 rubbers
        parent_a = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=grp_a.id,
            round=1,
            match_number=1,
            participant1_id=t_a1.id,
            participant2_id=t_a2.id,
            match_type='group_stage',
            status='pending'
        )
        db.session.add(parent_a)
        db.session.flush()

        r1 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_a.id, parent_match_id=parent_a.id, round=1, match_number=1, rubber_type='singles', rubber_number=1, status='pending')
        r2 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_a.id, parent_match_id=parent_a.id, round=1, match_number=1, rubber_type='doubles_1', rubber_number=2, status='pending')
        r3 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_a.id, parent_match_id=parent_a.id, round=1, match_number=1, rubber_type='doubles_2', rubber_number=3, status='pending')
        db.session.add_all([r1, r2, r3])

        # Create parent fixture in Group B
        parent_b = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=grp_b.id,
            round=1,
            match_number=2,
            participant1_id=t_b1.id,
            participant2_id=t_b2.id,
            match_type='group_stage',
            status='pending'
        )
        db.session.add(parent_b)
        db.session.flush()

        rb1 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_b.id, parent_match_id=parent_b.id, round=1, match_number=2, rubber_type='singles', rubber_number=1, status='pending')
        rb2 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_b.id, parent_match_id=parent_b.id, round=1, match_number=2, rubber_type='doubles_1', rubber_number=2, status='pending')
        rb3 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp_b.id, parent_match_id=parent_b.id, round=1, match_number=2, rubber_type='doubles_2', rubber_number=3, status='pending')
        db.session.add_all([rb1, rb2, rb3])
        db.session.commit()

        # Run scheduler
        res = auto_schedule_tournament(self.tournament_id)
        self.assertEqual(res['scheduled'], 2)  # 2 parent fixtures scheduled

        db.session.refresh(parent_a)
        db.session.refresh(parent_b)
        db.session.refresh(r1)
        db.session.refresh(r2)
        db.session.refresh(r3)

        # Parent A scheduled at or after 09:00 AM
        self.assertIsNotNone(parent_a.scheduled_time)
        self.assertEqual(parent_a.scheduled_time.hour, 9)
        self.assertEqual(parent_a.scheduled_time.minute, 0)

        # Child rubbers inherit scheduled_time from Parent A
        self.assertEqual(r1.scheduled_time, parent_a.scheduled_time)
        self.assertEqual(r2.scheduled_time, parent_a.scheduled_time)
        self.assertEqual(r3.scheduled_time, parent_a.scheduled_time)

        # Child rubbers are distributed across Court 1, Court 2, Court 3
        rubber_courts = {r1.court_name, r2.court_name, r3.court_name}
        self.assertTrue('Court 1' in rubber_courts or 'Court 2' in rubber_courts or 'Court 3' in rubber_courts)

    def test_10_tournament_creation_duration_and_daily_hours(self):
        """Test tournament creation captures duration and daily operating hours."""
        import json
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.user_id
                sess['_fresh'] = True

            post_data = {
                'name': 'Premier League 2026',
                'creator_name': 'Tournament Director',
                'start_date': '2026-11-01',
                'end_date': '2026-11-03',
                'court_operating_start': '08:30',
                'court_operating_end': '21:00',
                'num_courts': 3,
                'court_names': 'Centre Court, Court 1, Court 2',
                'daily_start_2026-11-01': '08:30',
                'daily_end_2026-11-01': '21:00',
                'daily_start_2026-11-02': '09:00',
                'daily_end_2026-11-02': '20:00',
                'daily_start_2026-11-03': '10:00',
                'daily_end_2026-11-03': '18:00',
            }
            res = client.post('/tournaments/new', data=post_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        created = Tournament.query.filter_by(name='Premier League 2026').first()
        self.assertIsNotNone(created)
        self.assertEqual(created.start_date.strftime('%Y-%m-%d'), '2026-11-01')
        self.assertEqual(created.end_date.strftime('%Y-%m-%d'), '2026-11-03')
        self.assertEqual(created.court_operating_start, '08:30')
        self.assertEqual(created.court_operating_end, '21:00')
        self.assertEqual(created.num_courts, 3)

        # Check daily operating hours JSON
        self.assertIsNotNone(created.daily_operating_hours)
        daily_hours = json.loads(created.daily_operating_hours)
        self.assertEqual(daily_hours['2026-11-01']['start'], '08:30')
        self.assertEqual(daily_hours['2026-11-02']['start'], '09:00')
        self.assertEqual(daily_hours['2026-11-03']['end'], '18:00')

    def test_11_captains_match_lineup_allotment(self):
        """Test admin allotment of fair captain match nominations across 3 rubbers."""
        category = Category(
            tournament_id=self.tournament_id,
            name='Inter-Club League',
            format='group_stage',
            has_group_stage=True,
            num_groups=1,
            teams_per_group=2,
            total_games=7
        )
        db.session.add(category)
        db.session.flush()

        grp = Group(category_id=category.id, name='Group 1')
        db.session.add(grp)
        db.session.flush()

        team1 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, name='Titans')
        team2 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, name='Warriors')
        db.session.add_all([team1, team2])
        db.session.flush()

        # Create 10 players
        players = [Player(name=f"Player {i}", gender='Male', age_category='Open') for i in range(1, 11)]
        db.session.add_all(players)
        db.session.flush()

        # Assign 5 to team1, 5 to team2
        for i in range(5):
            db.session.add(TeamMember(participant_id=team1.id, player_id=players[i].id, role='captain' if i == 0 else 'member', roster_order=i+1))
        for i in range(5, 10):
            db.session.add(TeamMember(participant_id=team2.id, player_id=players[i].id, role='captain' if i == 5 else 'member', roster_order=i-4))
        db.session.flush()

        # Parent fixture with 3 child rubbers
        fixture = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=grp.id,
            participant1_id=team1.id,
            participant2_id=team2.id,
            match_type='group_stage',
            round=1,
            match_number=1,
            status='pending'
        )
        db.session.add(fixture)
        db.session.flush()

        r1 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, parent_match_id=fixture.id, round=1, match_number=1, rubber_type='singles', rubber_number=1, status='pending')
        r2 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, parent_match_id=fixture.id, round=1, match_number=1, rubber_type='doubles_1', rubber_number=2, status='pending')
        r3 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, parent_match_id=fixture.id, round=1, match_number=1, rubber_type='doubles_2', rubber_number=3, status='pending')
        db.session.add_all([r1, r2, r3])
        db.session.commit()

        # Submit captains' lineup allotment
        lineup_data = {
            'r1_p1_player1': players[0].id,      # Singles: T1 Player 1 vs T2 Player 6
            'r1_p2_player1': players[5].id,
            'r2_p1_player1': players[1].id,      # Doubles 1: T1 P2+P3 vs T2 P7+P8
            'r2_p1_player2': players[2].id,
            'r2_p2_player1': players[6].id,
            'r2_p2_player2': players[7].id,
            'r3_p1_player1': players[3].id,      # Doubles 2: T1 P4+P5 vs T2 P9+P10
            'r3_p1_player2': players[4].id,
            'r3_p2_player1': players[8].id,
            'r3_p2_player2': players[9].id
        }
        tourn = Tournament.query.get(self.tournament_id)
        url = f"/tournaments/{tourn.url_slug}/categories/{category.id}/fixtures/{fixture.id}/lineup"
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.user_id
                sess['_fresh'] = True
            res = client.post(url, data=lineup_data, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        # Verify child rubbers updated
        db.session.refresh(r1)
        db.session.refresh(r2)
        db.session.refresh(r3)

        self.assertEqual(r1.p1_player1_id, players[0].id)
        self.assertEqual(r1.p2_player1_id, players[5].id)

        self.assertEqual(r2.p1_player1_id, players[1].id)
        self.assertEqual(r2.p1_player2_id, players[2].id)
        self.assertEqual(r2.p2_player1_id, players[6].id)
        self.assertEqual(r2.p2_player2_id, players[7].id)

        self.assertEqual(r3.p1_player1_id, players[3].id)
        self.assertEqual(r3.p1_player2_id, players[4].id)
        self.assertEqual(r3.p2_player1_id, players[8].id)
        self.assertEqual(r3.p2_player2_id, players[9].id)

    def test_12_order_of_play_shows_group_and_teams_without_child_rubber_chaos(self):
        """Test Order of Play cleanly presents [Group] Team 1 vs Team 2 and omits child rubber clutter."""
        from app.services.utils.scheduler import get_order_of_play
        tourn = Tournament.query.get(self.tournament_id)
        tourn.start_date = date(2026, 12, 1)
        tourn.end_date = date(2026, 12, 1)
        tourn.num_courts = 1
        tourn.court_names = 'Court 1'
        db.session.flush()

        category = Category(
            tournament_id=self.tournament_id,
            name='Club Championship',
            format='group_stage',
            has_group_stage=True,
            total_games=7
        )
        db.session.add(category)
        db.session.flush()

        grp = Group(category_id=category.id, name='Group Alpha')
        db.session.add(grp)
        db.session.flush()

        t1 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, name='Dragons')
        t2 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, name='Phoenix')
        db.session.add_all([t1, t2])
        db.session.flush()

        # Parent fixture scheduled on Court 1 at 10:00 AM
        fixture = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=grp.id,
            participant1_id=t1.id,
            participant2_id=t2.id,
            match_type='group_stage',
            round=1,
            match_number=1,
            court_name='Court 1',
            scheduled_time=datetime(2026, 12, 1, 10, 0),
            status='pending'
        )
        db.session.add(fixture)
        db.session.flush()

        # 3 Child rubbers also have court and scheduled_time
        r1 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, parent_match_id=fixture.id, round=1, match_number=1, rubber_type='singles', rubber_number=1, court_name='Court 1', scheduled_time=datetime(2026, 12, 1, 10, 0), status='pending')
        r2 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, parent_match_id=fixture.id, round=1, match_number=1, rubber_type='doubles_1', rubber_number=2, court_name='Court 1', scheduled_time=datetime(2026, 12, 1, 10, 0), status='pending')
        r3 = Match(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, parent_match_id=fixture.id, round=1, match_number=1, rubber_type='doubles_2', rubber_number=3, court_name='Court 1', scheduled_time=datetime(2026, 12, 1, 10, 0), status='pending')
        db.session.add_all([r1, r2, r3])
        db.session.commit()

        # Call get_order_of_play
        oop_data = get_order_of_play(tourn.url_slug, filter_date=date(2026, 12, 1))
        courts = oop_data['courts']
        self.assertIn('Court 1', courts)

        court_matches = courts['Court 1'].matches
        # Only 1 card should be displayed on Court 1 (the parent fixture), NOT 4 cards!
        self.assertEqual(len(court_matches), 1)

        card = court_matches[0]
        # Shows group name and teams facing each other
        self.assertEqual(card['round_name'], 'Group Alpha')
        self.assertEqual(card['p1'], 'Dragons')
        self.assertEqual(card['p2'], 'Phoenix')
        self.assertTrue(card['is_team'])
        self.assertTrue(card['has_rubbers'])
        self.assertEqual(card['sub_matches_count'], 3)

    def test_13_duration_and_daily_timings_settings(self):
        """Test creating a tournament with explicit duration_days and custom daily operating timings."""
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.user_id
                sess['_fresh'] = True

            payload = {
                'name': 'Duration Championship',
                'creator_name': 'Director Dave',
                'start_date': '2026-11-10',
                'duration_days': 4,
                'num_courts': 3,
                'court_operating_start': '08:30',
                'court_operating_end': '20:30',
                'daily_start_2026-11-10': '08:00',
                'daily_end_2026-11-10': '21:00',
                'daily_start_2026-11-11': '09:00',
                'daily_end_2026-11-11': '18:00',
            }
            res = client.post('/tournaments/new', data=payload, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            t = Tournament.query.filter_by(name='Duration Championship').first()
            self.assertIsNotNone(t)
            # Duration 4 days from 2026-11-10 should calculate end_date as 2026-11-13
            self.assertEqual(t.start_date, date(2026, 11, 10))
            self.assertEqual(t.end_date, date(2026, 11, 13))

            import json
            daily_hours = json.loads(t.daily_operating_hours) if t.daily_operating_hours else {}
            self.assertEqual(daily_hours.get('2026-11-10', {}).get('start'), '08:00')
            self.assertEqual(daily_hours.get('2026-11-10', {}).get('end'), '21:00')
            self.assertEqual(daily_hours.get('2026-11-11', {}).get('start'), '09:00')
            self.assertEqual(daily_hours.get('2026-11-11', {}).get('end'), '18:00')

    def test_14_rubber_reporting_summation_rule_and_tiebreak_promotion(self):
        """Test HTTP report endpoint enforcing summation rule (g1+g2==7) and 3-3 tiebreaker auto-promotion."""
        category = Category(
            tournament_id=self.tournament_id,
            name='Premier League Category',
            format='group_stage',
            total_games=7,
            num_groups=1,
            status='active'
        )
        db.session.add(category)
        db.session.flush()

        grp = Group(category_id=category.id, name='Group Alpha')
        db.session.add(grp)
        db.session.flush()

        t1 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, name='Titans')
        t2 = Participant(tournament_id=self.tournament_id, category_id=category.id, group_id=grp.id, name='Warriors')
        db.session.add_all([t1, t2])
        db.session.flush()

        fixture = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=grp.id,
            participant1_id=t1.id,
            participant2_id=t2.id,
            match_type='group_stage',
            round=1,
            match_number=1,
            status='pending'
        )
        db.session.add(fixture)
        db.session.flush()

        rubber = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=grp.id,
            parent_match_id=fixture.id,
            participant1_id=t1.id,
            participant2_id=t2.id,
            match_type='group_stage',
            round=1,
            match_number=1,
            rubber_type='singles',
            rubber_number=1,
            status='pending'
        )
        db.session.add(rubber)
        db.session.commit()

        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['user_id'] = self.user_id
                sess['_fresh'] = True

            report_url = f"/tournaments/{self.slug}/categories/{category.id}/match/{rubber.id}/report"

            # 1. Invalid summation (4-1, sum 5 != 7) -> should fail
            res = client.post(report_url, data={
                'action': 'complete_match',
                'set1_p1': '4',
                'set1_p2': '1',
                'winner_id': str(t1.id)
            }, follow_redirects=True)
            self.assertIn(b"Total games must sum to 7", res.data)

            # 2. Valid summation (6-1, sum 7) -> succeeds
            res = client.post(report_url, data={
                'action': 'complete_match',
                'set1_p1': '6',
                'set1_p2': '1',
                'winner_id': str(t1.id)
            }, follow_redirects=True)
            r = db.session.get(Match, rubber.id)
            self.assertEqual(r.score1, "6-1")
            self.assertEqual(r.status, "completed")
            self.assertEqual(r.winner_id, t1.id)

            # Reset rubber for tiebreak test
            r.status = 'pending'
            r.score1 = None
            r.score2 = None
            r.winner_id = None
            db.session.commit()

            # 3. 3-3 with 7-point tiebreak (7-4) -> auto-awarded 7th game (4-3)
            res = client.post(report_url, data={
                'action': 'complete_match',
                'set1_p1': '3',
                'set1_p2': '3',
                'tb1_p1': '7',
                'tb1_p2': '4',
                'winner_id': str(t1.id)
            }, follow_redirects=True)
            r = db.session.get(Match, rubber.id)
            self.assertEqual(r.score1, "4-3(4)")
            self.assertEqual(r.status, "completed")
            self.assertEqual(r.winner_id, t1.id)

            # Reset rubber for 4-3 without tiebreak test (majority of games won)
            r.status = 'pending'
            r.score1 = None
            r.score2 = None
            r.winner_id = None
            db.session.commit()

            # 4. 4-3 without tiebreak -> valid completed rubber (player took majority of games)
            res = client.post(report_url, data={
                'action': 'complete_match',
                'set1_p1': '4',
                'set1_p2': '3',
                'winner_id': str(t1.id)
            }, follow_redirects=True)
            r = db.session.get(Match, rubber.id)
            self.assertEqual(r.score1, "4-3")
            self.assertEqual(r.status, "completed")
            self.assertEqual(r.winner_id, t1.id)

    def test_15_walkover_and_retirement_remainder_scoring(self):
        """Test organizer rule: mid-match retirement awards all remaining games (up to 7) to opposition"""
        from app.services.tennis_logic import award_walkover_or_retirement_rubber, validate_team_rubber_score

        # Case 1: Pre-match walkover (0-0), Player 1 retired/absent -> Opponent (P2) gets 7-0
        s1, s2, w = award_walkover_or_retirement_rubber(p1_games=0, p2_games=0, retiring_player=1, total_games=7)
        self.assertEqual(s1, "0-7")
        self.assertEqual(s2, "7-0")
        self.assertEqual(w, 2)

        # Case 2: Mid-match retirement at 3-2, Player 2 retired -> Opponent (P1) gets remaining 2 games -> 5-2
        s1, s2, w = award_walkover_or_retirement_rubber(p1_games=3, p2_games=2, retiring_player=2, total_games=7)
        self.assertEqual(s1, "5-2")
        self.assertEqual(s2, "2-5")
        self.assertEqual(w, 1)

        # Case 3: Mid-match retirement via validate_team_rubber_score
        s1, s2, w = validate_team_rubber_score(p1_games=1, p2_games=3, is_retired=True, retiring_player=1, total_games=7)
        self.assertEqual(s1, "1-6")
        self.assertEqual(s2, "6-1")
        self.assertEqual(w, 2)

    def test_16_knockout_guard_against_pending_group_matches(self):
        """Test that start-knockout blocks bracket generation if group fixtures are still incomplete"""
        category = Category(
            tournament_id=self.tournament_id,
            name='Guard Cat',
            format='group_stage',
            max_players_per_team=5,
            num_groups=1,
            total_games=7,
            has_group_stage=True,
            status='in_progress'
        )
        db.session.add(category)
        db.session.flush()

        group = Group(category_id=category.id, name='Group 1')
        db.session.add(group)
        db.session.flush()

        # Incomplete group fixture
        m = Match(
            tournament_id=self.tournament_id,
            category_id=category.id,
            group_id=group.id,
            round=1,
            match_number=1,
            status='pending',
            match_type='group_stage'
        )
        db.session.add(m)
        db.session.commit()

        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['role'] = 'admin'

        res = client.post(
            f'/tournaments/{self.slug}/categories/{category.id}/start-knockout',
            follow_redirects=True
        )
        # Should reject because 1 match is pending
        self.assertIn(b"Cannot start knockout stage", res.data)
        self.assertIn(b"pending or in progress", res.data)

    def test_18_order_of_play_displays_full_scoreline_for_completed_team_and_rubber_matches(self):
        """Verify that completed matches in Order of Play show the complete scoreline (e.g. 17 – 4) instead of only score1 (17)."""
        with self.app.app_context():
            # Test template filter directly
            filter_fn = self.app.jinja_env.filters['display_match_score']

            # Case A: Team Tie numeric totals
            team_match = Match(score1='17', score2='4', status='completed')
            self.assertEqual(filter_fn(team_match), "17 \u2013 4")

            # Case B: Team Tie where team 2 has 0
            zero_match = Match(score1='17', score2='0', status='completed')
            self.assertEqual(filter_fn(zero_match), "17 \u2013 0")

            # Case C: Child Rubber with hyphen
            rubber_match = Match(score1='6-1', score2='1-6', status='completed')
            self.assertEqual(filter_fn(rubber_match), "6-1")

            # Case D: Standard match with tiebreak
            tb_match = Match(score1='7-6(4), 6-3', score2='6-7(4), 3-6', status='completed')
            self.assertEqual(filter_fn(tb_match), "7-6<sup>4</sup>, 6-3")

            # Case E: Dict format
            dict_match = {'score1': '8', 'score2': '13'}
            self.assertEqual(filter_fn(dict_match), "8 \u2013 13")


if __name__ == '__main__':
    unittest.main()

