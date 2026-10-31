import os
import tempfile
import unittest
from datetime import date
from io import BytesIO
from pypdf import PdfReader

from app import create_app
from app.domain.models import db, User, Tournament, Category, Match, Participant
from app.services.format_engine import get_format


class DrawPdfExportTestCase(unittest.TestCase):
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
            Match.query.delete()
            Participant.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            User.query.delete()
            db.session.commit()

            # Authorized Organizer
            self.organizer = User(username="organizer1", email="org1@test.com", role="admin")
            self.organizer.set_password("pass123")
            db.session.add(self.organizer)

            # Unauthorized Attacker Organizer
            self.attacker = User(username="attacker", email="attacker@test.com", role="admin")
            self.attacker.set_password("pass123")
            db.session.add(self.attacker)

            # Regular Player / User
            self.regular_user = User(username="player_user", email="player@test.com", role="user")
            self.regular_user.set_password("pass123")
            db.session.add(self.regular_user)

            db.session.commit()

            # Create standard tournament owned by self.organizer
            self.tournament = Tournament(
                name="Wimbledon Open Championship",
                url_slug="wimbledon-open-2026",
                user_id=self.organizer.id,
                status="in_progress",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 14),
            )
            db.session.add(self.tournament)
            db.session.commit()
            self.tournament_slug = self.tournament.url_slug
            self.tournament_id = self.tournament.id
            self.organizer_id = self.organizer.id

        self.client = self.app.test_client()

    def _login(self, username, password="pass123"):
        self.client.get("/logout")
        return self.client.post(
            "/login", data={"username": username, "password": password}, follow_redirects=True
        )

    def _create_single_elim_category(
        self,
        num_players,
        category_name="Men's Singles",
        is_doubles=False,
        custom_format="single_elimination",
    ):
        """Helper to create participants, start category, and generate authoritative saved draw."""
        with self.app.app_context():
            tourn = Tournament.query.filter_by(url_slug=self.tournament_slug).first()
            cat = Category(
                tournament_id=tourn.id,
                name=category_name,
                format=custom_format,
                status="setup",
                num_sets=3,
                games_per_set=6,
                start_date=date(2026, 7, 2),
                end_date=date(2026, 7, 10),
            )
            db.session.add(cat)
            db.session.commit()

            # Create participants
            participants = []
            for i in range(1, num_players + 1):
                p_name = f"Player {i}" if not is_doubles else f"Player {i}A / Player {i}B"
                part = Participant(
                    tournament_id=tourn.id,
                    category_id=cat.id,
                    name=p_name,
                    seed=i if i <= 8 else None,
                    manual_seed=i if i <= 4 else None,
                )
                db.session.add(part)
                participants.append(part)

            db.session.commit()

            # Generate and save draw via format engine
            fmt = get_format(cat.format)
            matches_data = fmt.generate(cat, participants)
            for m_data in matches_data:
                m_data["tournament_id"] = tourn.id
                m_data["category_id"] = cat.id
                match = Match(**m_data)
                db.session.add(match)

            cat.status = "in_progress"
            db.session.commit()

            return cat.id

    # -------------------------------------------------------------
    # 1. Standard Draw Sizes (8, 16, 32, 64, 128)
    # -------------------------------------------------------------
    def test_01_export_8_participant_draw(self):
        cat_id = self._create_single_elim_category(8, "Men's Singles 8")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "application/pdf")
        self.assertIn("attachment; filename=", res.headers.get("Content-Disposition"))
        self.assertIn("wimbledon_open_championship", res.headers.get("Content-Disposition"))

        # Verify PDF validity with pypdf
        reader = PdfReader(BytesIO(res.data))
        self.assertEqual(len(reader.pages), 1)
        # Verify page size is Landscape (width > height)
        box = reader.pages[0].mediabox
        self.assertGreater(box.width, box.height)

        text = reader.pages[0].extract_text()
        self.assertIn("Wimbledon Open Championship", text)
        self.assertIn("Men's Singles 8", text)
        self.assertIn("Player 1", text)
        self.assertIn("CHAMPION", text)

    def test_02_export_16_participant_draw(self):
        cat_id = self._create_single_elim_category(16, "Men's Singles 16")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        self.assertEqual(len(reader.pages), 1)
        text = reader.pages[0].extract_text()
        self.assertIn("Men's Singles 16", text)
        self.assertIn("Player 16", text)

    def test_03_export_32_participant_draw(self):
        cat_id = self._create_single_elim_category(32, "Men's Singles 32")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        self.assertEqual(len(reader.pages), 1)
        text = reader.pages[0].extract_text()
        self.assertIn("Men's Singles 32", text)
        self.assertIn("Player 32", text)
        self.assertIn("Round of 16", text)
        self.assertIn("Quarter-Finals", text)
        self.assertIn("Semi-Finals", text)
        self.assertIn("Final", text)

    def test_04_export_64_participant_draw_multipage(self):
        cat_id = self._create_single_elim_category(64, "Men's Singles 64")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        # 64 draw splits into 5 pages (4 quarters + Championship Stage)
        self.assertEqual(len(reader.pages), 5)
        # Check quarter page text and final page text
        page1_text = reader.pages[0].extract_text()
        self.assertIn("Quarter 1 of 4", page1_text)
        self.assertIn("Seeds 1–16", page1_text)

        page5_text = reader.pages[4].extract_text()
        self.assertIn("Championship Finals Stage", page5_text)
        self.assertIn("CHAMPION", page5_text)

    def test_05_export_128_participant_draw_multipage(self):
        cat_id = self._create_single_elim_category(128, "Men's Singles 128")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        # 128 draw splits into 9 pages (8 sections + Championship Stage)
        self.assertEqual(len(reader.pages), 9)
        page1_text = reader.pages[0].extract_text()
        self.assertIn("Section 1 of 8", page1_text)
        page9_text = reader.pages[8].extract_text()
        self.assertIn("Championship Finals Stage", page9_text)

    # -------------------------------------------------------------
    # 2. Non-Power-of-Two Draw & Bye Handling
    # -------------------------------------------------------------
    def test_06_non_power_of_two_draw_and_byes(self):
        # 6 players -> 8 bracket size with 2 Byes
        cat_id = self._create_single_elim_category(6, "Non-Power-of-Two 6 Draw")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        text = reader.pages[0].extract_text()
        self.assertIn("Bye", text)
        self.assertIn("Player 1", text)
        self.assertIn("Non-Power-of-Two 6 Draw", text)

    # -------------------------------------------------------------
    # 3. Doubles Representation
    # -------------------------------------------------------------
    def test_07_doubles_team_names(self):
        cat_id = self._create_single_elim_category(
            8, "Men's Doubles", is_doubles=True, custom_format="doubles_elimination"
        )
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        text = reader.pages[0].extract_text()
        self.assertIn("Player 1A / Player 1B", text)
        self.assertIn("Men's Doubles", text)

    # -------------------------------------------------------------
    # 4. Scores, Winners, and Champion
    # -------------------------------------------------------------
    def test_08_scores_and_completed_champion_display(self):
        cat_id = self._create_single_elim_category(8, "Completed Championship")
        with self.app.app_context():
            # Complete all matches up to the Final
            matches = (
                Match.query.filter_by(category_id=cat_id)
                .order_by(Match.round, Match.match_number)
                .all()
            )
            p1 = Participant.query.filter_by(category_id=cat_id, name="Player 1").first()

            # Set match results
            final_match = [m for m in matches if m.round == 3][0]
            final_match.score1 = "6-4, 6-3"
            final_match.score2 = "4-6, 3-6"
            final_match.winner_id = p1.id
            final_match.participant1_id = p1.id
            final_match.status = "completed"

            cat = Category.query.get(cat_id)
            cat.status = "completed"
            db.session.commit()

        self._login("organizer1")
        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        text = reader.pages[0].extract_text()
        self.assertIn("Player 1", text)
        self.assertIn("CHAMPION", text)
        self.assertIn("6-4", text)

    def test_09_in_progress_draw_does_not_fabricate_champion(self):
        cat_id = self._create_single_elim_category(8, "In Progress Championship")
        with self.app.app_context():
            # Final match has no winner yet
            matches = Match.query.filter_by(category_id=cat_id).all()
            for m in matches:
                m.status = "pending"
                m.winner_id = None
                m.score1 = None
                m.score2 = None
            db.session.commit()

        self._login("organizer1")
        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        reader = PdfReader(BytesIO(res.data))
        text = reader.pages[0].extract_text()
        self.assertIn("Tournament In Progress", text)

    # -------------------------------------------------------------
    # 5. Database Immutability Check (Strict Read-Only)
    # -------------------------------------------------------------
    def test_10_export_does_not_mutate_database(self):
        cat_id = self._create_single_elim_category(8, "Immutability Test")
        with self.app.app_context():
            matches_before = [
                (
                    m.id,
                    m.round,
                    m.match_number,
                    m.participant1_id,
                    m.participant2_id,
                    m.winner_id,
                    m.score1,
                    m.score2,
                    m.status,
                )
                for m in Match.query.filter_by(category_id=cat_id).order_by(Match.id).all()
            ]
            participants_before = [
                (p.id, p.name, p.seed, p.manual_seed)
                for p in Participant.query.filter_by(category_id=cat_id)
                .order_by(Participant.id)
                .all()
            ]

        self._login("organizer1")
        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            matches_after = [
                (
                    m.id,
                    m.round,
                    m.match_number,
                    m.participant1_id,
                    m.participant2_id,
                    m.winner_id,
                    m.score1,
                    m.score2,
                    m.status,
                )
                for m in Match.query.filter_by(category_id=cat_id).order_by(Match.id).all()
            ]
            participants_after = [
                (p.id, p.name, p.seed, p.manual_seed)
                for p in Participant.query.filter_by(category_id=cat_id)
                .order_by(Participant.id)
                .all()
            ]

            self.assertEqual(
                matches_before, matches_after, "Database matches were mutated during export!"
            )
            self.assertEqual(
                participants_before,
                participants_after,
                "Database participants were mutated during export!",
            )

    # -------------------------------------------------------------
    # 6. Security, Authorization, and Ownership Protection
    # -------------------------------------------------------------
    def test_11_unauthenticated_request_redirects_or_denies(self):
        cat_id = self._create_single_elim_category(8, "Auth Test")
        # Anonymous user (not logged in)
        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        # Should redirect to login
        self.assertIn(res.status_code, [302, 401])

    def test_12_cross_organizer_idor_blocked(self):
        cat_id = self._create_single_elim_category(8, "IDOR Protection Test")
        # Log in as attacker (different admin)
        self._login("attacker")
        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        # Forbidden
        self.assertEqual(res.status_code, 403)

    def test_13_regular_player_role_blocked(self):
        cat_id = self._create_single_elim_category(8, "Role RBAC Test")
        # Log in as normal user
        self._login("player_user")
        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 403)

    def test_14_invalid_tournament_or_category_returns_404(self):
        cat_id = self._create_single_elim_category(8, "404 Test")
        self._login("organizer1")

        # Invalid slug
        res1 = self.client.get(f"/tournaments/non-existent-slug/category/{cat_id}/export_pdf")
        self.assertEqual(res1.status_code, 404)

        # Invalid category ID
        res2 = self.client.get(f"/tournaments/{self.tournament_slug}/category/999999/export_pdf")
        self.assertEqual(res2.status_code, 404)

    def test_15_category_mismatched_tournament_returns_404(self):
        cat_id = self._create_single_elim_category(8, "Mismatch Test")
        with self.app.app_context():
            other_tourn = Tournament(
                name="Other Tournament",
                url_slug="other-tourn",
                user_id=self.organizer_id,
                status="in_progress",
            )
            db.session.add(other_tourn)
            db.session.commit()

        self._login("organizer1")
        # Request cat_id under other_tourn slug
        res = self.client.get(f"/tournaments/other-tourn/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 404)

    # -------------------------------------------------------------
    # 7. Unstarted / Missing Draw Handling
    # -------------------------------------------------------------
    def test_16_missing_draw_redirects_with_friendly_warning(self):
        with self.app.app_context():
            tourn = Tournament.query.filter_by(url_slug=self.tournament_slug).first()
            unstarted_cat = Category(
                tournament_id=tourn.id,
                name="Unstarted Category",
                format="single_elimination",
                status="setup",
            )
            db.session.add(unstarted_cat)
            db.session.commit()
            unstarted_id = unstarted_cat.id

        self._login("organizer1")
        res = self.client.get(
            f"/tournaments/{self.tournament_slug}/category/{unstarted_id}/export_pdf",
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"The tournament draw has not been generated yet", res.data)

    # -------------------------------------------------------------
    # 8. Regression Checks for CSV Exports & Download Performance
    # -------------------------------------------------------------
    def test_17_regression_matches_csv_export(self):
        cat_id = self._create_single_elim_category(8, "CSV Regression Test")
        res = self.client.get(
            f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_matches_csv"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type"))
        self.assertIn(
            "Round,Match Number,Status,Player 1,Player 2,Score,Winner", res.data.decode("utf-8")
        )

    def test_18_pdf_response_headers_and_etag_caching(self):
        cat_id = self._create_single_elim_category(8, "Header Performance Test")
        self._login("organizer1")

        res = self.client.get(f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf")
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/pdf", res.headers.get("Content-Type"))
        self.assertIn("Content-Length", res.headers)
        self.assertEqual(int(res.headers["Content-Length"]), len(res.data))
        self.assertIn("ETag", res.headers)
        etag = res.headers["ETag"]
        self.assertIn("private, max-age=120", res.headers.get("Cache-Control", ""))

        # Conditional GET with ETag should return 304 Not Modified instantly
        res_304 = self.client.get(
            f"/tournaments/{self.tournament_slug}/category/{cat_id}/export_pdf",
            headers={"If-None-Match": etag},
        )
        self.assertEqual(res_304.status_code, 304)
        self.assertEqual(len(res_304.data), 0)

    def test_19_in_memory_pdf_service_cache(self):
        from app.services.pdf.pdf_generator import DrawPdfService

        test_key = "test_cache_key_123"
        fake_bytes = b"%PDF-1.4 test binary data"

        DrawPdfService.clear_cache()
        self.assertIsNone(DrawPdfService.get_cached_pdf(test_key))

        DrawPdfService.set_cached_pdf(test_key, fake_bytes)
        cached = DrawPdfService.get_cached_pdf(test_key)
        self.assertEqual(cached, fake_bytes)

        DrawPdfService.clear_cache()
        self.assertIsNone(DrawPdfService.get_cached_pdf(test_key))

    def test_20_draw_with_byes_uneven_multipage_rendering(self):
        # 5-round draw with 31 matches in round 1 (e.g. 58 participants with byes)
        from app.services.pdf.draw_adapter import DrawExportAdapter
        from app.services.pdf.pdf_generator import DrawPdfService

        with self.app.app_context():
            tourn = Tournament.query.filter_by(url_slug=self.tournament_slug).first()
            cat = Category(
                tournament_id=tourn.id,
                name="58-Player Uneven Draw",
                format="single_elimination",
                status="in_progress",
            )
            db.session.add(cat)
            db.session.commit()

            # Create matches: R1: 31, R2: 15, R3: 7, R4: 3, R5: 1
            counts = {1: 31, 2: 15, 3: 7, 4: 3, 5: 1}
            for r_num, count in counts.items():
                for m_num in range(1, count + 1):
                    m = Match(
                        tournament_id=tourn.id,
                        category_id=cat.id,
                        round=r_num,
                        match_number=m_num,
                        bracket_type="main",
                        match_type="knockout",
                        status="pending",
                    )
                    db.session.add(m)
            db.session.commit()

            data = DrawExportAdapter.adapt(tourn, cat)
            self.assertEqual(len(data["pages"]), 3)
            self.assertEqual(data["pages"][0]["section_badge"], "Top Half Bracket")
            self.assertEqual(data["pages"][1]["section_badge"], "Bottom Half Bracket")
            self.assertEqual(data["pages"][2]["section_badge"], "Championship Finals Stage")

            with self.app.test_request_context():
                pdf_buf = DrawPdfService.render_draw_pdf(data)
                self.assertGreater(len(pdf_buf.getvalue()), 5000)
