"""
Unit and Integration Tests for Phase 8 and Phase 9:
Results, Qualified Leaderboard, Notifications Pipeline & Zero Dummy-Data Enforcement.
"""

import os
import tempfile
import unittest
from datetime import date, datetime
from app import create_app, db
from app.domain.models import (
    User, Player, Tournament, Category, Registration, Participant, Match,
    InAppNotification, UserNotificationPreferences, AcademyApplication
)
from app.services.notification_service import (
    send_notification,
    notify_registration_status,
    notify_academy_application_status,
    notify_draw_published,
    notify_match_called,
    NOTIFICATION_TYPE_MATCH_CALL,
    NOTIFICATION_TYPE_REGISTRATION_UPDATE,
)
from app.services.leaderboard import get_qualified_leaderboard_query


class Phase8And9NotificationsAndZeroDummyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-phase8-secret"
            JWT_SECRET_KEY = "test-phase8-jwt-secret"
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
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()

    def test_send_notification_and_preference_suppression(self):
        user = User(
            username="notif_test_user",
            email="notif@example.com",
            full_name="Notification Tester",
            role="player"
        )
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()

        # Send notification without custom preferences (default allowed)
        notif = send_notification(
            user_id=user.id,
            title="Test Alert",
            body="Test alert content",
            notification_type=NOTIFICATION_TYPE_REGISTRATION_UPDATE
        )
        db.session.commit()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "Test Alert")
        self.assertFalse(notif.is_read)

        # Set user preference to disable registration updates
        prefs = UserNotificationPreferences(
            user_id=user.id,
            notify_registration_updates=False,
            notify_match_called=True
        )
        db.session.add(prefs)
        db.session.commit()

        # Send notification of disabled type -> should return None (suppressed)
        suppressed = send_notification(
            user_id=user.id,
            title="Suppressed Alert",
            body="Should not be delivered",
            notification_type=NOTIFICATION_TYPE_REGISTRATION_UPDATE
        )
        self.assertIsNone(suppressed)

        # Send notification of enabled type -> should succeed
        allowed = send_notification(
            user_id=user.id,
            title="Allowed Alert",
            body="Match is called",
            notification_type=NOTIFICATION_TYPE_MATCH_CALL
        )
        db.session.commit()
        self.assertIsNotNone(allowed)

    def test_registration_and_academy_application_notifications(self):
        user = User(
            username="athlete_reg_notify",
            email="athlete_notif@example.com",
            full_name="Athlete Notif",
            role="player"
        )
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        player = Player(
            user_id=user.id,
            name="Athlete Notif",
            gender="Male",
            age_category="Open",
            dob=date(1995, 5, 5)
        )
        db.session.add(player)
        db.session.flush()

        tournament = Tournament(
            name="Open Slam 2026",
            url_slug="open-slam-notif-2026",
            status="setup",
            user_id=user.id,
            creator_name="Organizer"
        )
        db.session.add(tournament)
        db.session.flush()

        category = Category(
            tournament_id=tournament.id,
            name="Men's Singles",
            age_category="Open",
            format="single_elimination"
        )
        db.session.add(category)
        db.session.flush()

        reg = Registration(
            tournament_id=tournament.id,
            category_id=category.id,
            user_id=user.id,
            player_id=player.id,
            status="pending"
        )
        db.session.add(reg)
        db.session.commit()

        # Notify registration approved
        appr_notif = notify_registration_status(reg, "approved")
        db.session.commit()
        self.assertIsNotNone(appr_notif)
        self.assertIn("Approved", appr_notif.title)
        self.assertIn("Open Slam 2026", appr_notif.body)

        # Notify registration rejected
        rej_notif = notify_registration_status(reg, "rejected", reason="Category cap reached")
        db.session.commit()
        self.assertIsNotNone(rej_notif)
        self.assertIn("Category cap reached", rej_notif.body)

        # Academy application notification
        app_record = AcademyApplication(
            name="Vanguard Academy",
            applicant_id=user.id,
            contact_email="vanguard@example.com",
            status="PENDING",
            city="New York",
            state="NY",
            country="USA"
        )
        db.session.add(app_record)
        db.session.commit()

        acad_notif = notify_academy_application_status(app_record, "APPROVED")
        db.session.commit()
        self.assertIsNotNone(acad_notif)
        self.assertIn("Approved", acad_notif.title)
        self.assertIn("Vanguard Academy", acad_notif.body)

    def test_draw_published_and_match_called_notifications(self):
        user = User(
            username="player_draw_test",
            email="player_draw@example.com",
            full_name="Player Draw",
            role="player"
        )
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        player = Player(
            user_id=user.id,
            name="Player Draw",
            gender="Male",
            age_category="Open",
            dob=date(2000, 1, 1)
        )
        db.session.add(player)
        db.session.flush()

        tournament = Tournament(
            name="Championship Notif",
            url_slug="champ-notif-2026",
            status="setup",
            user_id=user.id
        )
        db.session.add(tournament)
        db.session.flush()

        category = Category(
            tournament_id=tournament.id,
            name="Men's Singles",
            age_category="Open",
            format="single_elimination"
        )
        db.session.add(category)
        db.session.flush()

        reg = Registration(
            tournament_id=tournament.id,
            category_id=category.id,
            user_id=user.id,
            player_id=player.id,
            status="approved"
        )
        db.session.add(reg)

        part1 = Participant(
            tournament_id=tournament.id,
            category_id=category.id,
            player_id=player.id,
            name="Player Draw"
        )
        db.session.add(part1)
        db.session.flush()

        match = Match(
            tournament_id=tournament.id,
            category_id=category.id,
            round=1,
            match_number=1,
            participant1_id=part1.id,
            court_name="Centre Court"
        )
        db.session.add(match)
        db.session.commit()

        # Notify draw published
        draw_notifs = notify_draw_published(category)
        db.session.commit()
        self.assertEqual(len(draw_notifs), 1)
        self.assertIn("Draws Published", draw_notifs[0].title)

        # Notify match called
        match_notifs = notify_match_called(match, court_name="Centre Court")
        db.session.commit()
        self.assertEqual(len(match_notifs), 1)
        self.assertIn("Match Called", match_notifs[0].title)
        self.assertIn("Centre Court", match_notifs[0].body)

    def test_qualified_leaderboard_query_zero_history_exclusion(self):
        # Unqualified player: 0 points, 0 matches played, no participation
        unqualified = Player(
            name="Ghost Unqualified Player",
            gender="Male",
            age_category="Open",
            total_points=0,
            matches_played=0
        )
        # Qualified player by points
        qualified_by_points = Player(
            name="Champion Star",
            gender="Male",
            age_category="Open",
            total_points=450,
            matches_played=3,
            matches_won=3
        )
        # Qualified player by tournament participation
        qualified_by_entry = Player(
            name="New Active Competitor",
            gender="Female",
            age_category="Under 18",
            total_points=0,
            matches_played=0
        )
        db.session.add_all([unqualified, qualified_by_points, qualified_by_entry])
        db.session.flush()

        part = Participant(
            tournament_id=1,
            name=qualified_by_entry.name,
            player_id=qualified_by_entry.id
        )
        db.session.add(part)
        db.session.commit()

        # Query all qualified players
        all_qualified = get_qualified_leaderboard_query().all()
        q_names = [p.name for p in all_qualified]

        self.assertIn("Champion Star", q_names)
        self.assertIn("New Active Competitor", q_names)
        self.assertNotIn("Ghost Unqualified Player", q_names)

        # Category and gender filtering
        u18_females = get_qualified_leaderboard_query(category_filter="Under 18", gender_filter="Female").all()
        u18_names = [p.name for p in u18_females]
        self.assertIn("New Active Competitor", u18_names)
        self.assertNotIn("Champion Star", u18_names)

    def test_zero_dummy_data_policy_blocks_dummy_generation(self):
        admin = User(
            username="admin_dummy_test",
            email="admin_dummy@example.com",
            full_name="Admin Dummy Test",
            role="admin"
        )
        admin.set_password("pass123")
        db.session.add(admin)
        db.session.flush()

        tournament = Tournament(
            name="Draft Cup 2026",
            url_slug="draft-cup-zero-dummy",
            user_id=admin.id,
            status="setup"
        )
        db.session.add(tournament)
        db.session.flush()

        category = Category(
            tournament_id=tournament.id,
            name="Team Event",
            age_category="Open",
            format="single_elimination",
            status="setup"
        )
        db.session.add(category)
        db.session.commit()

        admin_id = admin.id
        t_slug = tournament.url_slug
        cat_id = category.id

        # Log in as admin
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_id
            sess['_fresh'] = True

        # Attempt to post to add-dummy-players -> must return 400
        resp = self.client.post(
            f"/tournaments/{t_slug}/categories/{cat_id}/add-dummy-players",
            data={"count": 2},
            follow_redirects=False
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
