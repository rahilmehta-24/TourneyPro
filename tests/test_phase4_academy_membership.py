"""
Phase 4 Tests:
Single Active Academy Membership, Concurrency-Safe Transfers, and Snapshot Preservation.
"""

import os
import tempfile
import unittest
from datetime import datetime
from app import create_app, db
from app.domain.models import User, Player, Tournament, Category, Registration, Academy, AcademyMember, AuditLog
from app.services.academy_service import (
    add_academy_member,
    transfer_user_academy_membership,
    leave_academy_membership,
    get_user_active_academy_membership,
)


class Phase4AcademyMembershipTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-phase4-secret"
            JWT_SECRET_KEY = "test-phase4-jwt-secret"
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
        u = User(username=username, email=email, role=role, is_email_verified=True)
        u.set_password("Password123!")
        db.session.add(u)
        db.session.flush()
        return u

    def _create_active_academy(self, name, slug, owner):
        acad = Academy(name=name, url_slug=slug, owner_id=owner.id, status="ACTIVE", created_at=datetime.utcnow())
        db.session.add(acad)
        db.session.flush()
        owner_mem = AcademyMember(academy_id=acad.id, user_id=owner.id, role="owner", membership_status="ACTIVE")
        db.session.add(owner_mem)
        db.session.flush()
        return acad

    def test_01_single_active_academy_membership_enforcement(self):
        """A user cannot join two academies simultaneously."""
        owner1 = self._create_user("owner_one", "owner1@test.com", role="admin")
        owner2 = self._create_user("owner_two", "owner2@test.com", role="admin")
        player_user = self._create_user("player_sam", "sam@test.com", role="user")

        acad_a = self._create_active_academy("Apex Tennis", "apex-tennis", owner1)
        acad_b = self._create_active_academy("Baseline Club", "baseline-club", owner2)
        db.session.commit()

        # Sam joins Academy A
        mem_a = add_academy_member(acad_a.id, player_user.id, role="member")
        self.assertEqual(mem_a.membership_status, "ACTIVE")
        self.assertEqual(mem_a.academy_id, acad_a.id)

        # Attempting to join Academy B directly without leaving or transferring must be rejected!
        with self.assertRaises(ValueError) as ctx:
            add_academy_member(acad_b.id, player_user.id, role="member")
        self.assertIn("already an active member", str(ctx.exception))

        # Confirm user still has only 1 active membership in Academy A
        active_mem = get_user_active_academy_membership(player_user.id)
        self.assertEqual(active_mem.academy_id, acad_a.id)

    def test_02_transactional_membership_transfer(self):
        """Transferring deactivates previous membership and activates new membership with audit."""
        owner1 = self._create_user("owner_tx1", "tx1@test.com", role="admin")
        owner2 = self._create_user("owner_tx2", "tx2@test.com", role="admin")
        player_user = self._create_user("player_tim", "tim@test.com", role="user")

        acad_a = self._create_active_academy("North Academy", "north-acad", owner1)
        acad_b = self._create_active_academy("South Academy", "south-acad", owner2)
        db.session.commit()

        # Enroll in North
        add_academy_member(acad_a.id, player_user.id)

        # Execute Transfer to South
        new_mem = transfer_user_academy_membership(
            user_id=player_user.id,
            target_academy_id=acad_b.id,
            acting_user=player_user,
            reason="Relocated to south campus"
        )

        self.assertEqual(new_mem.academy_id, acad_b.id)
        self.assertEqual(new_mem.membership_status, "ACTIVE")

        # Previous membership in North must now be TRANSFERRED
        old_mem = AcademyMember.query.filter_by(academy_id=acad_a.id, user_id=player_user.id).first()
        self.assertEqual(old_mem.membership_status, "TRANSFERRED")
        self.assertIsNotNone(old_mem.left_at)

        # Confirm only ONE active membership exists across the platform
        active_mems = AcademyMember.query.filter_by(user_id=player_user.id, membership_status="ACTIVE").all()
        self.assertEqual(len(active_mems), 1)
        self.assertEqual(active_mems[0].academy_id, acad_b.id)

        # Verify audit log
        audit = AuditLog.query.filter_by(action_type="ACADEMY_MEMBERSHIP_TRANSFERRED", target_id=acad_b.id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, player_user.id)

    def test_03_leave_academy_membership(self):
        """User can leave an academy; status changes to INACTIVE and left_at is stamped."""
        owner = self._create_user("owner_leave", "leave_owner@test.com", role="admin")
        player_user = self._create_user("player_leo", "leo@test.com", role="user")
        acad = self._create_active_academy("West Academy", "west-acad", owner)
        db.session.commit()

        add_academy_member(acad.id, player_user.id)
        self.assertIsNotNone(get_user_active_academy_membership(player_user.id))

        leave_academy_membership(player_user.id, acad.id)

        self.assertIsNone(get_user_active_academy_membership(player_user.id))
        mem = AcademyMember.query.filter_by(academy_id=acad.id, user_id=player_user.id).first()
        self.assertEqual(mem.membership_status, "INACTIVE")
        self.assertIsNotNone(mem.left_at)

    def test_04_historical_tournament_registration_preserves_academy_snapshot(self):
        """Historical registrations maintain the academy snapshot even after user transfers or leaves."""
        owner1 = self._create_user("owner_snap1", "snap1@test.com", role="admin")
        owner2 = self._create_user("owner_snap2", "snap2@test.com", role="admin")
        player_user = self._create_user("player_mia", "mia@test.com", role="user")

        p = Player(user_id=player_user.id, name="Mia Hamm", email="mia@test.com", gender="Female", age_category="Open")
        db.session.add(p)
        db.session.flush()

        acad_a = self._create_active_academy("Club Alpha", "club-alpha", owner1)
        acad_b = self._create_active_academy("Club Beta", "club-beta", owner2)

        # Mia is active in Club Alpha
        add_academy_member(acad_a.id, player_user.id)

        # Tournament hosted by Club Alpha
        tourney = Tournament(name="Alpha Cup", url_slug="alpha-cup", user_id=owner1.id, academy_id=acad_a.id, status="in_progress")
        db.session.add(tourney)
        db.session.flush()

        cat = Category(tournament_id=tourney.id, name="Women's Singles", gender="Female", age_category="Open", format="knockout")
        db.session.add(cat)
        db.session.flush()

        # Registration created with academy_id_snapshot
        reg = Registration(
            tournament_id=tourney.id,
            category_id=cat.id,
            user_id=player_user.id,
            player_id=p.id,
            status="approved",
            payment_status="paid",
            academy_id_snapshot=acad_a.id
        )
        db.session.add(reg)
        db.session.commit()

        self.assertEqual(reg.academy_id_snapshot, acad_a.id)

        # Later, Mia transfers to Club Beta
        transfer_user_academy_membership(player_user.id, acad_b.id)

        # Refresh registration from database
        db.session.refresh(reg)

        # Historical registration STILL points to Club Alpha snapshot!
        self.assertEqual(reg.academy_id_snapshot, acad_a.id)

        # While Mia's current active academy is now Club Beta
        current_active = get_user_active_academy_membership(player_user.id)
        self.assertEqual(current_active.academy_id, acad_b.id)


if __name__ == '__main__':
    unittest.main()
