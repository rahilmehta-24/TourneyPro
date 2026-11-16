import unittest
import os
import tempfile
from flask_jwt_extended import create_access_token
from app import create_app
from app.domain.models import db, User, Tournament, Category, Match, Participant

class SecurityRemediationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret'
            JWT_SECRET_KEY = 'jwt-test-secret'
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{cls.db_path}'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.mkdtemp()

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        with self.app.app_context():
            Match.query.delete()
            Participant.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            User.query.delete()
            db.session.commit()

            # Admin 1 (Owner)
            self.admin1 = User(username='admin1', email='admin1@test.com', role='admin')
            self.admin1.set_password('pass1')
            db.session.add(self.admin1)

            # Admin 2 (Attacker / Different Tournament Owner)
            self.admin2 = User(username='admin2', email='admin2@test.com', role='admin')
            self.admin2.set_password('pass2')
            db.session.add(self.admin2)
            db.session.flush()

            # Tournament owned by Admin 1
            self.tourn = Tournament(
                name="Admin 1 Tournament",
                url_slug="admin-1-tourn",
                user_id=self.admin1.id
            )
            db.session.add(self.tourn)
            db.session.flush()

            self.cat = Category(
                tournament_id=self.tourn.id,
                name="Open",
                format="single_elimination"
            )
            db.session.add(self.cat)
            db.session.flush()

            self.match = Match(
                tournament_id=self.tourn.id,
                category_id=self.cat.id,
                round=1,
                match_number=1,
                status='scheduled'
            )
            db.session.add(self.match)
            db.session.commit()

            self.match_id = self.match.id
            self.cat_id = self.cat.id
            self.admin1_id = self.admin1.id
            self.admin2_id = self.admin2.id
            self.tourn_slug = self.tourn.url_slug

    def test_api_report_match_bola_protection(self):
        """Verify that Admin 2 cannot report or modify matches in Admin 1's tournament (BOLA prevention)"""
        with self.app.app_context():
            token_admin2 = create_access_token(identity=str(self.admin2_id))

        client = self.app.test_client()
        headers = {
            'Authorization': f'Bearer {token_admin2}',
            'Content-Type': 'application/json'
        }
        res = client.post(
            f'/api/v1/matches/{self.match_id}/report',
            json={'action_type': 'live_score', 'score1': '4', 'score2': '2'},
            headers=headers
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json()['message'])

    def test_api_report_match_owner_success(self):
        """Verify that Admin 1 (tournament owner) can successfully report score"""
        with self.app.app_context():
            token_admin1 = create_access_token(identity=str(self.admin1_id))

        client = self.app.test_client()
        headers = {
            'Authorization': f'Bearer {token_admin1}',
            'Content-Type': 'application/json'
        }
        res = client.post(
            f'/api/v1/matches/{self.match_id}/report',
            json={'action_type': 'live_score', 'score1': '4', 'score2': '2'},
            headers=headers
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()['success'])

    def test_allot_lineup_ownership_protection(self):
        """Verify that Admin 2 cannot allot lineup for Admin 1's tournament"""
        client = self.app.test_client()
        # Login as admin2
        with client.session_transaction() as sess:
            sess['user_id'] = self.admin2_id
            sess['role'] = 'admin'

        res = client.post(
            f'/t/admin-1-tourn/categories/{self.cat_id}/fixtures/{self.match_id}/lineup',
            data={'r1_p1_player1': 1, 'r1_p2_player1': 2}
        )
        # Should be 403 Forbidden due to check_tournament_ownership
        self.assertEqual(res.status_code, 403)

    def test_admin_create_user_superadmin_forbidden(self):
        """Verify that an admin cannot create a superadmin user via API"""
        with self.app.app_context():
            token_admin2 = create_access_token(identity=str(self.admin2_id))

        client = self.app.test_client()
        headers = {
            'Authorization': f'Bearer {token_admin2}',
            'Content-Type': 'application/json'
        }
        res = client.post(
            '/api/v1/admin/users',
            json={'username': 'hacked_super', 'email': 'hacked@test.com', 'password': 'Password123!', 'role': 'superadmin'},
            headers=headers
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Superadmin privileges required", res.get_json()['message'])

    def test_anonymous_registrations_account_login_rejected(self):
        """Verify that anonymous proxy user cannot be authenticated"""
        with self.app.app_context():
            anon_user = User(username='anonymous_registrations', email='anonymous@tourneypro.com', role='user')
            anon_user.password_hash = '*disabled*'
            db.session.add(anon_user)
            db.session.commit()

        client = self.app.test_client()
        res = client.post(
            '/api/v1/auth/login',
            json={'username': 'anonymous_registrations', 'password': 'random_unused_password_1234'}
        )
        self.assertEqual(res.status_code, 401)

    def test_payment_method_free_rejected_on_paid_category(self):
        """Verify that free payment method is rejected when category entry fee > 0"""
        with self.app.app_context():
            cat = Category.query.get(self.cat_id)
            cat.entry_fee = 150.0
            from app.domain.models import Player
            player = Player(user_id=self.admin1_id, name="Test Player", gender="Male", age_category="Open")
            db.session.add(player)
            db.session.commit()
            player_id = player.id
            token_admin1 = create_access_token(identity=str(self.admin1_id))

        client = self.app.test_client()
        res = client.post(
            f'/api/v1/tournaments/{self.tourn_slug}/register',
            headers={'Authorization': f'Bearer {token_admin1}'},
            json={
                'category_id': self.cat_id,
                'player_id': player_id,
                'payment_method': 'free'
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("requires an entry fee", res.get_json()['message'])

    def test_bola_player_registration_prevented(self):
        """Verify that user cannot register a player profile owned by another user"""
        with self.app.app_context():
            from app.domain.models import Player
            victim_player = Player(user_id=self.admin1_id, name="Victim Player", gender="Male", age_category="Open")
            db.session.add(victim_player)
            db.session.commit()
            victim_player_id = victim_player.id
            token_admin2 = create_access_token(identity=str(self.admin2_id))

        client = self.app.test_client()
        res = client.post(
            f'/api/v1/tournaments/{self.tourn_slug}/register',
            headers={'Authorization': f'Bearer {token_admin2}'},
            json={
                'category_id': self.cat_id,
                'player_id': victim_player_id,
                'payment_method': 'cash'
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("You may only register player profiles associated with your account", res.get_json()['message'])

    def test_match_score_filter_xss_escaped(self):
        """Verify that match score template filters escape raw HTML/script tags"""
        with self.app.app_context():
            filt_tennis = self.app.jinja_env.filters['format_tennis_score']
            filt_display = self.app.jinja_env.filters['display_match_score']

            res1 = filt_tennis('<script>alert(1)</script>')
            self.assertNotIn('<script>', res1)
            self.assertIn('&lt;script&gt;', res1)

            res2 = filt_display({'score1': '<script>alert(1)</script>', 'score2': '4'})
            self.assertNotIn('<script>', res2)
            self.assertIn('&lt;script&gt;', res2)

    def test_pdf_generator_safe_link_callback(self):
        """Verify that safe_pdf_link_callback blocks unsafe external or file URIs"""
        with self.app.app_context():
            from app.services.pdf.pdf_generator import safe_pdf_link_callback
            self.assertIsNone(safe_pdf_link_callback('http://169.254.169.254/latest/meta-data', None))
            self.assertIsNone(safe_pdf_link_callback('https://malicious.test/exploit.png', None))
            self.assertIsNone(safe_pdf_link_callback('file:///etc/passwd', None))
            self.assertIsNone(safe_pdf_link_callback('../../../config.py', None))

    def test_mobile_tournament_creation_import_fixed(self):
        """Verify that POST /api/v1/tournaments imports cleanly and creates tournament"""
        with self.app.app_context():
            token_admin1 = create_access_token(identity=str(self.admin1_id))

        client = self.app.test_client()
        res = client.post(
            '/api/v1/tournaments',
            headers={'Authorization': f'Bearer {token_admin1}'},
            json={'name': 'Spring Security Open'}
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.get_json()['success'])

if __name__ == '__main__':
    unittest.main()
