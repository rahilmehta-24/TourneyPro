import os
import tempfile
import unittest
from datetime import date
from app import create_app, db
from app.domain.models import User, Player, Tournament, UserNotificationPreferences
from app.services.user_service import (
    register_user,
    ensure_user_profile,
    MSG_REGISTRATION_CLEAN_WORKSPACE,
    MSG_REGISTRATION_EXISTING_DATA,
    MSG_REGISTRATION_INIT_FAILED
)


class TestAuthAndProfileSecurity(unittest.TestCase):
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
        self.client = self.app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        for p in Player.query.all():
            db.session.delete(p)
        for u in User.query.all():
            db.session.delete(u)
        db.session.commit()
        self.app_context.pop()

    # -------------------------------------------------------------
    # 1. Registration Testing
    # -------------------------------------------------------------
    def test_01_register_new_user_clean_workspace(self):
        """Register a brand new user and verify clean workspace & exact notification."""
        res = register_user(
            username="player_alice",
            email="alice@baseline.test",
            password="StrongPass123!",
            password_confirm="StrongPass123!",
            full_name="Alice Smith",
            gender="Female"
        )
        self.assertTrue(res.success)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.message, MSG_REGISTRATION_CLEAN_WORKSPACE)
        self.assertTrue(res.is_clean)
        self.assertFalse(res.has_existing_data)

        # Verify DB records
        user = User.query.filter_by(username="player_alice").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "user")  # Non-admin by default

        player = Player.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(player)
        self.assertEqual(player.name, "Alice Smith")
        self.assertEqual(player.email, "alice@baseline.test")
        self.assertEqual(player.gender, "Female")
        self.assertTrue(player.registration_no.startswith("TP-"))

        # Verify notification preferences
        prefs = UserNotificationPreferences.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(prefs)

    def test_02_register_user_with_existing_unassigned_data(self):
        """Register user whose email matches an unassigned player: preserves records."""
        # Pre-seed an unassigned player profile
        legacy_player = Player(
            name="Bob Jones",
            email="bob@baseline.test",
            gender="Male",
            age_category="Open",
            registration_no="TP-LEGACY-001",
            matches_played=12,
            matches_won=9,
            matches_lost=3
        )
        db.session.add(legacy_player)
        db.session.commit()

        res = register_user(
            username="player_bob",
            email="bob@baseline.test",
            password="StrongPass123!",
            password_confirm="StrongPass123!",
            full_name="Bob Jones"
        )
        self.assertTrue(res.success)
        self.assertEqual(res.message, MSG_REGISTRATION_EXISTING_DATA)
        self.assertTrue(res.has_existing_data)
        self.assertFalse(res.is_clean)

        # Verify profile was linked and existing stats preserved
        user = User.query.filter_by(username="player_bob").first()
        self.assertIsNotNone(user)
        self.assertEqual(legacy_player.user_id, user.id)
        self.assertEqual(legacy_player.registration_no, "TP-LEGACY-001")
        self.assertEqual(legacy_player.matches_played, 12)

    def test_03_registration_validation_and_duplicate_prevention(self):
        """Test mandatory validation, weak passwords, password confirmation, duplicate email/username."""
        # Pre-seed an existing user
        register_user("charlie", "charlie@baseline.test", "StrongPass123!", "StrongPass123!")

        # Duplicate username
        res = register_user("charlie", "different@baseline.test", "StrongPass123!", "StrongPass123!")
        self.assertFalse(res.success)
        self.assertIn("Username already exists", res.message)

        # Duplicate email
        res = register_user("charlie2", "charlie@baseline.test", "StrongPass123!", "StrongPass123!")
        self.assertFalse(res.success)
        self.assertIn("Email already exists", res.message)

        # Password mismatch
        res = register_user("david", "david@baseline.test", "StrongPass123!", "WrongConfirm123!")
        self.assertFalse(res.success)
        self.assertIn("do not match", res.message)

        # Weak password (under 8 chars or no numbers/symbols)
        res = register_user("david", "david@baseline.test", "short", "short")
        self.assertFalse(res.success)
        self.assertIn("Password must be at least 8 characters", res.message)

        res = register_user("david", "david@baseline.test", "lettersalltheway", "lettersalltheway")
        self.assertFalse(res.success)
        self.assertIn("at least one number or special character", res.message)

    def test_04_registration_initialization_failure_rollback(self):
        """Test transaction rollback on profile initialization failure."""
        res = register_user(
            username="failure_test",
            email="fail@baseline.test",
            password="StrongPass123!",
            password_confirm="StrongPass123!",
            simulate_init_failure=True
        )
        self.assertFalse(res.success)
        self.assertEqual(res.message, MSG_REGISTRATION_INIT_FAILED)

        # Ensure no orphaned User or Player record exists
        user = User.query.filter_by(username="failure_test").first()
        self.assertIsNone(user)
        player = Player.query.filter_by(email="fail@baseline.test").first()
        self.assertIsNone(player)

    # -------------------------------------------------------------
    # 2. Authentication & Session Testing (Web & API)
    # -------------------------------------------------------------
    def test_05_api_register_and_login_flow(self):
        """API registration and sign-in returns JWT and isolates identity."""
        reg_res = self.client.post("/api/v1/auth/register", json={
            "username": "emma_raducanu",
            "email": "emma@baseline.test",
            "password": "Champion2026!",
            "password_confirm": "Champion2026!",
            "full_name": "Emma Raducanu",
            "role": "admin"  # Attempt privilege escalation
        })
        self.assertEqual(reg_res.status_code, 201)
        data = reg_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["role"], "user")  # Privileged role escalation MUST be rejected!

        access_token = data["access_token"]
        self.assertIsNotNone(access_token)

        # Authenticate via /auth/login
        login_res = self.client.post("/api/v1/auth/login", json={
            "username": "emma_raducanu",
            "password": "Champion2026!"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data["success"])
        self.assertEqual(login_data["user"]["username"], "emma_raducanu")

        # Wrong password rejected
        bad_login = self.client.post("/api/v1/auth/login", json={
            "username": "emma_raducanu",
            "password": "WrongPassword!"
        })
        self.assertEqual(bad_login.status_code, 401)

    def test_06_web_login_correct_profile_redirection(self):
        """Web login correctly redirects to authenticated user's player dashboard."""
        register_user("roger_f", "roger@baseline.test", "Federer2026!", "Federer2026!", full_name="Roger Federer")

        login_res = self.client.post("/login", data={
            "username": "roger_f",
            "password": "Federer2026!"
        }, follow_redirects=False)

        # Must redirect to player.dashboard, NOT to main.index or a hardcoded profile!
        self.assertEqual(login_res.status_code, 302)
        self.assertTrue(login_res.location.endswith("/player/dashboard"))

    # -------------------------------------------------------------
    # 3. Profile Access, Self-Healing & Cross-User Data Isolation
    # -------------------------------------------------------------
    def test_07_api_users_me_profile_resolution_and_recovery(self):
        """Test /api/v1/users/me returns genuine profile and heals missing profile."""
        # Create a user directly without a player profile to simulate broken legacy state
        orphan_user = User(username="orphan_user", email="orphan@baseline.test", role="user")
        orphan_user.set_password("SecurePass123!")
        db.session.add(orphan_user)
        db.session.commit()

        login_res = self.client.post("/api/v1/auth/login", json={
            "username": "orphan_user",
            "password": "SecurePass123!"
        })
        token = login_res.get_json()["access_token"]

        # Call /users/me: must automatically self-heal and return player profile
        me_res = self.client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        data = me_res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["username"], "orphan_user")
        self.assertIsNotNone(data["player"])
        self.assertEqual(data["player"]["email"], "orphan@baseline.test")

    def test_08_cross_user_data_isolation(self):
        """User B cannot view or tamper with User A's profile or data."""
        # Create User A
        res_a = register_user("user_a", "usera@baseline.test", "PassUserA123!", "PassUserA123!", full_name="User Alpha")
        player_a = Player.query.filter_by(user_id=res_a.user.id).first()

        # Create User B
        res_b = register_user("user_b", "userb@baseline.test", "PassUserB123!", "PassUserB123!", full_name="User Beta")
        player_b = Player.query.filter_by(user_id=res_b.user.id).first()

        # Sign in as User B on web
        self.client.post("/login", data={"username": "user_b", "password": "PassUserB123!"})

        # User B visits dashboard: should only see User B's profile
        dash_res = self.client.get("/player/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        html = dash_res.get_data(as_text=True)
        self.assertIn("User Beta", html)
        self.assertNotIn("User Alpha", html)

        # Attempt IDOR: User B attempts to edit User A's profile
        edit_res = self.client.post("/player/dashboard", data={
            "action": "update_profile",
            "player_id": player_a.id,
            "name": "Hacked Name"
        })
        # Should return 404 because player_id is scoped to current_user.id
        self.assertEqual(edit_res.status_code, 404)

        # Verify player_a was not modified
        db.session.refresh(player_a)
        self.assertEqual(player_a.name, "User Alpha")

    def test_09_account_deletion_scrubs_pii(self):
        """Account deletion scrubs user and personal details properly."""
        reg = register_user("delete_me", "deleteme@baseline.test", "DeletePass123!", "DeletePass123!")
        uid = reg.user.id

        login_res = self.client.post("/api/v1/auth/login", json={
            "username": "delete_me",
            "password": "DeletePass123!"
        })
        token = login_res.get_json()["access_token"]

        del_res = self.client.post("/api/v1/users/delete_account", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(del_res.status_code, 200)

        # User should no longer exist or be deleted
        reloaded = db.session.get(User, uid)
        self.assertTrue(reloaded is None or reloaded.role == "deleted")

        # Subsequent login must fail
        login_again = self.client.post("/api/v1/auth/login", json={
            "username": "delete_me",
            "password": "DeletePass123!"
        })
        self.assertEqual(login_again.status_code, 401)


if __name__ == "__main__":
    unittest.main()
