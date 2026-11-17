"""
Integration Tests for Phase 5 & 6:
Tournament Management, Custom Logo Upload, Host-Controlled Approvals,
Inter-Academy Non-Membership Invariant, and Audited Score Revisions.
"""

import os
import io
import tempfile
import unittest
from datetime import datetime
from app import create_app, db
from app.domain.models import (
    User, Player, Tournament, Category, Match, Participant, Registration,
    Academy, AcademyMember, MatchScoreRevision
)
from app.services.academy_service import add_academy_member


class Phase5And6TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-phase5-secret"
            JWT_SECRET_KEY = "test-phase5-jwt-secret"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False

        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.rollback()
        self.app_context.pop()

    def _create_user(self, username, email, role="user"):
        u = User(username=username, email=email, role=role, is_email_verified=True, full_name=username.title())
        u.set_password("Password123!")
        db.session.add(u)
        db.session.flush()
        return u

    def _login(self, username, password="Password123!"):
        self.client.get('/logout', follow_redirects=True)
        return self.client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def _create_active_academy(self, name, slug, owner):
        acad = Academy(name=name, url_slug=slug, owner_id=owner.id, status="ACTIVE", created_at=datetime.utcnow())
        db.session.add(acad)
        db.session.flush()
        owner_mem = AcademyMember(academy_id=acad.id, user_id=owner.id, role="owner", membership_status="ACTIVE")
        db.session.add(owner_mem)
        db.session.flush()
        return acad

    def test_01_tournament_creation_with_custom_logo_and_real_identity(self):
        """Host uploads a custom logo image; tournament is created with authenticated user identity and logo_url."""
        host = self._create_user("host_elena", "elena@baseline.test", role="admin")
        acad = self._create_active_academy("Elena Tennis Club", "elena-tennis-club", host)
        db.session.commit()

        self._login("host_elena")

        # Fake PNG upload
        fake_logo = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

        res = self.client.post("/tournaments/new", data={
            "name": "Elena Invitational Trophy",
            "academy_id": str(acad.id),
            "start_date": "2026-12-01",
            "duration_days": "2",
            "logo": (fake_logo, "host_logo.png")
        }, content_type="multipart/form-data", follow_redirects=False)

        self.assertEqual(res.status_code, 302)

        tournament = Tournament.query.filter_by(name="Elena Invitational Trophy").first()
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament.user_id, host.id)
        self.assertEqual(tournament.creator_name, "Host_Elena")  # Real name, NOT 'Anonymous'
        self.assertIsNotNone(tournament.logo_url)
        self.assertTrue(tournament.logo_url.startswith("/static/uploads/tournaments/logos/"))

    def test_02_external_participant_approval_and_non_membership_invariant(self):
        """External player registers; host reviews approval; external player NEVER joins host academy."""
        host = self._create_user("host_marcus", "marcus@host.test", role="admin")
        host_acad = self._create_active_academy("Marcus Tennis Center", "marcus-center", host)

        ext_user = self._create_user("ext_rafa", "rafa@ext.test", role="user")
        ext_user.phone_number = "5551234567"
        ext_user.profile_completed = True
        ext_user.completion_percentage = 100

        ext_acad = self._create_active_academy("Mallorca Academy", "mallorca-acad", self._create_user("toni", "toni@ext.test", role="admin"))
        add_academy_member(ext_acad.id, ext_user.id)
        db.session.commit()

        from datetime import date
        p_ext = Player(
            user_id=ext_user.id,
            name="Rafa Nadal",
            email="rafa@ext.test",
            gender="Male",
            age_category="Open",
            dob=date(1986, 6, 3),
            primary_sport="Tennis",
            skill_level="Pro",
            emergency_contact_name="Toni Nadal",
            emergency_contact_phone="5559876543",
            profile_status="complete"
        )
        db.session.add(p_ext)
        db.session.flush()

        tourney = Tournament(name="Marcus Open 2026", url_slug="marcus-open-2026", user_id=host.id, academy_id=host_acad.id, status="registration")
        db.session.add(tourney)
        db.session.flush()

        cat = Category(tournament_id=tourney.id, name="Men's Singles", gender="Male", age_category="Open", format="knockout", entry_fee=0.0)
        db.session.add(cat)
        db.session.commit()

        # Rafa registers for Marcus Open
        self._login("ext_rafa")
        reg_res = self.client.post(f"/tournaments/{tourney.url_slug}/register", data={
            "category_id": [str(cat.id)],
            "participant_name": "Rafa Nadal",
            "mobile": "5551234567",
            "email": "rafa@ext.test",
            "gender": "Male",
            "dob": "1986-06-03"
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)

        # 1. Verify Registration record
        reg = Registration.query.filter_by(tournament_id=tourney.id, user_id=ext_user.id).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.academy_id_snapshot, ext_acad.id)  # Snapshotted external academy!

        # 2. Strict Invariant: Rafa must NOT become a member of Marcus Tennis Center!
        marcus_mem = AcademyMember.query.filter_by(academy_id=host_acad.id, user_id=ext_user.id).first()
        self.assertIsNone(marcus_mem, "External tournament registration must NEVER create host-academy membership!")

        # 3. Host reviews and approves the registration
        self._login("host_marcus")
        review_res = self.client.post(
            f"/tournaments/{tourney.url_slug}/manage",
            data={"action": "approve_registration", "registration_id": str(reg.id)},
            follow_redirects=True
        )
        self.assertEqual(review_res.status_code, 200)

        db.session.refresh(reg)
        self.assertEqual(reg.status, "approved")

        # 4. Invariant holds even after approval
        marcus_mem_after = AcademyMember.query.filter_by(academy_id=host_acad.id, user_id=ext_user.id).first()
        self.assertIsNone(marcus_mem_after)

    def test_03_match_score_revision_audit_trail(self):
        """Editing an already completed match requires a reason and writes a MatchScoreRevision entry."""
        host = self._create_user("host_roger", "roger@host.test", role="admin")
        p1_u = self._create_user("player_novak", "novak@p.test", role="user")
        p2_u = self._create_user("player_carlos", "carlos@p.test", role="user")

        p1 = Player(user_id=p1_u.id, name="Novak", email="novak@p.test", gender="Male", age_category="Open")
        p2 = Player(user_id=p2_u.id, name="Carlos", email="carlos@p.test", gender="Male", age_category="Open")
        db.session.add_all([p1, p2])
        db.session.flush()

        tourney = Tournament(name="Laver Cup 2026", url_slug="laver-cup-2026", user_id=host.id, status="in_progress")
        db.session.add(tourney)
        db.session.flush()

        cat = Category(tournament_id=tourney.id, name="Men's Singles", gender="Male", age_category="Open", format="single_elimination", num_sets=1, games_per_set=6)
        db.session.add(cat)
        db.session.flush()

        part1 = Participant(tournament_id=tourney.id, category_id=cat.id, player_id=p1.id, name="Novak")
        part2 = Participant(tournament_id=tourney.id, category_id=cat.id, player_id=p2.id, name="Carlos")
        db.session.add_all([part1, part2])
        db.session.flush()

        # Match initially completed: Novak won 6-4
        match = Match(
            tournament_id=tourney.id,
            category_id=cat.id,
            round=1,
            match_number=1,
            participant1_id=part1.id,
            participant2_id=part2.id,
            score1="6",
            score2="4",
            winner_id=part1.id,
            status="completed",
            completed_at=datetime.utcnow()
        )
        db.session.add(match)
        db.session.commit()

        self._login("host_roger")

        # Official corrects score: actually Carlos won 7-6 (tiebreak 7-5)
        res = self.client.post(f"/tournaments/{tourney.url_slug}/match/{match.id}/report", data={
            "action": "complete_match",
            "winner_id": str(part2.id),
            "set1_p1": "6",
            "set1_p2": "7",
            "tb1_p1": "5",
            "tb1_p2": "7",
            "audit_reason": "Score Entry Mistake",
            "audit_explanation": "Official paper scorecard audit revealed Carlos won set 1 tiebreak 7-5."
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)

        db.session.refresh(match)
        self.assertEqual(match.winner_id, part2.id)

        # Verify MatchScoreRevision recorded
        revisions = MatchScoreRevision.query.filter_by(match_id=match.id).all()
        self.assertEqual(len(revisions), 1)
        rev = revisions[0]
        self.assertEqual(rev.edited_by_id, host.id)
        self.assertEqual(rev.previous_winner_id, part1.id)
        self.assertEqual(rev.new_winner_id, part2.id)
        self.assertEqual(rev.reason, "Score Entry Mistake")
        self.assertIn("paper scorecard audit", rev.explanation)


if __name__ == '__main__':
    unittest.main()
