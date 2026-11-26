import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from app import create_app
from app.domain.models import (
    db,
    User,
    Tournament,
    Category,
    Participant,
    Player,
    Registration,
    ParticipantImportBatch,
    TournamentSettings,
)
from flask_jwt_extended import create_access_token


class FlexibleRegistrationAndBulkImportTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret-key-32-bytes-minimum-length"
            JWT_SECRET_KEY = "jwt-test-secret-key-32-bytes-min"
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
        db.session.rollback()
        self.client = self.app.test_client()
        ParticipantImportBatch.query.delete()
        Registration.query.delete()
        Participant.query.delete()
        Player.query.delete()
        Category.query.delete()
        TournamentSettings.query.delete()
        Tournament.query.delete()
        User.query.delete()
        db.session.commit()

        # Create Organizer (admin)
        self.organizer = User(
            username="organizer1",
            email="organizer1@example.com",
            role="admin",
            full_name="Tournament Organizer",
            profile_completed=True,
            completion_percentage=100,
        )
        self.organizer.set_password("SecurePass123!")
        db.session.add(self.organizer)

        # Create Player user
        self.player_user = User(
            username="player1",
            email="player1@example.com",
            role="user",
            full_name="Player One",
            profile_completed=True,
            completion_percentage=100,
        )
        self.player_user.set_password("SecurePass123!")
        db.session.add(self.player_user)

        # Create Second Organizer (for cross-tournament tests)
        self.organizer2 = User(
            username="organizer2",
            email="organizer2@example.com",
            role="admin",
            full_name="Second Organizer",
            profile_completed=True,
            completion_percentage=100,
        )
        self.organizer2.set_password("SecurePass123!")
        db.session.add(self.organizer2)

        db.session.commit()

        # Create Player Profile
        self.player_profile = Player(
            user_id=self.player_user.id,
            name="Player One",
            email="player1@example.com",
            contact_number="9876543210",
            gender="Male",
            age_category="Open",
            profile_status="complete",
        )
        db.session.add(self.player_profile)
        db.session.commit()

    def tearDown(self):
        db.session.rollback()
        db.session.remove()

    def _login(self, username="organizer1", password="SecurePass123!"):
        self.client.get("/logout", follow_redirects=True)
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def _create_sample_tournament(self, format_status="NOT_DECIDED", reg_status="OPEN"):
        tourn = Tournament(
            user_id=self.organizer.id,
            creator_name=self.organizer.full_name,
            name="Open Championship",
            url_slug="open-championship",
            format_status=format_status,
            registration_status=reg_status,
            is_published=True,
            start_date=datetime.utcnow().date(),
            end_date=(datetime.utcnow() + timedelta(days=2)).date(),
        )
        db.session.add(tourn)
        db.session.flush()

        cat1 = Category(
            tournament_id=tourn.id,
            name="Men's Singles",
            format=None if format_status == "NOT_DECIDED" else "single_elimination",
            format_status=format_status,
            registration_status="OPEN",
            is_registration_open=True,
            entry_fee=0.0,
            max_participants=16,
        )
        cat2 = Category(
            tournament_id=tourn.id,
            name="Men's Doubles",
            format=None if format_status == "NOT_DECIDED" else "doubles_elimination",
            format_status=format_status,
            registration_status="OPEN",
            is_registration_open=True,
            entry_fee=0.0,
            max_participants=8,
        )
        db.session.add(cat1)
        db.session.add(cat2)
        db.session.commit()
        return tourn, cat1, cat2

    # -------------------------------------------------------------------------
    # 1. Tournament creation without a finalized playing format
    # -------------------------------------------------------------------------
    def test_01_tournament_creation_without_finalized_format(self):
        self._login("organizer1")
        resp = self.client.post(
            "/tournaments/new",
            data={
                "name": "Summer Masters",
                "format_status": "NOT_DECIDED",
                "registration_status": "OPEN",
                "category_names_csv": "Open Singles, Veterans 40+",
                "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "duration_days": 2,
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        tourn = Tournament.query.filter_by(name="Summer Masters").first()
        self.assertIsNotNone(tourn)
        self.assertEqual(tourn.format_status, "NOT_DECIDED")
        self.assertEqual(tourn.registration_status, "OPEN")
        self.assertEqual(len(tourn.categories), 2)
        for cat in tourn.categories:
            self.assertIsNone(cat.format)
            self.assertEqual(cat.format_status, "NOT_DECIDED")

    # -------------------------------------------------------------------------
    # 2. Registration opening while format is undecided
    # -------------------------------------------------------------------------
    def test_02_registration_opening_while_format_undecided(self):
        tourn, cat1, _ = self._create_sample_tournament(format_status="NOT_DECIDED")
        self._login("player1")

        # View registration page
        resp = self.client.get(f"/t/{tourn.url_slug}/register")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"To Be Announced (TBA)", resp.data)

        # Register
        resp = self.client.post(
            f"/t/{tourn.url_slug}/register",
            data={"category_id": [cat1.id], "payment_method": "free"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        reg = Registration.query.filter_by(tournament_id=tourn.id, category_id=cat1.id).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.user_id, self.player_user.id)

    # -------------------------------------------------------------------------
    # 3. Registration for multiple categories
    # -------------------------------------------------------------------------
    def test_03_registration_for_multiple_categories(self):
        tourn, cat1, cat2 = self._create_sample_tournament()
        self._login("player1")

        resp = self.client.post(
            f"/t/{tourn.url_slug}/register",
            data={
                "category_id": [cat1.id, cat2.id],
                "payment_method": "free",
                f"partner_name_{cat2.id}": "Carlos Alcaraz",
                f"partner_age_{cat2.id}": "21",
                f"partner_mobile_{cat2.id}": "9876543299",
                f"partner_gender_{cat2.id}": "Male",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        regs = Registration.query.filter_by(
            tournament_id=tourn.id, user_id=self.player_user.id
        ).all()
        self.assertEqual(len(regs), 2)

    # -------------------------------------------------------------------------
    # 4. Category-specific registration closure
    # -------------------------------------------------------------------------
    def test_04_category_specific_registration_closure(self):
        tourn, cat1, cat2 = self._create_sample_tournament()
        self._login("organizer1")

        # Close Cat 1 registration
        resp = self.client.post(
            f"/t/{tourn.url_slug}/categories/{cat1.id}/toggle-registration",
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(cat1)
        self.assertFalse(cat1.is_registration_open)
        self.assertEqual(cat1.registration_status, "CLOSED")

        # Attempt to register for Cat 1 (should fail)
        self._login("player1")
        resp = self.client.post(
            f"/t/{tourn.url_slug}/register",
            data={"category_id": [cat1.id], "payment_method": "free"},
            follow_redirects=True,
        )
        self.assertIn(b"is closed", resp.data)

        # Register for Cat 2 (should succeed)
        resp = self.client.post(
            f"/t/{tourn.url_slug}/register",
            data={
                "category_id": [cat2.id],
                "payment_method": "free",
                f"partner_name_{cat2.id}": "Carlos Alcaraz",
                f"partner_age_{cat2.id}": "21",
                f"partner_mobile_{cat2.id}": "9876543299",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        reg2 = Registration.query.filter_by(tournament_id=tourn.id, category_id=cat2.id).first()
        self.assertIsNotNone(reg2)

    # -------------------------------------------------------------------------
    # 5. Playing format finalization after registrations
    # -------------------------------------------------------------------------
    def test_05_playing_format_finalization_after_registrations(self):
        tourn, cat1, _ = self._create_sample_tournament(format_status="NOT_DECIDED")

        # Create approved participant
        part = Participant(
            tournament_id=tourn.id,
            category_id=cat1.id,
            player_id=self.player_profile.id,
            name="Player One",
        )
        db.session.add(part)
        db.session.commit()

        self._login("organizer1")
        resp = self.client.post(
            f"/t/{tourn.url_slug}/categories/{cat1.id}/finalize-format",
            data={
                "format": "single_elimination",
                "scoring_format": "games",
                "num_sets": 1,
                "games_per_set": 6,
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        db.session.refresh(cat1)
        self.assertEqual(cat1.format, "single_elimination")
        self.assertEqual(cat1.format_status, "FINALIZED")

    # -------------------------------------------------------------------------
    # 6. Preservation of existing registrations after format changes
    # -------------------------------------------------------------------------
    def test_06_preservation_of_registrations_after_format_changes(self):
        tourn, cat1, _ = self._create_sample_tournament(format_status="NOT_DECIDED")
        reg = Registration(
            tournament_id=tourn.id,
            category_id=cat1.id,
            user_id=self.player_user.id,
            player_id=self.player_profile.id,
            status="approved",
        )
        part = Participant(
            tournament_id=tourn.id,
            category_id=cat1.id,
            player_id=self.player_profile.id,
            name="Player One",
        )
        db.session.add(reg)
        db.session.add(part)
        db.session.commit()

        self._login("organizer1")
        # Finalize to round robin
        self.client.post(
            f"/t/{tourn.url_slug}/categories/{cat1.id}/finalize-format",
            data={"format": "round_robin", "scoring_format": "games"},
            follow_redirects=True,
        )

        # Assert participant and registration still exist intact
        p = Participant.query.filter_by(tournament_id=tourn.id, category_id=cat1.id).first()
        r = Registration.query.filter_by(tournament_id=tourn.id, category_id=cat1.id).first()
        self.assertIsNotNone(p)
        self.assertIsNotNone(r)
        self.assertEqual(p.name, "Player One")

    # -------------------------------------------------------------------------
    # 7. Unauthorized CSV upload attempts
    # -------------------------------------------------------------------------
    def test_07_unauthorized_csv_upload_attempts(self):
        tourn, _, _ = self._create_sample_tournament()

        # 1. Unauthenticated
        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(b"dummy"), "test.csv")},
        )
        # Should redirect to login or deny
        self.assertIn(resp.status_code, [302, 401, 403])

        # 2. Regular player role
        self._login("player1")
        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(b"dummy"), "test.csv")},
            follow_redirects=True,
        )
        self.assertIn(b"Forbidden", resp.data)

    # -------------------------------------------------------------------------
    # 8. Invalid CSV files
    # -------------------------------------------------------------------------
    def test_08_invalid_csv_files(self):
        tourn, _, _ = self._create_sample_tournament()
        self._login("organizer1")

        # Empty CSV
        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(b""), "empty.csv")},
            follow_redirects=True,
        )
        self.assertIn(b"empty", resp.data.lower())

        # Missing required headers
        bad_headers = b"City,Zipcode,Country\nMumbai,400001,India\n"
        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(bad_headers), "missing.csv")},
            follow_redirects=True,
        )
        self.assertIn(b"Missing required CSV columns", resp.data)

    # -------------------------------------------------------------------------
    # 9. Duplicate participants in CSV
    # -------------------------------------------------------------------------
    def test_09_duplicate_participants_in_csv(self):
        tourn, _, _ = self._create_sample_tournament()
        self._login("organizer1")

        csv_content = (
            "First Name,Last Name,Email,Phone Number,Tournament Category,Registration Type\n"
            "Novak,Djokovic,novak@example.com,9876543210,Men's Singles,Singles\n"
            "Novak,Djokovic,novak@example.com,9876543210,Men's Singles,Singles\n"
        ).encode("utf-8")

        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(csv_content), "dups.csv")},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["valid_count"], 1)
        self.assertEqual(data["duplicate_count"], 1)

    # -------------------------------------------------------------------------
    # 10. Duplicate registrations (player already in database)
    # -------------------------------------------------------------------------
    def test_10_duplicate_registrations_existing_in_database(self):
        tourn, cat1, _ = self._create_sample_tournament()
        # Seed existing participant
        p = Participant(
            tournament_id=tourn.id,
            category_id=cat1.id,
            player_id=self.player_profile.id,
            name="Novak Djokovic",
            email="novak@example.com",
        )
        db.session.add(p)
        db.session.commit()

        self._login("organizer1")
        csv_content = (
            "First Name,Last Name,Email,Phone Number,Tournament Category,Registration Type\n"
            "Novak,Djokovic,novak@example.com,9876543210,Men's Singles,Singles\n"
        ).encode("utf-8")

        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(csv_content), "dups_db.csv")},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["valid_count"], 0)
        self.assertEqual(data["duplicate_count"], 1)

    # -------------------------------------------------------------------------
    # 11. Valid and invalid rows in the same file
    # -------------------------------------------------------------------------
    def test_11_valid_and_invalid_rows_in_same_file(self):
        tourn, _, _ = self._create_sample_tournament()
        self._login("organizer1")

        csv_content = (
            "First Name,Last Name,Email,Phone Number,Tournament Category,Registration Type\n"
            "Carlos,Alcaraz,carlos@example.com,9876543222,Men's Singles,Singles\n"
            ",MissingFirst,bad@example.com,9876543223,Men's Singles,Singles\n"
            "Jannik,Sinner,bad-email,9876543224,Men's Singles,Singles\n"
        ).encode("utf-8")

        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(csv_content), "mixed.csv")},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["valid_count"], 1)
        self.assertEqual(data["invalid_count"], 2)

        # Confirm import of valid rows
        batch_id = data["batch_id"]
        confirm_resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/confirm",
            json={"batch_id": batch_id, "valid_rows": data["valid_rows"]},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(confirm_resp.status_code, 200)

        # Carlos Alcaraz should be in participants
        part = Participant.query.filter_by(tournament_id=tourn.id, name="Carlos Alcaraz").first()
        self.assertIsNotNone(part)

        # Download error CSV
        err_resp = self.client.get(f"/tournaments/{tourn.url_slug}/import/{batch_id}/errors")
        self.assertEqual(err_resp.status_code, 200)
        self.assertIn(b"MissingFirst", err_resp.data)
        self.assertIn(b"bad-email", err_resp.data)

    # -------------------------------------------------------------------------
    # 12. Doubles partner validation
    # -------------------------------------------------------------------------
    def test_12_doubles_partner_validation(self):
        tourn, _, _ = self._create_sample_tournament()
        self._login("organizer1")

        # Missing partner on doubles
        csv_content = (
            "First Name,Last Name,Email,Phone Number,Tournament Category,Registration Type,Doubles Partner\n"
            "Bob,Bryan,bob@example.com,9876543230,Men's Doubles,Doubles,\n"
            "Mike,Bryan,mike@example.com,9876543231,Men's Doubles,Doubles,Mike Bryan\n"
            "Alexander,Zverev,sascha@example.com,9876543232,Men's Doubles,Doubles,Marcelo Melo\n"
        ).encode("utf-8")

        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(csv_content), "doubles.csv")},
            headers={"Accept": "application/json"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Row 1: missing partner -> invalid
        # Row 2: self-partner -> invalid
        # Row 3: valid partner -> valid
        self.assertEqual(data["valid_count"], 1)
        self.assertEqual(data["invalid_count"], 2)

    # -------------------------------------------------------------------------
    # 13. Repeated CSV imports (idempotency)
    # -------------------------------------------------------------------------
    def test_13_repeated_csv_imports_idempotency(self):
        tourn, _, _ = self._create_sample_tournament()
        self._login("organizer1")

        csv_content = (
            "First Name,Last Name,Email,Phone Number,Tournament Category,Registration Type\n"
            "Daniil,Medvedev,daniil@example.com,9876543240,Men's Singles,Singles\n"
        ).encode("utf-8")

        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/upload",
            data={"csv_file": (io.BytesIO(csv_content), "idempotent.csv")},
            headers={"Accept": "application/json"},
        )
        data = resp.get_json()
        batch_id = data["batch_id"]

        # First confirm
        confirm1 = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/confirm",
            json={"batch_id": batch_id, "valid_rows": data["valid_rows"]},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(confirm1.status_code, 200)

        # Repeated confirm on the same batch should be idempotent and not create duplicate
        confirm2 = self.client.post(
            f"/tournaments/{tourn.url_slug}/import/confirm",
            json={"batch_id": batch_id, "valid_rows": data["valid_rows"]},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(confirm2.status_code, 200)

        # Count participants named Daniil Medvedev
        count = Participant.query.filter_by(tournament_id=tourn.id, name="Daniil Medvedev").count()
        self.assertEqual(count, 1)

    # -------------------------------------------------------------------------
    # 14. Cross-tournament authorization
    # -------------------------------------------------------------------------
    def test_14_cross_tournament_authorization(self):
        tourn1, _, _ = self._create_sample_tournament()

        # Create tournament 2 belonging to organizer2
        tourn2 = Tournament(
            user_id=self.organizer2.id,
            name="Tournament Two",
            url_slug="tournament-two",
            is_published=True,
        )
        db.session.add(tourn2)
        db.session.commit()

        # Create a batch under Tournament 1
        batch1 = ParticipantImportBatch(
            tournament_id=tourn1.id,
            user_id=self.organizer.id,
            filename="t1.csv",
            file_hash="hash123",
            total_rows=1,
            valid_rows=1,
            status="PENDING_CONFIRMATION",
        )
        db.session.add(batch1)
        db.session.commit()

        # Organizer 2 logs in and attempts to confirm batch 1 on tournament 2
        self._login("organizer2")
        resp = self.client.post(
            f"/tournaments/{tourn2.url_slug}/import/confirm",
            json={"batch_id": batch1.id},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(resp.status_code, 403)

    # -------------------------------------------------------------------------
    # 15. Mobile registration and CSV interface responsiveness
    # -------------------------------------------------------------------------
    def test_15_mobile_registration_and_csv_interface_render(self):
        tourn, cat1, cat2 = self._create_sample_tournament(format_status="NOT_DECIDED")
        self._login("organizer1")

        # 1. Manage tournament page renders the Bulk Import tab and buttons
        resp = self.client.get(f"/tournaments/{tourn.url_slug}/manage")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Bulk CSV Import", resp.data)
        self.assertIn(b"tabContentImport", resp.data)
        self.assertIn(b"finalizeFormatModal", resp.data)

        # 2. Registration page renders accessible category cards with format TBA badge
        self._login("player1")
        resp = self.client.get(f"/t/{tourn.url_slug}/register")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"To Be Announced (TBA)", resp.data)
        self.assertIn(b"category-option-card", resp.data)

    # -------------------------------------------------------------------------
    # 16. CSV Formula Injection (CWE-1236) Protection
    # -------------------------------------------------------------------------
    def test_16_csv_formula_injection_protection(self):
        from app.services.bulk_import_service import sanitize_for_csv_injection

        self.assertEqual(sanitize_for_csv_injection("=cmd|' /C calc'!A0"), "'=cmd|' /C calc'!A0")
        self.assertEqual(sanitize_for_csv_injection("+12345"), "'+12345")
        self.assertEqual(sanitize_for_csv_injection("-100"), "'-100")
        self.assertEqual(sanitize_for_csv_injection("@SUM(A1:A10)"), "'@SUM(A1:A10)")
        self.assertEqual(sanitize_for_csv_injection("Normal Name"), "Normal Name")

    # -------------------------------------------------------------------------
    # 17. API Endpoint: Finalize Format
    # -------------------------------------------------------------------------
    def test_17_api_finalize_format(self):
        tourn, cat1, _ = self._create_sample_tournament(format_status="NOT_DECIDED")
        token = create_access_token(identity=str(self.organizer.id))

        resp = self.client.post(
            f"/api/v1/tournaments/{tourn.url_slug}/categories/{cat1.id}/format",
            json={"format": "single_elimination", "num_sets": 3, "games_per_set": 6},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["category"]["format"], "single_elimination")
        self.assertEqual(data["category"]["format_status"], "FINALIZED")

    # -------------------------------------------------------------------------
    # 18. API Endpoint: Toggle Category Registration Status
    # -------------------------------------------------------------------------
    def test_18_api_toggle_category_registration_status(self):
        tourn, cat1, _ = self._create_sample_tournament()
        token = create_access_token(identity=str(self.organizer.id))

        resp = self.client.patch(
            f"/api/v1/tournaments/{tourn.url_slug}/categories/{cat1.id}/registration-status",
            json={"status": "CLOSED"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["registration_status"], "CLOSED")
        self.assertFalse(data["is_registration_open"])

    # -------------------------------------------------------------------------
    # 19. Tournament Creation Status Sync & Direct Registration Link
    # -------------------------------------------------------------------------
    def test_19_tournament_creation_status_sync_and_direct_registration_link(self):
        self._login("organizer1")
        resp = self.client.post(
            "/tournaments/new",
            data={
                "name": "Sync Test Tournament",
                "format_status": "NOT_DECIDED",
                "registration_status": "OPEN",
                "category_names_csv": "Open Singles",
                "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "duration_days": 1,
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

        tourn = Tournament.query.filter_by(name="Sync Test Tournament").first()
        self.assertIsNotNone(tourn)
        self.assertEqual(tourn.status, "registration")
        self.assertEqual(tourn.registration_status, "OPEN")

        # Verify manage dashboard renders public tournament link
        manage_resp = self.client.get(f"/tournaments/{tourn.url_slug}/manage")
        self.assertEqual(manage_resp.status_code, 200)
        self.assertIn(f"{tourn.url_slug}".encode(), manage_resp.data)
        self.assertIn(b"Public Tournament Link:", manage_resp.data)

        # Verify public view displays the registration banner and entry link
        view_resp = self.client.get(f"/tournaments/{tourn.url_slug}?view=bracket")
        self.assertEqual(view_resp.status_code, 200)
        self.assertIn(b"Registration is currently Open!", view_resp.data)
        self.assertIn(b"Register Entry", view_resp.data)

    # -------------------------------------------------------------------------
    # 20. Prevent Infinite Redirect Loop When Registration Is Closed
    # -------------------------------------------------------------------------
    def test_20_no_infinite_redirect_when_registration_closed(self):
        tourn, _, _ = self._create_sample_tournament(reg_status="CLOSED")
        tourn.status = "registration"
        db.session.commit()

        # Accessing register page when closed must redirect to bracket view, not loop
        resp = self.client.get(f"/tournaments/{tourn.url_slug}/register", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(tourn.url_slug, resp.headers["Location"])
        self.assertIn("view=bracket", resp.headers["Location"])

        # Following redirect terminates at bracket view successfully with 200 OK
        resp_followed = self.client.get(
            f"/tournaments/{tourn.url_slug}/register", follow_redirects=True
        )
        self.assertEqual(resp_followed.status_code, 200)
        self.assertIn(b"Registration is currently closed for this tournament.", resp_followed.data)

    # -------------------------------------------------------------------------
    # 21. Open and Close Registration Actions Keep Status Synchronized
    # -------------------------------------------------------------------------
    def test_21_open_and_close_registration_actions_sync(self):
        tourn, _, _ = self._create_sample_tournament(reg_status="DRAFT")
        tourn.status = "setup"
        db.session.commit()
        self._login("organizer1")

        # Open registration
        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/manage",
            data={"action": "open_registration"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(tourn)
        self.assertEqual(tourn.status, "registration")
        self.assertEqual(tourn.registration_status, "OPEN")

        # Close registration
        resp = self.client.post(
            f"/tournaments/{tourn.url_slug}/manage",
            data={"action": "close_registration"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        db.session.refresh(tourn)
        self.assertEqual(tourn.status, "setup")
        self.assertEqual(tourn.registration_status, "CLOSED")

    # -------------------------------------------------------------------------
    # 22. Default Route for Unauthenticated Visitors & Guest Registration
    # -------------------------------------------------------------------------
    def test_22_unauthenticated_default_route_and_guest_registration(self):
        tourn, cat_singles, _ = self._create_sample_tournament(reg_status="OPEN")
        tourn.status = "registration"
        db.session.commit()

        # 1. Visiting tournament hub unauthenticated lands on tournament view (200, no redirect to login)
        resp_hub = self.client.get(f"/tournaments/{tourn.url_slug}")
        self.assertEqual(resp_hub.status_code, 200)
        self.assertIn(b"Registration is currently Open!", resp_hub.data)
        self.assertIn(b"Register as a guest or sign in", resp_hub.data)
        self.assertIn(b"Go to Registration Form", resp_hub.data)

        # 2. Visiting direct registration link unauthenticated opens guest registration form
        resp_reg = self.client.get(f"/tournaments/{tourn.url_slug}/register")
        self.assertEqual(resp_reg.status_code, 200)
        self.assertIn(b"Guest Registration & Leaderboard Access", resp_reg.data)
        self.assertIn(b"guest_name", resp_reg.data)
        self.assertIn(b"guest_mobile", resp_reg.data)

        # 3. Submitting registration as guest
        post_data = {
            "category_id": [cat_singles.id],
            "guest_name": "Guest Tennis Star",
            "guest_age": "24",
            "guest_mobile": "9876543299",
            "guest_gender": "Male",
            "guest_email": "gueststar@example.com",
            "payment_method": "cash",
            "tz_offset": "0",
        }
        resp_post = self.client.post(
            f"/tournaments/{tourn.url_slug}/register",
            data=post_data,
            follow_redirects=True,
        )
        self.assertEqual(resp_post.status_code, 200)
        self.assertIn(b"Registration Submitted as Guest!", resp_post.data)
        self.assertIn(b"view live leaderboards", resp_post.data)

        # 4. Verify database state
        guest_player = Player.query.filter_by(contact_number="9876543299").first()
        self.assertIsNotNone(guest_player)
        self.assertIsNone(guest_player.user_id)
        self.assertEqual(guest_player.name, "Guest Tennis Star")

        reg = Registration.query.filter_by(
            tournament_id=tourn.id, player_id=guest_player.id
        ).first()
        self.assertIsNotNone(reg)
        anon_user = User.query.filter_by(username="anonymous_registrations").first()
        self.assertIsNotNone(anon_user)
        self.assertEqual(reg.user_id, anon_user.id)
