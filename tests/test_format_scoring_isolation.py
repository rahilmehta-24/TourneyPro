import os
import tempfile
import unittest
from datetime import date

from app import create_app
from app.domain.models import Category, Group, Match, Participant, Tournament, User, db


class FormatScoringIsolationTestCase(unittest.TestCase):
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
        with self.app.app_context():
            db.session.remove()
            Match.query.delete()
            Participant.query.delete()
            Group.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            User.query.delete()
            db.session.commit()

            user = User(username='organizer_iso', email='iso@test.com', role='admin')
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()

            tournament = Tournament(
                name='Isolation Open 2026',
                url_slug='isolation-open-2026',
                user_id=user.id,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 2),
                num_courts=2,
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

    def _login(self, client):
        with client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['_fresh'] = True

    def test_01_create_single_elimination_ignores_group_stage_fields(self):
        """Creating Single Elimination must not inherit total_games or max_players_per_team."""
        with self.app.test_client() as client:
            self._login(client)
            res = client.post(
                f'/t/{self.slug}/categories/new',
                data={
                    'name': 'Mens Singles Knockout',
                    'format': 'single_elimination',
                    'sub_format': 'singles',
                    'scoring_format': 'games',
                    'num_sets': '3',
                    'games_per_set': '6',
                    # Simulate hidden inputs still present in form submission
                    'total_games': '7',
                    'points_to_win': '11',
                    'max_players_per_team': '5',
                },
                follow_redirects=False,
            )
            self.assertEqual(res.status_code, 302)

            cat = Category.query.filter_by(name='Mens Singles Knockout').first()
            self.assertIsNotNone(cat)
            self.assertEqual(cat.format, 'single_elimination')
            self.assertEqual(cat.scoring_format, 'games')
            self.assertEqual(cat.num_sets, 3)
            self.assertEqual(cat.games_per_set, 6)
            self.assertIsNone(cat.total_games)
            self.assertIsNone(cat.max_players_per_team)
            self.assertFalse(cat.has_group_stage)

    def test_02_create_single_elimination_points_and_group_stage_isolated(self):
        """Single Elimination (Points) and Group Stage keep distinct scoring settings."""
        with self.app.test_client() as client:
            self._login(client)

            # Single elimination with points (e.g. Badminton 21-pt)
            client.post(
                f'/t/{self.slug}/categories/new',
                data={
                    'name': 'Badminton Singles',
                    'format': 'single_elimination',
                    'sub_format': 'singles',
                    'scoring_format': 'points',
                    'points_to_win': '21',
                    'num_sets': '3',
                    'games_per_set': '6',
                    'total_games': '7',
                    'max_players_per_team': '5',
                },
            )
            se_pts = Category.query.filter_by(name='Badminton Singles').first()
            self.assertEqual(se_pts.format, 'single_elimination')
            self.assertEqual(se_pts.scoring_format, 'points')
            self.assertEqual(se_pts.points_to_win, 21)
            self.assertIsNone(se_pts.total_games)
            self.assertIsNone(se_pts.max_players_per_team)

            # Group stage + knockout team league
            client.post(
                f'/t/{self.slug}/categories/new',
                data={
                    'name': 'Team Premier League',
                    'format': 'group_stage',
                    'total_games': '7',
                    'num_groups': '2',
                    'qualifiers_per_group': '2',
                    'max_players_per_team': '5',
                    'num_sets': '3',
                    'games_per_set': '6',
                },
            )
            gs = Category.query.filter_by(name='Team Premier League').first()
            self.assertEqual(gs.format, 'group_stage')
            self.assertEqual(gs.scoring_format, 'games')
            self.assertEqual(gs.total_games, 7)
            self.assertEqual(gs.max_players_per_team, 5)
            self.assertTrue(gs.has_group_stage)

    def test_03_update_settings_preserves_and_isolates_scoring(self):
        """Switching format in setup clears prior format's scoring fields; in_progress edits preserve scoring."""
        cat = Category(
            tournament_id=self.tournament_id,
            name='Switchable Cat',
            format='group_stage',
            has_group_stage=True,
            total_games=7,
            max_players_per_team=5,
            num_groups=2,
            qualifiers_per_group=2,
            status='setup',
        )
        db.session.add(cat)
        db.session.commit()

        with self.app.test_client() as client:
            self._login(client)
            # Switch from group_stage to single_elimination in setup
            client.post(
                f'/tournaments/{self.slug}/categories/{cat.id}/manage',
                data={
                    'action': 'update_settings',
                    'name': 'Switchable Cat',
                    'format': 'single_elimination',
                    'sub_format': 'singles',
                    'scoring_format': 'games',
                    'num_sets': '3',
                    'games_per_set': '4',
                    'total_games': '7',
                    'max_players_per_team': '5',
                },
            )
            db.session.refresh(cat)
            self.assertEqual(cat.format, 'single_elimination')
            self.assertEqual(cat.scoring_format, 'games')
            self.assertEqual(cat.num_sets, 3)
            self.assertEqual(cat.games_per_set, 4)
            self.assertIsNone(cat.total_games)
            self.assertIsNone(cat.max_players_per_team)
            self.assertFalse(cat.has_group_stage)

            # Move to in_progress with points scoring and save non-format settings
            cat.scoring_format = 'points'
            cat.points_to_win = 21
            cat.num_sets = None
            cat.games_per_set = None
            cat.status = 'in_progress'
            db.session.commit()

            client.post(
                f'/tournaments/{self.slug}/categories/{cat.id}/manage',
                data={
                    'action': 'update_settings',
                    'name': 'Switchable Cat Renamed',
                    'max_participants': '16',
                },
            )
            db.session.refresh(cat)
            self.assertEqual(cat.name, 'Switchable Cat Renamed')
            self.assertEqual(cat.scoring_format, 'points')
            self.assertEqual(cat.points_to_win, 21)

    def test_04_single_elimination_view_uses_standard_modal_not_group_rubber(self):
        """Single elimination view must open modal in 'standard' mode and render multi-set inputs."""
        cat = Category(
            tournament_id=self.tournament_id,
            name='SE Tennis Draw',
            format='single_elimination',
            scoring_format='games',
            num_sets=3,
            games_per_set=6,
            status='in_progress',
            draw_published=True,
        )
        db.session.add(cat)
        db.session.flush()

        p1 = Participant(tournament_id=self.tournament_id, category_id=cat.id, name='Roger')
        p2 = Participant(tournament_id=self.tournament_id, category_id=cat.id, name='Rafa')
        db.session.add_all([p1, p2])
        db.session.flush()

        m = Match(
            tournament_id=self.tournament_id,
            category_id=cat.id,
            participant1_id=p1.id,
            participant2_id=p2.id,
            match_type='knockout',
            bracket_type='main',
            round=1,
            match_number=1,
            status='pending',
        )
        db.session.add(m)
        db.session.commit()

        with self.app.test_client() as client:
            self._login(client)
            res = client.get(f'/tournaments/{self.slug}/categories/{cat.id}')
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)
            self.assertIn("'standard'", html)
            self.assertIn('id="modalStandardSetsScore"', html)
            self.assertIn('id="modalSetsTable"', html)
            self.assertIn('Best of 3 Sets (6 Games/Set)', html)

    def test_05_single_elimination_games_and_points_scoring_validation(self):
        """Single elimination uses standard tennis set rules or target points, never Group Stage T=7."""
        cat_games = Category(
            tournament_id=self.tournament_id,
            name='SE Tennis',
            format='single_elimination',
            scoring_format='games',
            num_sets=3,
            games_per_set=6,
            status='in_progress',
        )
        cat_points = Category(
            tournament_id=self.tournament_id,
            name='SE Pickleball',
            format='single_elimination',
            scoring_format='points',
            points_to_win=11,
            status='in_progress',
        )
        db.session.add_all([cat_games, cat_points])
        db.session.flush()

        p1 = Participant(tournament_id=self.tournament_id, category_id=cat_games.id, name='Alice')
        p2 = Participant(tournament_id=self.tournament_id, category_id=cat_games.id, name='Bob')
        p3 = Participant(tournament_id=self.tournament_id, category_id=cat_points.id, name='Carol')
        p4 = Participant(tournament_id=self.tournament_id, category_id=cat_points.id, name='Dave')
        db.session.add_all([p1, p2, p3, p4])
        db.session.flush()

        m_games = Match(
            tournament_id=self.tournament_id,
            category_id=cat_games.id,
            participant1_id=p1.id,
            participant2_id=p2.id,
            match_type='knockout',
            round=1,
            match_number=1,
            status='pending',
        )
        m_points = Match(
            tournament_id=self.tournament_id,
            category_id=cat_points.id,
            participant1_id=p3.id,
            participant2_id=p4.id,
            match_type='knockout',
            round=1,
            match_number=1,
            status='pending',
        )
        db.session.add_all([m_games, m_points])
        db.session.commit()

        with self.app.test_client() as client:
            self._login(client)

            # Group stage 4-3 single-set score must be REJECTED for Single Elimination Best-of-3
            res_bad = client.post(
                f'/tournaments/{self.slug}/categories/{cat_games.id}/match/{m_games.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'games',
                    'num_sets': '3',
                    'games_per_set': '6',
                    'set1_p1': '4',
                    'set1_p2': '3',
                    'winner_id': str(p1.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Invalid Tennis Score', res_bad.data)
            self.assertEqual(db.session.get(Match, m_games.id).status, 'pending')

            # Standard Best-of-3 tennis score (6-4, 6-3) must SUCCEED
            res_ok = client.post(
                f'/tournaments/{self.slug}/categories/{cat_games.id}/match/{m_games.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'games',
                    'num_sets': '3',
                    'games_per_set': '6',
                    'set1_p1': '6',
                    'set1_p2': '4',
                    'set2_p1': '6',
                    'set2_p2': '3',
                    'winner_id': str(p1.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res_ok.data)
            m_g_db = db.session.get(Match, m_games.id)
            self.assertEqual(m_g_db.status, 'completed')
            self.assertEqual(m_g_db.score1, '6-4, 6-3')
            self.assertEqual(m_g_db.winner_id, p1.id)

            # Points scoring (11-7) must SUCCEED for points single elimination
            res_pts = client.post(
                f'/tournaments/{self.slug}/categories/{cat_points.id}/match/{m_points.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'points',
                    'points_to_win': '11',
                    'points_p1': '11',
                    'points_p2': '7',
                    'winner_id': str(p3.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res_pts.data)
            m_p_db = db.session.get(Match, m_points.id)
            self.assertEqual(m_p_db.status, 'completed')
            self.assertEqual(m_p_db.score1, '11')
            self.assertEqual(m_p_db.score2, '7')

    def test_06_round_robin_games_scoring_via_tournament_route(self):
        """Round Robin configured with 'games' scoring uses standard sets validation on tournament route."""
        cat_rr = Category(
            tournament_id=self.tournament_id,
            name='RR Tennis',
            format='round_robin',
            scoring_format='games',
            num_sets=3,
            games_per_set=6,
            status='in_progress',
        )
        db.session.add(cat_rr)
        db.session.flush()

        p1 = Participant(tournament_id=self.tournament_id, category_id=cat_rr.id, name='Eve')
        p2 = Participant(tournament_id=self.tournament_id, category_id=cat_rr.id, name='Frank')
        db.session.add_all([p1, p2])
        db.session.flush()

        m_rr = Match(
            tournament_id=self.tournament_id,
            category_id=cat_rr.id,
            participant1_id=p1.id,
            participant2_id=p2.id,
            match_type='round_robin',
            round=1,
            match_number=1,
            status='pending',
        )
        db.session.add(m_rr)
        db.session.commit()

        with self.app.test_client() as client:
            self._login(client)
            res = client.post(
                f'/t/{self.slug}/match/{m_rr.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'games',
                    'num_sets': '3',
                    'games_per_set': '6',
                    'set1_p1': '6',
                    'set1_p2': '2',
                    'set2_p1': '6',
                    'set2_p2': '4',
                    'winner_id': str(p1.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res.data)
            m_db = db.session.get(Match, m_rr.id)
            self.assertEqual(m_db.status, 'completed')
            self.assertEqual(m_db.score1, '6-2, 6-4')

    def test_07_standard_6_6_tiebreak_7pt_and_win_by_2(self):
        """6-6 set score accepts 7-point tiebreak (and extended win-by-2 like 8-6) and rejects invalid tiebreak."""
        from app.services.tennis_logic import validate_and_format_score

        # 1. 6-6 with 7-5 tiebreak in 1-set match -> promoted to 7-6(5)
        s1, s2 = validate_and_format_score(
            winner_id=10,
            p1_id=10,
            p2_id=20,
            num_sets=1,
            games_per_set=6,
            form_data={'set1_p1': '6', 'set1_p2': '6', 'tb1_p1': '7', 'tb1_p2': '5'},
        )
        self.assertEqual(s1, '7-6(5)')
        self.assertEqual(s2, '6-7(5)')

        # 2. 6-6 with extended 6-6 -> 8-6 tiebreak -> promoted to 7-6(6)
        s1, s2 = validate_and_format_score(
            winner_id=20,
            p1_id=10,
            p2_id=20,
            num_sets=1,
            games_per_set=6,
            form_data={'set1_p1': '6', 'set1_p2': '6', 'tb1_p1': '6', 'tb1_p2': '8'},
        )
        self.assertEqual(s1, '6-7(6)')
        self.assertEqual(s2, '7-6(6)')

        # 3. 6-6 with invalid tiebreak 7-6 (must win by 2) -> raises ValueError
        with self.assertRaises(ValueError):
            validate_and_format_score(
                winner_id=10,
                p1_id=10,
                p2_id=20,
                num_sets=1,
                games_per_set=6,
                form_data={'set1_p1': '6', 'set1_p2': '6', 'tb1_p1': '7', 'tb1_p2': '6'},
            )

        # 4. 6-6 without tiebreak points -> raises ValueError
        with self.assertRaises(ValueError):
            validate_and_format_score(
                winner_id=10,
                p1_id=10,
                p2_id=20,
                num_sets=1,
                games_per_set=6,
                form_data={'set1_p1': '6', 'set1_p2': '6'},
            )

    def test_08_walkover_and_retirement_across_formats(self):
        """Walkover (W/O) and mid-match retirement (RET) work across Games and Points categories."""
        cat_games = Category(
            tournament_id=self.tournament_id,
            name='SE Walkover Tennis',
            format='single_elimination',
            scoring_format='games',
            num_sets=3,
            games_per_set=6,
            status='in_progress',
            draw_published=True,
        )
        cat_points = Category(
            tournament_id=self.tournament_id,
            name='SE Retired Badminton',
            format='single_elimination',
            scoring_format='points',
            points_to_win=21,
            status='in_progress',
            draw_published=True,
        )
        db.session.add_all([cat_games, cat_points])
        db.session.flush()

        p1 = Participant(tournament_id=self.tournament_id, category_id=cat_games.id, name='P1 Tennis')
        p2 = Participant(tournament_id=self.tournament_id, category_id=cat_games.id, name='P2 Tennis')
        p3 = Participant(tournament_id=self.tournament_id, category_id=cat_games.id, name='P3 Tennis')
        p4 = Participant(tournament_id=self.tournament_id, category_id=cat_games.id, name='P4 Tennis')
        b1 = Participant(tournament_id=self.tournament_id, category_id=cat_points.id, name='P1 Badm')
        b2 = Participant(tournament_id=self.tournament_id, category_id=cat_points.id, name='P2 Badm')
        b3 = Participant(tournament_id=self.tournament_id, category_id=cat_points.id, name='P3 Badm')
        b4 = Participant(tournament_id=self.tournament_id, category_id=cat_points.id, name='P4 Badm')
        db.session.add_all([p1, p2, p3, p4, b1, b2, b3, b4])
        db.session.flush()

        m_wo = Match(
            tournament_id=self.tournament_id, category_id=cat_games.id,
            participant1_id=p1.id, participant2_id=p2.id,
            match_type='knockout', round=1, match_number=1, status='pending',
        )
        m_ret = Match(
            tournament_id=self.tournament_id, category_id=cat_games.id,
            participant1_id=p3.id, participant2_id=p4.id,
            match_type='knockout', round=1, match_number=2, status='pending',
        )
        m_pts_wo = Match(
            tournament_id=self.tournament_id, category_id=cat_points.id,
            participant1_id=b1.id, participant2_id=b2.id,
            match_type='knockout', round=1, match_number=1, status='pending',
        )
        m_pts_ret = Match(
            tournament_id=self.tournament_id, category_id=cat_points.id,
            participant1_id=b3.id, participant2_id=b4.id,
            match_type='knockout', round=1, match_number=2, status='pending',
        )
        db.session.add_all([m_wo, m_ret, m_pts_wo, m_pts_ret])
        db.session.commit()

        with self.app.test_client() as client:
            self._login(client)

            # 1. Games Walkover: P2 withdraws -> P1 wins W/O
            res = client.post(
                f'/tournaments/{self.slug}/categories/{cat_games.id}/match/{m_wo.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'games',
                    'outcome_type': 'walkover',
                    'retiring_player': '2',
                    'winner_id': str(p1.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res.data)
            m_wo_db = db.session.get(Match, m_wo.id)
            self.assertEqual(m_wo_db.status, 'completed')
            self.assertEqual(m_wo_db.winner_id, p1.id)
            self.assertEqual(m_wo_db.score1, 'W/O')
            self.assertEqual(m_wo_db.score2, '')

            # 2. Games Mid-match Retirement: P3 retires at 4-6, 1-2 -> P4 wins RET
            res = client.post(
                f'/tournaments/{self.slug}/categories/{cat_games.id}/match/{m_ret.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'games',
                    'outcome_type': 'retired',
                    'retiring_player': '1',
                    'set1_p1': '4',
                    'set1_p2': '6',
                    'set2_p1': '1',
                    'set2_p2': '2',
                    'winner_id': str(p4.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res.data)
            m_ret_db = db.session.get(Match, m_ret.id)
            self.assertEqual(m_ret_db.status, 'completed')
            self.assertEqual(m_ret_db.winner_id, p4.id)
            self.assertEqual(m_ret_db.score1, '4-6, 1-2, RET')
            self.assertEqual(m_ret_db.score2, '6-4, 2-1')

            # 3. Points Walkover: B1 withdraws -> B2 wins W/O
            res = client.post(
                f'/tournaments/{self.slug}/categories/{cat_points.id}/match/{m_pts_wo.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'points',
                    'outcome_type': 'walkover',
                    'retiring_player': '1',
                    'winner_id': str(b2.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res.data)
            m_pwo_db = db.session.get(Match, m_pts_wo.id)
            self.assertEqual(m_pwo_db.status, 'completed')
            self.assertEqual(m_pwo_db.winner_id, b2.id)
            self.assertEqual(m_pwo_db.score2, 'W/O')

            # 4. Points Mid-match Retirement: B4 retires at 7-5 -> B3 wins RET
            res = client.post(
                f'/tournaments/{self.slug}/categories/{cat_points.id}/match/{m_pts_ret.id}/report',
                data={
                    'action': 'complete_match',
                    'scoring_format': 'points',
                    'outcome_type': 'retired',
                    'retiring_player': '2',
                    'points_p1': '7',
                    'points_p2': '5',
                    'winner_id': str(b3.id),
                },
                follow_redirects=True,
            )
            self.assertIn(b'Match result reported successfully', res.data)
            m_pret_db = db.session.get(Match, m_pts_ret.id)
            self.assertEqual(m_pret_db.status, 'completed')
            self.assertEqual(m_pret_db.winner_id, b3.id)
            self.assertEqual(m_pret_db.score1, '7')
            self.assertEqual(m_pret_db.score2, '5 RET')

            # 5. Category view renders cleanly with W/O and RET badges
            view_res = client.get(f'/tournaments/{self.slug}/categories/{cat_games.id}')
            self.assertEqual(view_res.status_code, 200)
            html = view_res.get_data(as_text=True)
            self.assertIn('W/O', html)
            self.assertIn('RET', html)
            self.assertIn('modalOutcomeType', html)



