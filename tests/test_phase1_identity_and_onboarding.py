"""
Unit and Integration Tests for Phase 1: Identity, Canonical Categories,
Two-Stage Onboarding, Profile Completion, and Zero-Dummy Gated Tournament Entry.
"""

import os
import tempfile
import unittest
from datetime import date, datetime
from app import create_app, db
from app.domain.models import User, Player, Tournament, Category, Participant, Registration
from app.domain.constants import (
    COMPETITION_CATEGORIES, AGE_CATEGORIES,
    calculate_canonical_age_category,
    calculate_profile_completion_percentage
)
from app.services.user_service import (
    register_user, complete_player_profile,
    verify_user_email, request_password_reset, reset_password_with_token
)


class Phase1IdentityAndOnboardingTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-phase1-secret"
            JWT_SECRET_KEY = "test-phase1-jwt-secret"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.mkdtemp()

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        try:
            if os.path.exists(cls.db_path):
                os.remove(cls.db_path)
        except OSError:
            pass

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()

    def _login(self, username, password="password123"):
        return self.client.post("/login", data={
            "username": username,
            "password": password
        }, follow_redirects=False)

    def test_01_canonical_categories_standardization(self):
        """Verify exact 10 competition categories and 14 age categories."""
        self.assertEqual(len(COMPETITION_CATEGORIES), 10)
        self.assertIn("Men's Singles", COMPETITION_CATEGORIES)
        self.assertIn("Women's Singles", COMPETITION_CATEGORIES)
        self.assertIn("Mixed Doubles", COMPETITION_CATEGORIES)
        self.assertIn("Team Event", COMPETITION_CATEGORIES)

        self.assertEqual(len(AGE_CATEGORIES), 14)
        self.assertEqual(AGE_CATEGORIES[0], "Under 8")
        self.assertEqual(AGE_CATEGORIES[5], "Under 18")
        self.assertEqual(AGE_CATEGORIES[6], "Under 21")
        self.assertEqual(AGE_CATEGORIES[7], "Open")
        self.assertEqual(AGE_CATEGORIES[8], "Veterans 35+")
        self.assertEqual(AGE_CATEGORIES[13], "Veterans 60+")

    def test_02_dec_31_calendar_year_cutoff_age_calculation(self):
        """Verify player age category is derived as tournament_year - birth_year."""
        # 14 years old in 2026
        dob_u14 = date(2012, 11, 20)
        self.assertEqual(calculate_canonical_age_category(dob_u14, tournament_year=2026), "Under 14")

        # 8 years old in 2026
        dob_u8 = date(2018, 5, 10)
        self.assertEqual(calculate_canonical_age_category(dob_u8, tournament_year=2026), "Under 8")

        # 26 years old in 2026 -> Open
        dob_open = date(2000, 1, 15)
        self.assertEqual(calculate_canonical_age_category(dob_open, tournament_year=2026), "Open")

        # 42 years old in 2026 -> Veterans 40+
        dob_v40 = date(1984, 8, 30)
        self.assertEqual(calculate_canonical_age_category(dob_v40, tournament_year=2026), "Veterans 40+")

        # 62 years old in 2026 -> Veterans 60+
        dob_v60 = date(1964, 2, 1)
        self.assertEqual(calculate_canonical_age_category(dob_v60, tournament_year=2026), "Veterans 60+")

    def test_03_registration_intent_user_decouples_player_profile(self):
        """Standard user registration creates user record without fabricating athletic profile."""
        res = register_user(
            username="fan_user_1",
            email="fan@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="Fan User",
            registration_intent="user"
        )
        self.assertTrue(res.success)
        user = res.user
        self.assertEqual(user.role, "user")
        self.assertEqual(user.registration_intent, "user")
        self.assertFalse(user.profile_completed)
        self.assertEqual(user.completion_percentage, 30)

        # Confirm player shell is incomplete without verified athletic onboarding
        player = Player.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(player)
        self.assertEqual(player.profile_status, "incomplete")
        self.assertEqual(player.total_points, 0.0)
        self.assertIsNone(player.dob)
        self.assertFalse(user.profile_completed)

    def test_04_registration_intent_player_initializes_shell_profile(self):
        """Player registration creates user and initializes an incomplete player profile shell."""
        res = register_user(
            username="player_competitor_1",
            email="competitor@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="Competitor One",
            registration_intent="player"
        )
        self.assertTrue(res.success)
        user = res.user
        self.assertEqual(user.registration_intent, "player")
        self.assertFalse(user.profile_completed)

        player = Player.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(player)
        self.assertEqual(player.name, "Competitor One")
        self.assertEqual(player.profile_status, "incomplete")
        self.assertEqual(player.total_points, 0.0)

    def test_05_unqualified_players_excluded_from_leaderboard(self):
        """Zero dummy data: newly registered users with 0 points and 0 registrations never appear on leaderboard."""
        register_user(
            username="idle_user_1",
            email="idle1@example.com",
            password="SecurePassword123!",
            full_name="Idle One",
            registration_intent="player"
        )

        res_web = self.client.get("/leaderboard/")
        self.assertEqual(res_web.status_code, 200)
        self.assertNotIn(b"Idle One", res_web.data)

        res_api = self.client.get("/api/v1/leaderboard")
        self.assertEqual(res_api.status_code, 200)
        json_data = res_api.get_json()
        self.assertEqual(json_data["count"], 0)

        # Now give a player points through competition
        player = Player.query.filter_by(name="Idle One").first()
        player.total_points = 50.0
        db.session.commit()

        res_web2 = self.client.get("/leaderboard/")
        self.assertIn(b"Idle One", res_web2.data)

        res_api2 = self.client.get("/api/v1/leaderboard")
        json_data2 = res_api2.get_json()
        self.assertEqual(json_data2["count"], 1)
        self.assertEqual(json_data2["rankings"][0]["name"], "Idle One")

    def test_06_profile_completion_calculates_100_percent(self):
        """Stage 2 onboarding validates fields and elevates completion percentage to 100%."""
        res = register_user(
            username="athlete_john",
            email="john@example.com",
            password="SecurePassword123!",
            full_name="John Doe",
            registration_intent="player"
        )
        user = res.user
        self.assertFalse(user.profile_completed)

        comp_res = complete_player_profile(
            user_id=user.id,
            full_name="Johnathon Doe",
            gender="Male",
            dob=date(1995, 6, 15),
            contact_number="+919876543210",
            primary_sport="Tennis",
            skill_level="Advanced",
            preferred_competition_category="Men's Singles",
            emergency_contact_name="Jane Doe",
            emergency_contact_phone="+919876500000"
        )
        self.assertTrue(comp_res["success"])
        self.assertEqual(comp_res["completion_percentage"], 100)
        self.assertTrue(comp_res["is_complete"])

        db.session.refresh(user)
        self.assertTrue(user.profile_completed)
        self.assertEqual(user.completion_percentage, 100)

        player = Player.query.filter_by(user_id=user.id).first()
        self.assertEqual(player.name, "Johnathon Doe")
        self.assertEqual(player.gender, "Male")
        self.assertEqual(player.age_category, "Open")
        self.assertEqual(player.profile_status, "complete")

    def test_07_gated_tournament_registration_intercept(self):
        """Incomplete profile is redirected to /profile/complete?next=... when registering for tournament."""
        # Setup tournament
        creator = User(username="director_org", email="org@example.com", role="admin")
        creator.set_password("SecurePassword123!")
        db.session.add(creator)
        db.session.flush()

        tournament = Tournament(
            name="Spring Championship 2026",
            url_slug="spring-championship-2026",
            user_id=creator.id,
            status="registration"
        )
        db.session.add(tournament)
        db.session.flush()

        cat = Category(
            tournament_id=tournament.id,
            name="Men's Singles",
            gender="Male",
            age_category="Open",
            format="singles",
            entry_fee=50.0
        )
        db.session.add(cat)
        db.session.commit()

        # Case A: Unauthenticated request redirects to /login?next=...
        res_guest = self.client.get(f"/tournaments/{tournament.url_slug}/register")
        self.assertEqual(res_guest.status_code, 302)
        self.assertIn("/login", res_guest.headers["Location"])
        self.assertIn(f"next=/tournaments/{tournament.url_slug}/register", res_guest.headers["Location"])

        # Case B: Authenticated user with incomplete profile redirects to /profile/complete?next=...
        register_user(
            username="incomplete_user",
            email="incomplete@example.com",
            password="password123",
            full_name="Incomplete User",
            registration_intent="user"
        )
        self._login("incomplete_user")

        res_auth_incomplete = self.client.get(f"/tournaments/{tournament.url_slug}/register")
        self.assertEqual(res_auth_incomplete.status_code, 302)
        self.assertIn("/profile/complete", res_auth_incomplete.headers["Location"])
        self.assertIn(f"next=/tournaments/{tournament.url_slug}/register", res_auth_incomplete.headers["Location"])

        # Case C: After completing profile, user gets 200 OK on tournament register
        user = User.query.filter_by(username="incomplete_user").first()
        complete_player_profile(
            user_id=user.id,
            full_name="Now Complete",
            gender="Male",
            dob=date(1998, 4, 12),
            contact_number="+919999988888",
            emergency_contact_name="Guardian Name",
            emergency_contact_phone="+919999977777"
        )

        res_complete = self.client.get(f"/tournaments/{tournament.url_slug}/register")
        self.assertEqual(res_complete.status_code, 200)

    def test_08_email_verification_and_password_reset(self):
        """Verify token generation, email verification, and password reset."""
        res = register_user(
            username="verify_user",
            email="verify@example.com",
            password="InitialPassword123!",
            full_name="Verify User"
        )
        user = res.user
        token = user.email_verification_token
        self.assertIsNotNone(token)
        self.assertFalse(user.is_email_verified)

        # Verify email
        v_res = verify_user_email(token)
        self.assertTrue(v_res["success"])
        db.session.refresh(user)
        self.assertTrue(user.is_email_verified)

        # Password reset
        r_req = request_password_reset("verify@example.com")
        self.assertTrue(r_req["success"])
        db.session.refresh(user)
        reset_token = user.password_reset_token
        self.assertIsNotNone(reset_token)

        # Reset with new password
        r_done = reset_password_with_token(reset_token, "NewSecurePassword456!", "NewSecurePassword456!")
        self.assertTrue(r_done["success"])
        db.session.refresh(user)
        self.assertTrue(user.check_password("NewSecurePassword456!"))
        self.assertIsNone(user.password_reset_token)


if __name__ == '__main__':
    unittest.main()
