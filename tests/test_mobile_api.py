import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from app import create_app
from app.domain.models import (
    db, User, Tournament, Category, Match, Participant, Player,
    TournamentStaff, Registration, DeviceRegistration, InAppNotification,
    UserNotificationPreferences, Group
)


class MobileApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "mobile-test-secret-key-at-least-32-bytes-long"
            JWT_SECRET_KEY = "mobile-jwt-test-secret-key-at-least-32-bytes"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"
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
        self.client = self.app.test_client()

        with self.app.app_context():
            db.session.rollback()
            InAppNotification.query.delete()
            DeviceRegistration.query.delete()
            UserNotificationPreferences.query.delete()
            Registration.query.delete()
            TournamentStaff.query.delete()
            Match.query.delete()
            Participant.query.delete()
            Group.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            Player.query.delete()
            User.query.delete()
            db.session.commit()

            # Seed Owner
            self.owner = User(username="organizer", email="organizer@baseline.local", role="admin")
            self.owner.set_password("pass123")
            db.session.add(self.owner)

            # Seed Player User
            self.player_user = User(username="player1", email="player1@baseline.local", role="user")
            self.player_user.set_password("pass123")
            db.session.add(self.player_user)

            # Seed Official User
            self.official_user = User(username="umpire1", email="umpire1@baseline.local", role="user")
            self.official_user.set_password("pass123")
            db.session.add(self.official_user)

            db.session.commit()

            # Seed Player Profile
            self.player_profile = Player(
                user_id=self.player_user.id,
                name="Rafael Nadal",
                gender="Boys",
                age_category="Open",
                contact_number="9876543210",
                email="player1@baseline.local"
            )
            self.player_profile2 = Player(
                name="Roger Federer",
                gender="Boys",
                age_category="Open",
                contact_number="9876543211",
                email="federer@baseline.local"
            )
            db.session.add_all([self.player_profile, self.player_profile2])
            db.session.commit()

            # Seed Tournament
            self.tournament = Tournament(
                user_id=self.owner.id,
                name="Baseline Championship",
                url_slug="baseline-championship",
                status="registration",
                start_date=date.today(),
                end_date=date.today() + timedelta(days=2),
                num_courts=2,
                court_names="Court 1, Court 2"
            )
            db.session.add(self.tournament)
            db.session.commit()

            # Seed Category
            self.category = Category(
                tournament_id=self.tournament.id,
                name="Men's Singles Open",
                gender="Men",
                format="single_elimination",
                entry_fee=500.0,
                status="in_progress",
                draw_published=False
            )
            db.session.add(self.category)
            db.session.commit()

            # Seed Participants
            self.part1 = Participant(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                player_id=self.player_profile.id,
                name="Rafael Nadal",
                manual_seed=1
            )
            self.part2 = Participant(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                player_id=self.player_profile2.id,
                name="Roger Federer",
                manual_seed=2
            )
            db.session.add_all([self.part1, self.part2])
            db.session.commit()

            # Seed Match
            self.match = Match(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                round=1,
                match_number=1,
                participant1_id=self.part1.id,
                participant2_id=self.part2.id,
                court_name="Court 1",
                scheduled_date=date.today(),
                scheduled_time=datetime.utcnow() + timedelta(hours=1),
                status="pending",
                lock_version=1
            )
            db.session.add(self.match)

            # Seed Court Staff with 6-digit PIN
            self.court_staff = TournamentStaff(
                tournament_id=self.tournament.id,
                user_id=None,
                role="official",
                assigned_court="Court 1",
                access_pin="123456",
                pin_expires_at=datetime.utcnow() + timedelta(hours=12)
            )
            db.session.add(self.court_staff)
            db.session.commit()

            self.owner_id = self.owner.id
            self.player_user_id = self.player_user.id
            self.tournament_slug = self.tournament.url_slug
            self.category_id = self.category.id
            self.part1_id = self.part1.id
            self.part2_id = self.part2.id
            self.match_id = self.match.id
            self.player_profile_id = self.player_profile.id

    def _login(self, username, password="pass123"):
        res = self.client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        return res.get_json()

    # ----------------------------------------------------------------------
    # 1. AUTHENTICATION & REFRESH TOKEN ROTATION
    # ----------------------------------------------------------------------
    def test_01_login_and_refresh_token(self):
        login_data = self._login("organizer")
        self.assertTrue(login_data["success"])
        self.assertIn("access_token", login_data)
        self.assertIn("refresh_token", login_data)
        self.assertEqual(login_data["user"]["role"], "admin")

        refresh_token = login_data["refresh_token"]
        res_refresh = self.client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        self.assertEqual(res_refresh.status_code, 200)
        data = res_refresh.get_json()
        self.assertTrue(data["success"])
        self.assertIn("access_token", data)

    # ----------------------------------------------------------------------
    # 2. COURT PIN AUTHENTICATION & MATCH SCORING
    # ----------------------------------------------------------------------
    def test_02_court_pin_login_and_scoring(self):
        # Invalid PIN
        res_bad = self.client.post("/api/v1/auth/court-login", json={
            "pin": "999999",
            "slug": self.tournament_slug
        })
        self.assertEqual(res_bad.status_code, 401)

        # Valid 6-digit PIN
        res_good = self.client.post("/api/v1/auth/court-login", json={
            "pin": "123456",
            "slug": self.tournament_slug
        })
        self.assertEqual(res_good.status_code, 200)
        court_data = res_good.get_json()
        self.assertTrue(court_data["success"])
        self.assertEqual(court_data["court"], "Court 1")
        access_token = court_data["access_token"]

        # Report live score using court PIN token
        res_live = self.client.post(
            f"/api/v1/matches/{self.match_id}/report",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "action_type": "live_score",
                "score1": "6",
                "score2": "4",
                "lock_version": 1
            }
        )
        self.assertEqual(res_live.status_code, 200)

        # Complete match
        res_complete = self.client.post(
            f"/api/v1/matches/{self.match_id}/report",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "action_type": "complete_match",
                "winner_id": self.part1_id,
                "score1": "6, 6",
                "score2": "4, 3",
                "lock_version": 2
            }
        )
        self.assertEqual(res_complete.status_code, 200)

        with self.app.app_context():
            m = Match.query.get(self.match_id)
            self.assertEqual(m.status, "completed")
            self.assertEqual(m.winner_id, self.part1_id)

    # ----------------------------------------------------------------------
    # 3. CONCURRENCY OPTIMISTIC LOCKING (HTTP 409)
    # ----------------------------------------------------------------------
    def test_03_concurrency_lock_version_409(self):
        login_data = self._login("organizer")
        token = login_data["access_token"]

        # First official updates score (increments lock_version from 1 to 2)
        res1 = self.client.post(
            f"/api/v1/matches/{self.match_id}/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action_type": "live_score",
                "score1": "3",
                "score2": "2",
                "lock_version": 1
            }
        )
        self.assertEqual(res1.status_code, 200)

        # Second official sends stale lock_version=1 -> must reject with 409 Conflict
        res2 = self.client.post(
            f"/api/v1/matches/{self.match_id}/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action_type": "live_score",
                "score1": "4",
                "score2": "2",
                "lock_version": 1
            }
        )
        self.assertEqual(res2.status_code, 409)
        self.assertIn("Conflict", res2.get_json()["message"])

    # ----------------------------------------------------------------------
    # 4. ANTI-CONFLICT OF INTEREST GUARD (HTTP 403)
    # ----------------------------------------------------------------------
    def test_04_anti_conflict_of_interest(self):
        login_data = self._login("player1")
        token = login_data["access_token"]

        # Player attempts to score their own match
        res = self.client.post(
            f"/api/v1/matches/{self.match_id}/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action_type": "complete_match",
                "winner_id": self.part1_id,
                "score1": "6",
                "score2": "0",
                "lock_version": 1
            }
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Forbidden", res.get_json()["message"])

    # ----------------------------------------------------------------------
    # 5. TOURNAMENT REGISTRATION & ORGANIZER REVIEW
    # ----------------------------------------------------------------------
    def test_05_tournament_registration_and_review(self):
        login_data = self._login("player1")
        token = login_data["access_token"]

        # Submit registration with UPI UTR
        res_reg = self.client.post(
            f"/api/v1/tournaments/{self.tournament_slug}/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": self.category_id,
                "player_id": self.player_profile_id,
                "payment_method": "online",
                "transaction_id": "UPI_UTR_987654321012",
                "amount_due": 500.0
            }
        )
        self.assertEqual(res_reg.status_code, 201)
        reg_id = res_reg.get_json()["registration"]["id"]

        # Duplicate registration attempt
        res_dup = self.client.post(
            f"/api/v1/tournaments/{self.tournament_slug}/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "category_id": self.category_id,
                "player_id": self.player_profile_id
            }
        )
        self.assertEqual(res_dup.status_code, 409)

        # Organizer review and approval
        owner_login = self._login("organizer")
        owner_token = owner_login["access_token"]

        res_review = self.client.post(
            f"/api/v1/registrations/{reg_id}/review",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "status": "approved",
                "payment_status": "paid"
            }
        )
        self.assertEqual(res_review.status_code, 200)
        self.assertEqual(res_review.get_json()["registration"]["status"], "approved")

        # Check in-app notification delivered to player
        res_notif = self.client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_notif.status_code, 200)
        notifs = res_notif.get_json()["notifications"]
        self.assertGreaterEqual(len(notifs), 1)
        self.assertIn("Registration Approved", notifs[0]["title"])

    # ----------------------------------------------------------------------
    # 6. ORDER OF PLAY API
    # ----------------------------------------------------------------------
    def test_06_order_of_play_endpoint(self):
        res = self.client.get(f"/api/v1/tournaments/{self.tournament_slug}/order-of-play")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["tournament"]["slug"], self.tournament_slug)
        self.assertIn("schedule", data)
        self.assertGreaterEqual(len(data["schedule"]), 1)

    # ----------------------------------------------------------------------
    # 7. STANDINGS & TOGGLE DRAW PUBLISH
    # ----------------------------------------------------------------------
    def test_07_standings_and_toggle_draw_publish(self):
        # Fetch standings
        res_standings = self.client.get(f"/api/v1/categories/{self.category_id}/standings")
        self.assertEqual(res_standings.status_code, 200)
        data = res_standings.get_json()
        self.assertTrue(data["success"])
        self.assertIn("participants", data)

        # Toggle publish draw
        owner_login = self._login("organizer")
        owner_token = owner_login["access_token"]

        res_pub = self.client.post(
            f"/api/v1/categories/{self.category_id}/toggle-publish",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        self.assertEqual(res_pub.status_code, 200)
        self.assertTrue(res_pub.get_json()["draw_published"])

    # ----------------------------------------------------------------------
    # 8. DEVICE REGISTRATION & NOTIFICATION PREFERENCES
    # ----------------------------------------------------------------------
    def test_08_device_registration_and_preferences(self):
        login_data = self._login("player1")
        token = login_data["access_token"]

        # Register device token
        res_dev = self.client.post(
            "/api/v1/devices/register",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "device_token": "fcm_test_token_abc123xyz456",
                "platform": "android",
                "device_name": "Google Pixel 8",
                "os_version": "Android 14"
            }
        )
        self.assertEqual(res_dev.status_code, 200)

        # Update notification preferences
        res_pref = self.client.put(
            "/api/v1/users/notification-preferences",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "notify_match_called": True,
                "notify_draw_published": False
            }
        )
        self.assertEqual(res_pref.status_code, 200)
        self.assertFalse(res_pref.get_json()["preferences"]["notify_draw_published"])

    # ----------------------------------------------------------------------
    # 9. USER ACCOUNT DELETION (GOOGLE PLAY / APPLE STORE COMPLIANCE)
    # ----------------------------------------------------------------------
    def test_09_user_delete_account(self):
        login_data = self._login("player1")
        token = login_data["access_token"]

        res_del = self.client.post(
            "/api/v1/users/delete_account",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

        # Attempt to login with deleted user -> fails
        res_fail = self._login("player1")
        self.assertFalse(res_fail["success"])


if __name__ == "__main__":
    unittest.main()
