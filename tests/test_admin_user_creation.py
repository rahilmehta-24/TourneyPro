import os
import tempfile
import unittest
from datetime import date
from app import create_app, db
from app.domain.models import User, Player, Tournament, UserNotificationPreferences
from app.services.user_service import (
    admin_create_user,
    MSG_CLEAN_WORKSPACE,
    MSG_EXISTING_DATA_RETAINED,
    MSG_VERIFICATION_FAILED
)


class TestAdminUserCreation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret-key-at-least-32-bytes-long"
            JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.gettempdir()

        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Check or seed superadmin
        self.superadmin = User.query.filter_by(username='superadmin').first()
        if not self.superadmin:
            self.superadmin = User(username='superadmin', email='superadmin@baseline.test', role='superadmin')
            self.superadmin.set_password('AdminPass123!')
            db.session.add(self.superadmin)

        # Check or seed regular user
        self.regular_user = User.query.filter_by(username='regular').first()
        if not self.regular_user:
            self.regular_user = User(username='regular', email='regular@baseline.test', role='user')
            self.regular_user.set_password('UserPass123!')
            db.session.add(self.regular_user)

        db.session.commit()

    def tearDown(self):
        for p in Player.query.all():
            db.session.delete(p)
        for u in User.query.filter(User.username.notin_(['superadmin', 'regular'])).all():
            db.session.delete(u)
        db.session.commit()
        self.app_context.pop()

    def test_clean_workspace_creation_success(self):
        """Case 1: New user created with no previous records displays clean workspace notification."""
        result = admin_create_user(
            username='carlosalcaraz',
            email='carlos@alcaraz.test',
            password='Password123!',
            role='user',
            full_name='Carlos Alcaraz'
        )

        self.assertTrue(result.success)
        self.assertEqual(result.category, 'success')
        self.assertEqual(result.message, MSG_CLEAN_WORKSPACE)
        self.assertTrue(result.is_clean)
        self.assertFalse(result.has_existing_data)
        self.assertFalse(result.verification_failed)

        # Verify DB records
        created_user = User.query.filter_by(username='carlosalcaraz').first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.email, 'carlos@alcaraz.test')

        # Verify user preferences initialized
        prefs = UserNotificationPreferences.query.filter_by(user_id=created_user.id).first()
        self.assertIsNotNone(prefs)

        # Verify player profile created and isolated to this user ID
        player = Player.query.filter_by(user_id=created_user.id).first()
        self.assertIsNotNone(player)
        self.assertEqual(player.name, 'Carlos Alcaraz')
        self.assertEqual(player.user_id, created_user.id)

        # Verify strict isolation: no tournaments exist for this user
        tournaments = Tournament.query.filter_by(user_id=created_user.id).all()
        self.assertEqual(len(tournaments), 0)

    def test_existing_user_data_detected_and_retained(self):
        """Case 2: If existing user records exist, they are preserved and existing data notification is shown."""
        # Pre-seed an unassigned player profile that previously existed with this email
        pre_existing_player = Player(
            user_id=None,
            name='Novak Djokovic',
            email='novak@djokovic.test',
            gender='Male',
            age_category='Open',
            registration_no='TP-PREV-9999',
            registration_date=date.today(),
            current_status='Active'
        )
        db.session.add(pre_existing_player)
        db.session.commit()
        pre_existing_player_id = pre_existing_player.id

        result = admin_create_user(
            username='novakdjokovic',
            email='novak@djokovic.test',
            password='Password123!',
            role='user'
        )

        self.assertTrue(result.success)
        self.assertEqual(result.category, 'success')
        self.assertEqual(result.message, MSG_EXISTING_DATA_RETAINED)
        self.assertTrue(result.has_existing_data)
        self.assertFalse(result.is_clean)
        self.assertFalse(result.verification_failed)

        # Verify existing record was retained and NOT overwritten
        retained_player = db.session.get(Player, pre_existing_player_id)
        self.assertIsNotNone(retained_player)
        self.assertEqual(retained_player.registration_no, 'TP-PREV-9999')
        self.assertEqual(retained_player.user_id, result.user.id)

    def test_workspace_verification_failure_displays_warning(self):
        """Case 3: When initialization or verification fails, a warning notification is displayed."""
        result = admin_create_user(
            username='failuretestuser',
            email='fail@test.com',
            password='Password123!',
            role='user',
            simulate_verification_failure=True
        )

        self.assertTrue(result.success)
        self.assertEqual(result.category, 'warning')
        self.assertEqual(result.message, MSG_VERIFICATION_FAILED)
        self.assertTrue(result.verification_failed)
        self.assertFalse(result.is_clean)

        # Verify user still exists in database (account was created)
        user = User.query.filter_by(username='failuretestuser').first()
        self.assertIsNotNone(user)

    def test_duplicate_user_handled_gracefully(self):
        """Duplicate username or email fails gracefully with error category."""
        # Attempt to create user with existing username
        result1 = admin_create_user(
            username='superadmin',
            email='newemail@test.com',
            password='Password123!'
        )
        self.assertFalse(result1.success)
        self.assertEqual(result1.category, 'error')
        self.assertEqual(result1.message, 'Username already exists.')

        # Attempt to create user with existing email
        result2 = admin_create_user(
            username='newusername',
            email='regular@baseline.test',
            password='Password123!'
        )
        self.assertFalse(result2.success)
        self.assertEqual(result2.category, 'error')
        self.assertEqual(result2.message, 'Email already exists.')

    def test_web_admin_create_user_flow(self):
        """Web admin route /admin/users/create verifies authentication, authorization, and flash notification."""
        # Unauthenticated request redirects to login
        res_unauth = self.client.post('/admin/users/create', data={
            'username': 'test1', 'email': 'test1@test.com', 'password': 'pass'
        })
        self.assertEqual(res_unauth.status_code, 302)

        # Regular user gets 403 Forbidden
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.regular_user.id)
            sess['user_id'] = self.regular_user.id
            sess['role'] = 'user'
        res_forbidden = self.client.post('/admin/users/create', data={
            'username': 'test2', 'email': 'test2@test.com', 'password': 'pass'
        })
        self.assertEqual(res_forbidden.status_code, 403)

        # Superadmin succeeds and receives flash message
        superadmin = User.query.filter_by(role='superadmin').first()
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(superadmin.id)
            sess['user_id'] = superadmin.id
            sess['role'] = 'superadmin'

        res_admin = self.client.post('/admin/users/create', data={
            'username': 'janniksinner',
            'email': 'jannik@sinner.test',
            'password': 'Password123!',
            'role': 'user',
            'full_name': 'Jannik Sinner'
        }, follow_redirects=True)

        self.assertEqual(res_admin.status_code, 200)
        response_text = res_admin.get_data(as_text=True)
        self.assertIn("A fresh workspace has been initialized", response_text)

        self.assertEqual(res_admin.status_code, 200)
        response_text = res_admin.get_data(as_text=True)
        self.assertIn("A fresh workspace has been initialized", response_text)

    def test_api_admin_create_user_flow(self):
        """REST API endpoint POST /api/v1/admin/users verifies JWT, RBAC, and JSON envelope."""
        from flask_jwt_extended import create_access_token

        # Non-admin token gets 403
        reg_token = create_access_token(identity=str(self.regular_user.id))
        res_api_forbid = self.client.post(
            '/api/v1/admin/users',
            headers={'Authorization': f'Bearer {reg_token}'},
            json={'username': 'apiuser1', 'email': 'api1@test.com', 'password': 'pass'}
        )
        self.assertEqual(res_api_forbid.status_code, 403)

        # Admin token succeeds
        admin_token = create_access_token(identity=str(self.superadmin.id))
        res_api_ok = self.client.post(
            '/api/v1/admin/users',
            headers={'Authorization': f'Bearer {admin_token}'},
            json={
                'username': 'daniilmedvedev',
                'email': 'daniil@medvedev.test',
                'password': 'Password123!',
                'role': 'user'
            }
        )
        self.assertEqual(res_api_ok.status_code, 201)
        data = res_api_ok.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], MSG_CLEAN_WORKSPACE)
        self.assertTrue(data['is_clean'])
        self.assertEqual(data['user']['username'], 'daniilmedvedev')


if __name__ == '__main__':
    unittest.main()
