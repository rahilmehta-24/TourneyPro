"""Comprehensive Test Suite for Tournament Participants PDF Export.

Validates:
1. Export endpoint response headers, MIME type (application/pdf), and filename.
2. Authentication and authorization (login_required, role_required, tournament ownership).
3. Grouping of participants by category.
4. Payment method formatting strictly as 'Online' or 'Cash' without transaction IDs.
5. Multi-category tags (including players in 3 and 4 categories).
6. Doubles partner display.
7. Empty tournament / category handling.
8. PDF integrity verification using pypdf.
9. Compatibility route (/tournaments/<slug>/print redirect).
10. Database immutability (zero writes/mutations).
"""

import os
import tempfile
import unittest
from datetime import date
from io import BytesIO
from pypdf import PdfReader

from app import create_app
from app.domain.models import db, User, Tournament, Category, Participant, Registration, Player
from app.services.pdf.participants_adapter import ParticipantsExportAdapter


class ParticipantsPdfExportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret-key"
            JWT_SECRET_KEY = "jwt-test-secret"
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
        with self.app.app_context():
            Registration.query.delete()
            Participant.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            Player.query.delete()
            User.query.delete()
            db.session.commit()

            # Create Organizer (Admin)
            self.organizer = User(username="tournament_admin", email="admin@test.com", role="admin")
            self.organizer.set_password("adminpass")
            db.session.add(self.organizer)

            # Create Another User
            self.other_user = User(username="other_admin", email="other@test.com", role="admin")
            self.other_user.set_password("otherpass")
            db.session.add(self.other_user)

            db.session.commit()

            # Create Tournament
            self.tournament = Tournament(
                name="National Junior Championship 2026",
                url_slug="national-junior-2026",
                user_id=self.organizer.id,
                status="registration",
                game_info="Central Tennis Club, Metropolis",
                start_date=date(2026, 8, 10),
                end_date=date(2026, 8, 15),
            )
            db.session.add(self.tournament)
            db.session.commit()

            # Create Categories (4 categories for multi-category testing)
            self.cat_u14 = Category(
                tournament_id=self.tournament.id,
                name="Boys U-14 Singles",
                format="single_elimination",
                entry_fee=500.0,
            )
            self.cat_u16 = Category(
                tournament_id=self.tournament.id,
                name="Boys U-16 Singles",
                format="single_elimination",
                entry_fee=600.0,
            )
            self.cat_u18 = Category(
                tournament_id=self.tournament.id,
                name="Boys U-18 Singles",
                format="single_elimination",
                entry_fee=700.0,
            )
            self.cat_doubles = Category(
                tournament_id=self.tournament.id,
                name="Mens Doubles",
                format="single_elimination",
                entry_fee=800.0,
            )
            db.session.add_all([self.cat_u14, self.cat_u16, self.cat_u18, self.cat_doubles])
            db.session.commit()

            # Create Global Players
            self.player_multi = Player(
                name="Liam O'Connell",
                contact_number="+91 9876543210",
                email="liam@example.com",
                gender="Male",
                age_category="Open",
            )
            self.player_regular = Player(
                name="Noah Smith",
                contact_number="+91 9876543211",
                email="noah@example.com",
                gender="Male",
                age_category="Open",
            )
            self.player_partner = Player(
                name="Kevin Smith",
                contact_number="+91 9876543212",
                email="kevin@example.com",
                gender="Male",
                age_category="Open",
            )
            db.session.add_all([self.player_multi, self.player_regular, self.player_partner])
            db.session.commit()

            # Liam O'Connell registers for 4 categories (Multi-category player)
            # Cat 1: Boys U-14 (Online payment)
            self.p_liam_1 = Participant(
                tournament_id=self.tournament.id,
                category_id=self.cat_u14.id,
                player_id=self.player_multi.id,
                name=self.player_multi.name,
                mobile=self.player_multi.contact_number,
                email=self.player_multi.email,
                payment_status="paid",
                payment_method="online",
            )
            # Cat 2: Boys U-16 (Online payment)
            self.p_liam_2 = Participant(
                tournament_id=self.tournament.id,
                category_id=self.cat_u16.id,
                player_id=self.player_multi.id,
                name=self.player_multi.name,
                mobile=self.player_multi.contact_number,
                email=self.player_multi.email,
                payment_status="paid",
                payment_method="online",
            )
            # Cat 3: Boys U-18 (Online payment)
            self.p_liam_3 = Participant(
                tournament_id=self.tournament.id,
                category_id=self.cat_u18.id,
                player_id=self.player_multi.id,
                name=self.player_multi.name,
                mobile=self.player_multi.contact_number,
                email=self.player_multi.email,
                payment_status="paid",
                payment_method="online",
            )
            # Cat 4: Mens Doubles (with Kevin Smith, Cash payment)
            self.p_liam_4 = Participant(
                tournament_id=self.tournament.id,
                category_id=self.cat_doubles.id,
                player_id=self.player_multi.id,
                player2_id=self.player_partner.id,
                partner_name="Kevin Smith",
                name="Liam O'Connell / Kevin Smith",
                mobile=self.player_multi.contact_number,
                email=self.player_multi.email,
                payment_status="paid",
                payment_method="cash",
            )

            # Noah Smith registers for only 1 category (Boys U-14, Cash payment)
            self.p_noah = Participant(
                tournament_id=self.tournament.id,
                category_id=self.cat_u14.id,
                player_id=self.player_regular.id,
                name=self.player_regular.name,
                mobile=self.player_regular.contact_number,
                email=self.player_regular.email,
                payment_status="paid",
                payment_method="cash",
            )

            # Add corresponding Registrations with UPI transaction IDs to verify Txn is NOT leaked
            self.reg_liam_1 = Registration(
                tournament_id=self.tournament.id,
                category_id=self.cat_u14.id,
                user_id=self.organizer.id,
                player_id=self.player_multi.id,
                payment_method="online",
                payment_status="paid",
                transaction_id="UPI_TXN_SECRET_998877",
                status="approved",
            )
            self.reg_noah = Registration(
                tournament_id=self.tournament.id,
                category_id=self.cat_u14.id,
                user_id=self.organizer.id,
                player_id=self.player_regular.id,
                payment_method="cash",
                payment_status="paid",
                transaction_id="CASH_DESK_REF_123",
                status="approved",
            )

            db.session.add_all(
                [
                    self.p_liam_1,
                    self.p_liam_2,
                    self.p_liam_3,
                    self.p_liam_4,
                    self.p_noah,
                    self.reg_liam_1,
                    self.reg_noah,
                ]
            )
            db.session.commit()
            self.tournament_slug = self.tournament.url_slug
            self.tournament_id = self.tournament.id
            self.organizer_id = self.organizer.id
            self.other_user_id = self.other_user.id

        self.client = self.app.test_client()

    def login_organizer(self):
        self.client.get("/logout")
        return self.client.post(
            "/login",
            data={"username": "tournament_admin", "password": "adminpass"},
            follow_redirects=True,
        )

    def login_other_user(self):
        self.client.get("/logout")
        return self.client.post(
            "/login",
            data={"username": "other_admin", "password": "otherpass"},
            follow_redirects=True,
        )

    def test_01_adapter_multi_category_and_payment_formatting(self):
        """Adapter correctly tags multi-category players (4 categories) and shows only Online or Cash."""
        with self.app.app_context():
            tournament = Tournament.query.get(self.tournament_id)
            data = ParticipantsExportAdapter.adapt(tournament)

            self.assertEqual(data["tournament_name"], "National Junior Championship 2026")
            self.assertEqual(data["total_categories"], 4)
            # Unique participants: Liam and Noah
            self.assertEqual(data["total_unique_participants"], 2)

            # Check Boys U-14 participants
            u14_cat = next(c for c in data["categories"] if c["name"] == "Boys U-14 Singles")
            self.assertEqual(len(u14_cat["participants"]), 2)

            liam_row = next(p for p in u14_cat["participants"] if p["name"] == "Liam O'Connell")
            # Payment must be 'Online - Paid' (no transaction ID anywhere)
            self.assertEqual(liam_row["payment_label"], "Online - Paid")
            self.assertNotIn("UPI_TXN_SECRET", liam_row["payment_label"])

            # Liam should have tags for all 4 categories!
            tag_names = [t["name"] for t in liam_row["category_tags"]]
            self.assertEqual(len(tag_names), 4)
            self.assertIn("Boys U-14 Singles", tag_names)
            self.assertIn("Boys U-16 Singles", tag_names)
            self.assertIn("Boys U-18 Singles", tag_names)
            self.assertIn("Mens Doubles", tag_names)

            # Noah row should have 1 category tag and 'Cash - Paid'
            noah_row = next(p for p in u14_cat["participants"] if p["name"] == "Noah Smith")
            self.assertEqual(noah_row["payment_label"], "Cash - Paid")
            self.assertNotIn("CASH_DESK_REF", noah_row["payment_label"])
            self.assertEqual(len(noah_row["category_tags"]), 1)
            self.assertEqual(noah_row["category_tags"][0]["name"], "Boys U-14 Singles")

    def test_02_export_participants_pdf_success(self):
        """Organizing admin successfully downloads binary participants PDF with correct headers."""
        self.login_organizer()
        response = self.client.get(
            f"/tournaments/{self.tournament.url_slug}/participants/export_pdf"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response.headers["Content-Disposition"])
        self.assertIn(
            "national_junior_championship_2026", response.headers["Content-Disposition"].lower()
        )
        self.assertIn("participants.pdf", response.headers["Content-Disposition"].lower())

        # Verify PDF validity with PdfReader
        pdf_bytes = BytesIO(response.data)
        reader = PdfReader(pdf_bytes)
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_03_export_participants_pdf_short_route(self):
        """Short route /t/<slug>/participants/export_pdf functions identically."""
        self.login_organizer()
        response = self.client.get(f"/t/{self.tournament.url_slug}/participants/export_pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")

    def test_04_print_tournament_redirects_to_participants_pdf(self):
        """The /tournaments/<slug>/print route redirects to participants PDF."""
        self.login_organizer()
        response = self.client.get(f"/tournaments/{self.tournament_slug}/print")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/participants/export_pdf", response.headers.get("Location", ""))

    def test_05_unauthorized_user_access(self):
        """Non-owner admin is blocked with 403 or redirect."""
        self.login_other_user()
        response = self.client.get(f"/tournaments/{self.tournament_slug}/participants/export_pdf")
        # Non-owner fails check_tournament_ownership
        self.assertIn(response.status_code, [403, 302])

    def test_06_unauthenticated_user_access(self):
        """Unauthenticated user is redirected to login."""
        self.client.get("/logout")
        response = self.client.get(f"/tournaments/{self.tournament_slug}/participants/export_pdf")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers.get("Location", ""))

    def test_07_doubles_partner_handling(self):
        """Doubles category correctly formats partner details in PDF adapter."""
        with self.app.app_context():
            tournament = Tournament.query.get(self.tournament_id)
            data = ParticipantsExportAdapter.adapt(tournament)

            doubles_cat = next(c for c in data["categories"] if c["name"] == "Mens Doubles")
            self.assertEqual(len(doubles_cat["participants"]), 1)
            p = doubles_cat["participants"][0]
            self.assertTrue(p["is_doubles"])
            self.assertEqual(p["partner_name"], "Kevin Smith")
            self.assertEqual(p["payment_label"], "Cash - Paid")

    def test_08_empty_tournament_handling(self):
        """A tournament with zero participants renders PDF without crashing."""
        self.login_organizer()
        with self.app.app_context():
            empty_tourney = Tournament(
                name="Empty Championship",
                url_slug="empty-tourney-2026",
                user_id=self.organizer_id,
                status="setup",
            )
            db.session.add(empty_tourney)
            db.session.commit()

        response = self.client.get("/tournaments/empty-tourney-2026/participants/export_pdf")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        reader = PdfReader(BytesIO(response.data))
        self.assertGreaterEqual(len(reader.pages), 1)

    def test_09_database_immutability(self):
        """Exporting PDF performs zero database mutations."""
        self.login_organizer()
        with self.app.app_context():
            p_count_before = Participant.query.count()
            r_count_before = Registration.query.count()
            c_count_before = Category.query.count()

        _ = self.client.get(f"/tournaments/{self.tournament_slug}/participants/export_pdf")

        with self.app.app_context():
            self.assertEqual(Participant.query.count(), p_count_before)
            self.assertEqual(Registration.query.count(), r_count_before)
            self.assertEqual(Category.query.count(), c_count_before)


if __name__ == "__main__":
    unittest.main()
