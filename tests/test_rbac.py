import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from app import create_app
from app.domain.models import (
    db,
    User,
    Tournament,
    Category,
    Match,
    Participant,
    Player,
    TournamentStaff,
    Academy,
    AcademyMember,
    TeamMember,
)


class RbacSecurityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "rbac-test-secret"
            JWT_SECRET_KEY = "rbac-jwt-secret"
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
            db.session.rollback()
            TournamentStaff.query.delete()
            AcademyMember.query.delete()
            Academy.query.delete()
            Match.query.delete()
            TeamMember.query.delete()
            Participant.query.delete()
            Player.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            User.query.delete()
            db.session.commit()

            # 1. Superadmin
            self.superadmin = User(username="superadmin_user", email="super@test.com", role="superadmin")
            self.superadmin.set_password("pass123")
            db.session.add(self.superadmin)

            # 2. Tournament Owner / Organizer (admin)
            self.organizer = User(username="tournament_owner", email="owner@test.com", role="admin")
            self.organizer.set_password("pass123")
            db.session.add(self.organizer)

            # 3. Rogue Admin (Attacker from different tournament)
            self.rogue_admin = User(username="rogue_admin", email="rogue@test.com", role="admin")
            self.rogue_admin.set_password("pass123")
            db.session.add(self.rogue_admin)

            # 4. Appointed Official (regular user assigned to staff)
            self.official_user = User(username="official_staff", email="official@test.com", role="user")
            self.official_user.set_password("pass123")
            db.session.add(self.official_user)

            # 5. Playing User (Player in match)
            self.player_user = User(username="player_roger", email="roger@test.com", role="user")
            self.player_user.set_password("pass123")
            db.session.add(self.player_user)

            # 6. Team Captain User
            self.captain_user = User(username="captain_rafa", email="captain@test.com", role="user")
            self.captain_user.set_password("pass123")
            db.session.add(self.captain_user)

            db.session.commit()

            # Save user IDs
            self.organizer_id = self.organizer.id
            self.official_user_id = self.official_user.id
            self.player_user_id = self.player_user.id
            self.captain_user_id = self.captain_user.id

            # Tournament
            self.tournament = Tournament(
                name="TourneyPro Championship",
                url_slug="tourneypro-championship-2026",
                user_id=self.organizer.id,
                status="in_progress",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 7),
            )
            db.session.add(self.tournament)
            db.session.commit()
            self.tournament_slug = self.tournament.url_slug
            self.tournament_id = self.tournament.id

            # Category
            self.category = Category(
                tournament_id=self.tournament.id,
                name="Men's Singles",
                format="single_elimination",
                status="in_progress",
                draw_published=False,
            )
            db.session.add(self.category)
            db.session.commit()
            self.category_id = self.category.id

            # Players & Participants
            self.p1_player = Player(user_id=self.player_user.id, name="Roger Federer", email="roger@test.com", gender="Male", age_category="Open")
            self.p2_player = Player(user_id=None, name="Novak Djokovic", email="novak@test.com", gender="Male", age_category="Open")
            db.session.add_all([self.p1_player, self.p2_player])
            db.session.commit()
            self.p1_player_id = self.p1_player.id
            self.p2_player_id = self.p2_player.id

            self.part1 = Participant(tournament_id=self.tournament.id, category_id=self.category.id, name="Roger Federer", player_id=self.p1_player.id)
            self.part2 = Participant(tournament_id=self.tournament.id, category_id=self.category.id, name="Novak Djokovic", player_id=self.p2_player.id)
            db.session.add_all([self.part1, self.part2])
            db.session.commit()
            self.part1_id = self.part1.id
            self.part2_id = self.part2.id

            # Match
            self.match = Match(
                tournament_id=self.tournament.id,
                category_id=self.category.id,
                round=1,
                match_number=1,
                participant1_id=self.part1.id,
                participant2_id=self.part2.id,
                status="pending",
                match_type="knockout",
                lock_version=1,
            )
            db.session.add(self.match)
            db.session.commit()
            self.match_id = self.match.id

        self.client = self.app.test_client()

    def _login(self, username, password="pass123"):
        self.client.get("/logout")
        return self.client.post("/login", data={"username": username, "password": password}, follow_redirects=True)

    # ------------------------------------------------------------------
    # 1. DRAW PDF PUBLIC RELEASE & DRAFT ACCESS CONTROL
    # ------------------------------------------------------------------
    def test_01_unpublished_draw_pdf_restricted_from_public(self):
        """Draft draws cannot be downloaded by public visitors or regular players."""
        # Unauthenticated request to draft draw
        res = self.client.get(
            f"/tournaments/{self.tournament_slug}/category/{self.category_id}/export_pdf"
        )
        self.assertIn(res.status_code, [302, 401, 403])

        # Regular logged-in player
        self._login("player_roger")
        res_player = self.client.get(
            f"/tournaments/{self.tournament_slug}/category/{self.category_id}/export_pdf"
        )
        self.assertEqual(res_player.status_code, 403)

    def test_02_published_draw_pdf_accessible_by_public(self):
        """When draw_published is True, anyone can download the official Draw PDF."""
        with self.app.app_context():
            cat = Category.query.get(self.category_id)
            cat.draw_published = True
            db.session.commit()

        # Unauthenticated request to published draw
        res = self.client.get(
            f"/tournaments/{self.tournament_slug}/category/{self.category_id}/export_pdf"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/pdf", res.headers.get("Content-Type"))

    def test_03_toggle_publish_draw_permissions(self):
        """Only tournament owner or superadmin can toggle draw publishing."""
        # Rogue admin cannot publish someone else's tournament draw
        self._login("rogue_admin")
        res_rogue = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/toggle-publish"
        )
        self.assertEqual(res_rogue.status_code, 403)

        # Owner publishes
        self._login("tournament_owner")
        res_owner = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/toggle-publish",
            follow_redirects=True,
        )
        self.assertEqual(res_owner.status_code, 200)

        with self.app.app_context():
            cat = Category.query.get(self.category_id)
            self.assertTrue(cat.draw_published)

    # ------------------------------------------------------------------
    # 2. PARTICIPANT DESK ROSTER STRICT PRIVACY
    # ------------------------------------------------------------------
    def test_04_desk_roster_pdf_restricted_to_organizer_and_superadmin(self):
        """Desk roster PDF contains private contacts and must remain organizer/superadmin only."""
        # Public
        res_anon = self.client.get(f"/tournaments/{self.tournament_slug}/export_participants_pdf")
        self.assertIn(res_anon.status_code, [302, 401])

        # Player User
        self._login("player_roger")
        res_player = self.client.get(f"/tournaments/{self.tournament_slug}/export_participants_pdf")
        self.assertEqual(res_player.status_code, 403)

        # Rogue Admin (IDOR attack)
        self._login("rogue_admin")
        res_rogue = self.client.get(f"/tournaments/{self.tournament_slug}/export_participants_pdf")
        self.assertEqual(res_rogue.status_code, 403)

        # Owner success
        self._login("tournament_owner")
        res_owner = self.client.get(f"/tournaments/{self.tournament_slug}/export_participants_pdf")
        self.assertEqual(res_owner.status_code, 200)
        self.assertIn("application/pdf", res_owner.headers.get("Content-Type"))

    # ------------------------------------------------------------------
    # 3. TOURNAMENT STAFF APPOINTMENT & MATCH SCORING
    # ------------------------------------------------------------------
    def test_05_staff_appointment_and_score_reporting(self):
        """Owner appoints an official user, who can then report scores without site admin role."""
        with self.app.app_context():
            staff = TournamentStaff(
                tournament_id=self.tournament_id,
                user_id=self.official_user_id,
                role="official",
                assigned_court="Court 1",
            )
            db.session.add(staff)
            db.session.commit()

        # Log in as official_user (role='user', but has TournamentStaff)
        self._login("official_staff")
        res = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/match/{self.match_id}/report",
            data={
                "action": "completed",
                "winner_id": self.part2_id,
                "set1_p1": "4",
                "set1_p2": "6",
                "lock_version": 1,
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            m = Match.query.get(self.match_id)
            self.assertEqual(m.status, "completed")
            self.assertEqual(m.winner_id, self.part2_id)

    # ------------------------------------------------------------------
    # 4. COURT PIN AUTHENTICATION
    # ------------------------------------------------------------------
    def test_06_court_pin_umpire_login_and_scoring(self):
        """Court umpires can sign in via 6-digit access PIN and enter scores."""
        pin = "852963"
        with self.app.app_context():
            staff_pin = TournamentStaff(
                tournament_id=self.tournament_id,
                user_id=None,
                role="official",
                assigned_court="Court 2",
                access_pin=pin,
                pin_expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            db.session.add(staff_pin)
            db.session.commit()

        # Submit invalid PIN
        res_bad = self.client.post(
            f"/t/{self.tournament_slug}/score-login",
            data={"pin": "000000"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid access PIN", res_bad.data)

        # Submit valid PIN
        res_ok = self.client.post(
            f"/t/{self.tournament_slug}/score-login",
            data={"pin": pin},
            follow_redirects=True,
        )
        self.assertEqual(res_ok.status_code, 200)

        # Score the match using court PIN session
        res_score = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/match/{self.match_id}/report",
            data={
                "action": "completed",
                "winner_id": self.part2_id,
                "set1_p1": "3",
                "set1_p2": "6",
                "lock_version": 1,
            },
            follow_redirects=True,
        )
        self.assertEqual(res_score.status_code, 200)

        # Logout from court session
        self.client.get(f"/t/{self.tournament_slug}/score-logout")
        # Attempt to score after logout -> denied
        res_denied = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/match/{self.match_id}/report",
            data={"action": "completed"},
        )
        self.assertIn(res_denied.status_code, [302, 401, 403])

    # ------------------------------------------------------------------
    # 5. ANTI-CONFLICT OF INTEREST GUARD
    # ------------------------------------------------------------------
    def test_07_player_cannot_score_own_match(self):
        """A user who is a player in the match is blocked from recording scores on that match."""
        # player_roger is participant1 in self.match
        self._login("player_roger")

        # Even if player_roger was given a staff assignment
        with self.app.app_context():
            staff = TournamentStaff(
                tournament_id=self.tournament_id,
                user_id=self.player_user_id,
                role="official",
            )
            db.session.add(staff)
            db.session.commit()

        res = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/match/{self.match_id}/report",
            data={
                "action": "completed",
                "winner_id": self.part1_id,
                "set1_p1": "6",
                "set1_p2": "0",
                "lock_version": 1,
            },
            follow_redirects=True,
        )
        # Should be blocked by anti-conflict check with warning message
        self.assertIn(b"Conflict of interest", res.data)

        with self.app.app_context():
            m = Match.query.get(self.match_id)
            self.assertEqual(m.status, "pending")

    # ------------------------------------------------------------------
    # 6. OPTIMISTIC CONCURRENCY LOCKING
    # ------------------------------------------------------------------
    def test_08_optimistic_locking_prevents_stale_overwrites(self):
        """When an outdated lock_version is submitted, the score update is rejected."""
        self._login("tournament_owner")

        # Step A: First official updates score to completed (advancing lock_version to 2)
        res1 = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/match/{self.match_id}/report",
            data={
                "action": "completed",
                "winner_id": self.part2_id,
                "set1_p1": "4",
                "set1_p2": "6",
                "lock_version": 1,
            },
            follow_redirects=True,
        )
        self.assertEqual(res1.status_code, 200)

        # Step B: Second official submits from stale tab with old lock_version 1
        res2 = self.client.post(
            f"/t/{self.tournament_slug}/categories/{self.category_id}/match/{self.match_id}/report",
            data={
                "action": "completed",
                "winner_id": self.part1_id,
                "set1_p1": "6",
                "set1_p2": "4",
                "lock_version": 1,
                "audit_reason": "Correction",
                "audit_explanation": "Correction explanation greater than 10 chars",
            },
            follow_redirects=True,
        )
        # Conflict warning shown
        self.assertIn(b"Conflict detected", res2.data)

        # Winner remains Djokovic (part2)
        with self.app.app_context():
            m = Match.query.get(self.match_id)
            self.assertEqual(m.winner_id, self.part2_id)

    # ------------------------------------------------------------------
    # 7. TEAM CAPTAINS LINEUP NOMINATION & OPPONENT ISOLATION
    # ------------------------------------------------------------------
    def test_09_team_captain_lineup_nomination(self):
        """Team captains can nominate their team lineup, but cannot overwrite opponent lineup."""
        with self.app.app_context():
            # Create Team League Category
            team_cat = Category(
                tournament_id=self.tournament_id,
                name="Team League",
                format="group_stage",
                status="in_progress",
                max_players_per_team=4,
            )
            db.session.add(team_cat)
            db.session.commit()

            team1 = Participant(tournament_id=self.tournament_id, category_id=team_cat.id, name="Team Red")
            team2 = Participant(tournament_id=self.tournament_id, category_id=team_cat.id, name="Team Blue")
            db.session.add_all([team1, team2])
            db.session.commit()

            # Assign captain_user as captain of Team Red
            tm = TeamMember(participant_id=team1.id, player_id=self.p1_player_id, role="captain")
            # Link p1_player to captain_user
            p1 = Player.query.get(self.p1_player_id)
            p1.user_id = self.captain_user_id
            db.session.add(tm)

            # Fixture and child rubber
            fixture = Match(
                tournament_id=self.tournament_id,
                category_id=team_cat.id,
                round=1,
                match_number=1,
                participant1_id=team1.id,
                participant2_id=team2.id,
                status="pending",
                match_type="group_stage",
                scheduled_time=datetime.utcnow() + timedelta(hours=2),  # Well outside 15-min lock
            )
            db.session.add(fixture)
            db.session.commit()

            sub_rubber = Match(
                tournament_id=self.tournament_id,
                category_id=team_cat.id,
                parent_match_id=fixture.id,
                rubber_type="singles",
                rubber_number=1,
                round=1,
                match_number=1,
                participant1_id=team1.id,
                participant2_id=team2.id,
                status="pending",
                match_type="group_stage",
            )
            db.session.add(sub_rubber)
            db.session.commit()
            fixture_id = fixture.id
            sub_rubber_id = sub_rubber.id
            team_cat_id = team_cat.id

        # Log in as Captain of Team 1
        self._login("captain_rafa")

        res = self.client.post(
            f"/t/{self.tournament_slug}/categories/{team_cat_id}/fixtures/{fixture_id}/lineup",
            data={
                "r1_p1_player1": self.p1_player_id,  # Team 1 selection
                "r1_p2_player1": self.p2_player_id,  # Attempt to force Team 2 selection
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            r = Match.query.get(sub_rubber_id)
            # Team 1 was updated
            self.assertEqual(r.p1_player1_id, self.p1_player_id)
            # Team 2 player was NOT overwritten by opposing captain
            self.assertIsNone(r.p2_player1_id)

    # ------------------------------------------------------------------
    # 8. ACADEMY TENANT ISOLATION
    # ------------------------------------------------------------------
    def test_10_academy_multi_tenant_isolation(self):
        """Non-members cannot manage members or post announcements in another academy."""
        with self.app.app_context():
            academy = Academy(
                name="Elite Tennis Academy",
                url_slug="elite-tennis-academy",
                owner_id=self.organizer_id,
            )
            db.session.add(academy)
            db.session.commit()
            acad_slug = academy.url_slug

        # Rogue user attempts to post announcement
        self._login("rogue_admin")
        res_rogue = self.client.post(
            f"/academies/{acad_slug}/announcements",
            data={"title": "Rogue Post", "content": "Rogue Announcement"},
        )
        self.assertEqual(res_rogue.status_code, 403)

        # Academy owner posts successfully
        self._login("tournament_owner")
        res_owner = self.client.post(
            f"/academies/{acad_slug}/announcements",
            data={"title": "Official Camp", "content": "Summer junior training camp announcement."},
            follow_redirects=True,
        )
        self.assertEqual(res_owner.status_code, 200)
        self.assertIn(b"Announcement posted", res_owner.data)


if __name__ == "__main__":
    unittest.main()
