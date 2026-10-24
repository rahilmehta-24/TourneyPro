"""Comprehensive Test Suite for Order of Play PDF Export.

Validates:
1. Basic Order of Play PDF generation and response headers.
2. Filter by date.
3. Filter by court.
4. Filter by session (Day vs Evening).
5. Team League matches with child rubbers.
6. Completed matches score display.
7. Empty schedule rendering.
8. 404 for nonexistent tournament.
9. Legacy ?export=1 redirect.
10. Database immutability (zero writes/updates).
"""

import os
import tempfile
import unittest
from datetime import date, datetime
from io import BytesIO
from pypdf import PdfReader

from app import create_app
from app.domain.models import db, User, Tournament, Category, Match, Participant, Group


class OrderOfPlayPdfExportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret-key'
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
            Group.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            User.query.delete()
            db.session.commit()

            self.organizer = User(username='organizer1', email='org1@test.com', role='admin')
            self.organizer.set_password('pass123')
            db.session.add(self.organizer)
            db.session.commit()

            self.tournament = Tournament(
                name="Wimbledon Championship",
                url_slug="wimbledon-2026",
                user_id=self.organizer.id,
                status="in_progress",
                court_names="Court 1, Court 2",
                num_courts=2,
                court_operating_start="09:00",
                court_operating_end="19:00",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 7)
            )
            db.session.add(self.tournament)
            db.session.commit()

            self.category = Category(
                tournament_id=self.tournament.id,
                name="Men's Singles",
                format="single_elimination",
                status="in_progress",
                num_sets=3,
                games_per_set=6
            )
            db.session.add(self.category)
            db.session.commit()

            self.p1 = Participant(tournament_id=self.tournament.id, category_id=self.category.id, name="Novak Djokovic", seed=1, manual_seed=1)
            self.p2 = Participant(tournament_id=self.tournament.id, category_id=self.category.id, name="Carlos Alcaraz", seed=2, manual_seed=2)
            self.p3 = Participant(tournament_id=self.tournament.id, category_id=self.category.id, name="Jannik Sinner", seed=3, manual_seed=3)
            self.p4 = Participant(tournament_id=self.tournament.id, category_id=self.category.id, name="Daniil Medvedev", seed=4, manual_seed=4)
            db.session.add_all([self.p1, self.p2, self.p3, self.p4])
            db.session.commit()

            # Schedule matches on Day 1 (2026-07-01)
            # Court 1, Day session (09:30)
            self.m1 = Match(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                round=1,
                match_number=1,
                match_type='knockout',
                participant1_id=self.p1.id,
                participant2_id=self.p4.id,
                court_name="Court 1",
                scheduled_time=datetime(2026, 7, 1, 9, 30),
                status="completed",
                winner_id=self.p1.id,
                score1="6-4, 6-3",
                score2="4-6, 3-6"
            )
            # Court 1, Evening session (17:00, NB)
            self.m2 = Match(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                round=1,
                match_number=2,
                match_type='knockout',
                participant1_id=self.p2.id,
                participant2_id=self.p3.id,
                court_name="Court 1",
                scheduled_time=datetime(2026, 7, 1, 17, 0),
                is_not_before=True,
                status="in_progress"
            )
            # Court 2, Day session (10:00)
            self.m3 = Match(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                round=2,
                match_number=1,
                match_type='knockout',
                participant1_id=self.p1.id,
                participant2_id=self.p2.id,
                court_name="Court 2",
                scheduled_time=datetime(2026, 7, 1, 10, 0),
                status="pending"
            )
            # Match on Day 2 (2026-07-02)
            self.m4 = Match(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                round=2,
                match_number=2,
                match_type='knockout',
                participant1_id=self.p3.id,
                participant2_id=self.p4.id,
                court_name="Court 1",
                scheduled_time=datetime(2026, 7, 2, 11, 0),
                status="pending"
            )
            db.session.add_all([self.m1, self.m2, self.m3, self.m4])
            db.session.commit()
            self.tournament_slug = self.tournament.url_slug
            self.tournament_id = self.tournament.id

        self.client = self.app.test_client()

    def test_01_export_order_of_play_pdf_success(self):
        """Test default export returns a valid PDF with correct headers and Content-Disposition."""
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/pdf")
        self.assertIn("attachment; filename=", res.headers.get("Content-Disposition", ""))
        self.assertIn("tourneypro_wimbledon_championship_order_of_play_", res.headers.get("Content-Disposition"))

        pdf_reader = PdfReader(BytesIO(res.data))
        self.assertGreaterEqual(len(pdf_reader.pages), 1)

        # Verify page size is A4 portrait (595 x 842 pt ± 2pt)
        page0 = pdf_reader.pages[0]
        mb = page0.mediabox
        self.assertAlmostEqual(float(mb.width), 595.27, delta=5.0)
        self.assertAlmostEqual(float(mb.height), 841.89, delta=5.0)

        # Extract text content and verify key strings
        text = page0.extract_text()
        self.assertIn("Wimbledon Championship", text)
        self.assertIn("ORDER OF PLAY", text)
        self.assertIn("Court 1", text)
        self.assertIn("Novak Djokovic", text)

    def test_02_export_order_of_play_date_filtering(self):
        """Test filtering by date only exports matches for that specific date."""
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf?date=2026-07-02")
        self.assertEqual(res.status_code, 200)
        self.assertIn("20260702", res.headers.get("Content-Disposition", ""))

        pdf_reader = PdfReader(BytesIO(res.data))
        text = "".join(p.extract_text() for p in pdf_reader.pages)
        self.assertIn("02 July 2026", text)
        self.assertIn("Court 1", text)
        # Match 4 is at 11:00 on Day 2
        self.assertIn("11:00", text)

    def test_03_export_order_of_play_court_filtering(self):
        """Test filtering by court only includes matches from that court."""
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf?date=2026-07-01&court=Court+2")
        self.assertEqual(res.status_code, 200)
        self.assertIn("court_2", res.headers.get("Content-Disposition", ""))

        pdf_reader = PdfReader(BytesIO(res.data))
        text = "".join(p.extract_text() for p in pdf_reader.pages)
        self.assertIn("Court 2", text)
        self.assertNotIn("Court 1", text)

    def test_04_export_order_of_play_session_filtering(self):
        """Test filtering by session (day vs evening) includes only target session matches."""
        # Evening session on 2026-07-01 (Match 2 at 17:00)
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf?date=2026-07-01&session=evening")
        self.assertEqual(res.status_code, 200)
        self.assertIn("evening", res.headers.get("Content-Disposition", ""))

        pdf_reader = PdfReader(BytesIO(res.data))
        text = "".join(p.extract_text() for p in pdf_reader.pages)
        self.assertIn("17:00", text)
        self.assertNotIn("09:30", text)

    def test_05_export_team_league_tie_with_rubbers(self):
        """Test team league parent match with child rubbers renders cleanly."""
        with self.app.app_context():
            cat = Category(
                tournament_id=self.tournament_id,
                name="Club League",
                format="group_stage",
                has_group_stage=True,
                status="in_progress"
            )
            db.session.add(cat)
            db.session.flush()

            grp = Group(category_id=cat.id, name="Group Alpha")
            db.session.add(grp)
            db.session.flush()

            t1 = Participant(tournament_id=self.tournament_id, category_id=cat.id, group_id=grp.id, name="Dragons Team")
            t2 = Participant(tournament_id=self.tournament_id, category_id=cat.id, group_id=grp.id, name="Phoenix Team")
            db.session.add_all([t1, t2])
            db.session.flush()

            parent = Match(
                tournament_id=self.tournament_id,
                category_id=cat.id,
                group_id=grp.id,
                participant1_id=t1.id,
                participant2_id=t2.id,
                match_type='group_stage',
                round=1,
                match_number=10,
                court_name="Court 1",
                scheduled_time=datetime(2026, 7, 3, 10, 0),
                status="in_progress"
            )
            db.session.add(parent)
            db.session.flush()

            r1 = Match(
                tournament_id=self.tournament_id,
                category_id=cat.id,
                group_id=grp.id,
                parent_match_id=parent.id,
                round=1,
                match_number=10,
                rubber_type='singles',
                rubber_number=1,
                court_name="Court 1",
                scheduled_time=datetime(2026, 7, 3, 10, 0),
                status="completed",
                score1="6-3, 6-4",
                score2="3-6, 4-6"
            )
            db.session.add(r1)
            db.session.commit()

        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf?date=2026-07-03")
        self.assertEqual(res.status_code, 200)

        pdf_reader = PdfReader(BytesIO(res.data))
        text = "".join(p.extract_text() for p in pdf_reader.pages)
        self.assertIn("Dragons Team", text)
        self.assertIn("Phoenix Team", text)
        self.assertIn("Singles", text)

    def test_06_completed_matches_display_scores(self):
        """Test that completed match displays recorded scoreline."""
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf?date=2026-07-01")
        self.assertEqual(res.status_code, 200)

        pdf_reader = PdfReader(BytesIO(res.data))
        text = "".join(p.extract_text() for p in pdf_reader.pages)
        self.assertIn("6-4, 6-3", text)

    def test_07_empty_order_of_play_returns_valid_pdf(self):
        """Test that a date with no scheduled matches returns a valid PDF with empty notice."""
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf?date=2026-07-05")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/pdf")

        pdf_reader = PdfReader(BytesIO(res.data))
        self.assertEqual(len(pdf_reader.pages), 1)
        text = pdf_reader.pages[0].extract_text()
        self.assertIn("No matches scheduled for this date or selection", text)

    def test_08_invalid_tournament_slug_returns_404(self):
        """Test nonexistent tournament returns 404."""
        res = self.client.get("/tournaments/nonexistent-tournament-999/order-of-play/export_pdf")
        self.assertEqual(res.status_code, 404)

    def test_09_legacy_export_query_param_redirects(self):
        """Test that legacy order-of-play?export=1 redirects to export_order_of_play_pdf."""
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play?export=1&date=2026-07-01")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/order-of-play/export_pdf", res.headers.get("Location", ""))

    def test_10_database_immutability(self):
        """Test that Order of Play export is strictly read-only and does not mutate any records."""
        with self.app.app_context():
            matches_before = [(m.id, m.status, m.winner_id, m.score1, m.score2, m.court_name, m.scheduled_time) for m in Match.query.all()]
            participants_before = [(p.id, p.name, p.seed) for p in Participant.query.all()]
            t = db.session.get(Tournament, self.tournament_id)
            tourn_before = (t.name, t.status)

        # Call export endpoint
        res = self.client.get(f"/tournaments/{self.tournament_slug}/order-of-play/export_pdf")
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            matches_after = [(m.id, m.status, m.winner_id, m.score1, m.score2, m.court_name, m.scheduled_time) for m in Match.query.all()]
            participants_after = [(p.id, p.name, p.seed) for p in Participant.query.all()]
            t = db.session.get(Tournament, self.tournament_id)
            tourn_after = (t.name, t.status)

        self.assertEqual(matches_before, matches_after)
        self.assertEqual(participants_before, participants_after)
        self.assertEqual(tourn_before, tourn_after)


if __name__ == '__main__':
    unittest.main()
