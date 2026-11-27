import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from app import create_app, db
from app.domain.models import (
    User, Player, Tournament, Category, Registration
)
from app.services.email_service import (
    send_email,
    notify_registration_created,
    notify_registration_status_update,
)


class EmailNotificationsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)
        cls.upload_dir = tempfile.mkdtemp()

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-email-secret-key-32-chars-minimum-safe"
            JWT_SECRET_KEY = "test-email-jwt-secret-key-32-chars-minimum-safe"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = cls.upload_dir
            MAIL_SUPPRESS_SEND = True
            MAIL_DEFAULT_SENDER = "The Baseline Society <no-reply@baselinesociety.com>"
            SUPERADMIN_EMAIL = "superadmin@baselinesociety.com"

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()
        if os.path.exists(cls.db_path):
            os.unlink(cls.db_path)

    def setUp(self):
        db.session.rollback()

    def _create_base_tournament(self):
        """Helper to create tournament and organizer cleanly."""
        organizer = User(
            username=f"org_{os.urandom(4).hex()}",
            email=f"org_{os.urandom(4).hex()}@example.com",
            full_name="Tournament Director Jane",
            phone_number="+91 9876543210",
            role="organizer",
            password_hash="fake",
        )
        db.session.add(organizer)
        db.session.flush()

        tournament = Tournament(
            name="Spring Championship 2026",
            url_slug=f"spring-{os.urandom(4).hex()}",
            user_id=organizer.id,
            creator_name="Director Jane",
            status="registration",
            is_published=True,
        )
        db.session.add(tournament)
        db.session.flush()

        category = Category(
            tournament_id=tournament.id,
            name="Men's Open Singles",
            entry_fee=1200.0,
            status="setup",
            is_registration_open=True,
            registration_status="OPEN",
        )
        db.session.add(category)
        db.session.commit()
        return tournament, category, organizer

    def test_send_email_dev_mode(self):
        """Verify send_email runs safely in dev/suppressed mode without errors."""
        res = send_email(
            to_email="testplayer@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>",
            reply_to="organizer@example.com",
            async_send=False,
        )
        self.assertTrue(res)

    @patch("smtplib.SMTP")
    def test_send_email_smtp_delivery(self, mock_smtp_class):
        """Verify real SMTP transport construction, Reply-To header, and TLS handshake."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        # Temporarily enable SMTP configuration
        self.app.config["MAIL_SUPPRESS_SEND"] = False
        self.app.config["MAIL_SERVER"] = "smtp.example.com"
        self.app.config["MAIL_PORT"] = 587
        self.app.config["MAIL_USE_TLS"] = True
        self.app.config["MAIL_USERNAME"] = "mailer@example.com"
        self.app.config["MAIL_PASSWORD"] = "secret"

        try:
            res = send_email(
                to_email=["player@example.com"],
                subject="Winter Tennis Open Confirmation",
                html_body="<h1>Welcome</h1>",
                reply_to="organizer@example.com",
                async_send=False,
            )
            self.assertTrue(res)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("mailer@example.com", "secret")
            mock_server.send_message.assert_called_once()

            sent_msg = mock_server.send_message.call_args[0][0]
            self.assertEqual(sent_msg["To"], "player@example.com")
            self.assertEqual(sent_msg["Reply-To"], "organizer@example.com")
            self.assertEqual(sent_msg["Subject"], "Winter Tennis Open Confirmation")
        finally:
            self.app.config["MAIL_SUPPRESS_SEND"] = True
            self.app.config["MAIL_SERVER"] = None

    def test_notify_registration_created_three_recipients(self):
        """
        Verify that notify_registration_created dispatches:
        1. Player confirmation email (with organizer as Reply-To).
        2. Organizer alert email (with player as Reply-To).
        3. Superadmin system audit email.
        """
        tournament, category, organizer = self._create_base_tournament()

        # Create Player User & Profile
        player_user = User(
            username=f"player_{os.urandom(4).hex()}",
            email=f"dan_{os.urandom(4).hex()}@example.com",
            full_name="Dan Player",
            role="user",
            password_hash="fake",
        )
        db.session.add(player_user)
        db.session.flush()

        player = Player(
            user_id=player_user.id,
            name="Dan Player",
            email=player_user.email,
            contact_number="+91 9123456789",
            gender="Male",
        )
        db.session.add(player)
        db.session.flush()

        # Create Registration
        registration = Registration(
            tournament_id=tournament.id,
            category_id=category.id,
            user_id=player_user.id,
            player_id=player.id,
            amount_due=1200.0,
            status="pending",
            payment_status="paid",
            payment_method="online",
        )
        db.session.add(registration)
        db.session.commit()

        # Spy on send_email
        with patch("app.services.email_service.send_email", wraps=send_email) as mock_send:
            res = notify_registration_created(registration.id, async_send=False)
            self.assertEqual(res["status"], "success")

            # Check that 3 emails were dispatched
            self.assertEqual(mock_send.call_count, 3)

            calls = mock_send.call_args_list

            # Call 1: To Player (with Reply-To: organizer and masked From: confirmation@thebaselinesociety.com)
            player_call = calls[0]
            self.assertEqual(player_call.kwargs["to_email"], player_user.email)
            self.assertEqual(player_call.kwargs["reply_to"], organizer.email)
            self.assertIn("confirmation@thebaselinesociety.com", player_call.kwargs["from_sender"])
            self.assertIn(organizer.full_name, player_call.kwargs["from_sender"])
            self.assertIn("Registration Confirmed", player_call.kwargs["subject"])
            self.assertIn("The Baseline Society", player_call.kwargs["html_body"])
            self.assertNotIn("TourneyPro Platform", player_call.kwargs["html_body"])

            # Call 2: To Organizer (with Reply-To: player)
            org_call = calls[1]
            self.assertEqual(org_call.kwargs["to_email"], organizer.email)
            self.assertEqual(org_call.kwargs["reply_to"], player_user.email)
            self.assertIn("New Registration", org_call.kwargs["subject"])
            self.assertIn("Dan Player", org_call.kwargs["html_body"])

            # Call 3: To Superadmin
            admin_call = calls[2]
            admin_recips = admin_call.kwargs["to_email"]
            self.assertTrue(
                any("superadmin" in r for r in admin_recips)
            )
            self.assertIn("System Audit", admin_call.kwargs["subject"])

    def test_notify_registration_status_update_email(self):
        """Verify registration status update (approved/rejected) sends email to player."""
        tournament, category, organizer = self._create_base_tournament()

        player_user = User(
            username=f"player_stat_{os.urandom(4).hex()}",
            email=f"dan_stat_{os.urandom(4).hex()}@example.com",
            password_hash="fake",
        )
        db.session.add(player_user)
        db.session.flush()

        player = Player(
            user_id=player_user.id,
            name="Status Dan",
            email=player_user.email,
            contact_number="+91 9999999999",
            gender="Male",
        )
        db.session.add(player)
        db.session.flush()

        reg = Registration(
            tournament_id=tournament.id,
            category_id=category.id,
            user_id=player_user.id,
            player_id=player.id,
            status="pending",
        )
        db.session.add(reg)
        db.session.commit()

        with patch("app.services.email_service.send_email", wraps=send_email) as mock_send:
            ok = notify_registration_status_update(reg.id, "approved", async_send=False)
            self.assertTrue(ok)
            mock_send.assert_called_once()
            call = mock_send.call_args
            self.assertEqual(call.kwargs["to_email"], player_user.email)
            self.assertIn("Approved", call.kwargs["subject"])

    def test_mobile_api_registration_mandatory_email_and_mobile(self):
        """Verify mobile API rejects registration if email or mobile are missing."""
        from flask_jwt_extended import create_access_token

        tournament, category, organizer = self._create_base_tournament()

        # Create user without email/mobile
        bare_user = User(
            username=f"bare_{os.urandom(4).hex()}",
            email="",
            password_hash="fake",
        )
        db.session.add(bare_user)
        db.session.flush()

        bare_player = Player(
            user_id=bare_user.id,
            name="Bare Player",
            email=None,
            contact_number=None,
        )
        db.session.add(bare_player)
        db.session.commit()

        token = create_access_token(identity=str(bare_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Missing email & mobile
        resp = self.client.post(
            f"/api/v1/tournaments/{tournament.url_slug}/register",
            headers=headers,
            json={
                "category_id": category.id,
                "player_id": bare_player.id,
            },
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Email", data["message"])

        # 2. Provide email but missing mobile
        resp = self.client.post(
            f"/api/v1/tournaments/{tournament.url_slug}/register",
            headers=headers,
            json={
                "category_id": category.id,
                "player_id": bare_player.id,
                "email": "bare@example.com",
            },
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("Mobile", data["message"])

        # 3. Provide both valid email and mobile -> success
        with patch("app.services.email_service.notify_registration_created") as mock_notif:
            resp = self.client.post(
                f"/api/v1/tournaments/{tournament.url_slug}/register",
                headers=headers,
                json={
                    "category_id": category.id,
                    "player_id": bare_player.id,
                    "email": "bare@example.com",
                    "mobile": "+91 9988776655",
                },
            )
            self.assertEqual(resp.status_code, 201)
            mock_notif.assert_called_once()

    def test_web_registration_mandatory_fields_and_notification(self):
        """Verify web tournament registration mandates email/mobile and triggers notification."""
        tournament, category, organizer = self._create_base_tournament()

        # 1. Post without email -> redirects with error flash
        resp = self.client.post(
            f"/tournaments/{tournament.url_slug}/register",
            data={
                "category_id": [category.id],
                "guest_name": "Web Guest",
                "guest_age": "25",
                "guest_gender": "Male",
                "guest_mobile": "+91 9876501234",
                "guest_email": "",  # Empty email
                "payment_method": "online",
                "transaction_id": "TXN-WEB-12345",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Email Address is required", resp.data)

        # 2. Post without mobile -> redirects with error flash
        resp = self.client.post(
            f"/tournaments/{tournament.url_slug}/register",
            data={
                "category_id": [category.id],
                "guest_name": "Web Guest",
                "guest_age": "25",
                "guest_gender": "Male",
                "guest_mobile": "",  # Empty mobile
                "guest_email": "webguest@example.com",
                "payment_method": "online",
                "transaction_id": "TXN-WEB-12345",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Mobile Number is required", resp.data)

        # 3. Post with both email and mobile -> success & notification dispatched
        with patch("app.services.email_service.notify_registration_created") as mock_notif:
            resp = self.client.post(
                f"/tournaments/{tournament.url_slug}/register",
                data={
                    "category_id": [category.id],
                    "guest_name": "Web Guest",
                    "guest_age": "25",
                    "guest_gender": "Male",
                    "guest_mobile": "+91 9876501234",
                    "guest_email": "webguest@example.com",
                    "payment_method": "online",
                    "transaction_id": "TXN-WEB-12345",
                },
                follow_redirects=True,
            )
            self.assertEqual(resp.status_code, 200)
            mock_notif.assert_called_once()



if __name__ == "__main__":
    unittest.main()
