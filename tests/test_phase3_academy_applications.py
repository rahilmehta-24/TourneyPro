"""
Phase 3 Tests:
Academy Applications and Platform Superadmin Verification.
"""

import os
import tempfile
import unittest
from app import create_app, db
from app.domain.models import User, Academy, AcademyMember, AuditLog
from app.services.academy_service import (
    submit_academy_application,
    review_academy_application,
)


class Phase3AcademyApplicationsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-phase3-secret"
            JWT_SECRET_KEY = "test-phase3-jwt-secret"
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

    def _login(self, username, password="Password123!"):
        return self.client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)

    def test_01_applicant_submits_academy_application(self):
        """Authenticated user submits an application; status becomes PENDING with an AuditLog."""
        applicant = self._create_user("applicant_bob", "bob@apex.test")
        db.session.commit()

        app_rec = submit_academy_application(applicant.id, {
            "name": "Apex Elite Tennis Academy",
            "description": "Premier facility with 8 clay courts.",
            "address": "100 Championship Blvd",
            "city": "Atlanta",
            "state": "GA",
            "country": "USA",
            "contact_email": "info@apex.test",
            "contact_phone": "+1 404-555-0100",
            "sports_offered": "Tennis, Pickleball",
            "website_url": "https://apex.test"
        })

        self.assertIsNotNone(app_rec.id)
        self.assertEqual(app_rec.status, "PENDING")
        self.assertEqual(app_rec.applicant_id, applicant.id)
        self.assertIsNone(app_rec.academy_id)

        # Verify audit log was created
        audit = AuditLog.query.filter_by(action_type="ACADEMY_APPLICATION_SUBMITTED", target_id=app_rec.id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user_id, applicant.id)

    def test_02_prevent_duplicate_pending_applications(self):
        """User cannot submit a second application while one is already pending."""
        applicant = self._create_user("applicant_alice", "alice@test.com")
        db.session.commit()

        submit_academy_application(applicant.id, {
            "name": "Alice Tennis Club",
            "contact_email": "alice@test.com"
        })

        with self.assertRaises(ValueError) as ctx:
            submit_academy_application(applicant.id, {
                "name": "Alice Tennis Club 2",
                "contact_email": "alice2@test.com"
            })
        self.assertIn("already have an academy application pending", str(ctx.exception))

    def test_03_non_superadmin_cannot_verify_academy(self):
        """Regular users and support staff are barred from verifying academies."""
        applicant = self._create_user("applicant_carol", "carol@test.com")
        support_user = self._create_user("support_dan", "dan@support.test", role="support")
        regular_user = self._create_user("reg_user", "reg@test.com", role="user")
        db.session.commit()

        app_rec = submit_academy_application(applicant.id, {
            "name": "Carol Racquet Center",
            "contact_email": "carol@test.com"
        })

        # Regular user attempt
        with self.assertRaises(PermissionError):
            review_academy_application(app_rec.id, reviewer_user=regular_user, decision="APPROVED")

        # Support user attempt
        with self.assertRaises(PermissionError):
            review_academy_application(app_rec.id, reviewer_user=support_user, decision="APPROVED")

    def test_04_platform_superadmin_rejects_application(self):
        """Superadmin rejects application with mandatory reason; no academy is activated."""
        applicant = self._create_user("applicant_dave", "dave@test.com")
        superadmin = self._create_user("super_admin_eva", "eva@baseline.test", role="superadmin")
        db.session.commit()

        app_rec = submit_academy_application(applicant.id, {
            "name": "Dave Unverified Courts",
            "contact_email": "dave@test.com"
        })

        # Rejection without reason must fail
        with self.assertRaises(ValueError):
            review_academy_application(app_rec.id, reviewer_user=superadmin, decision="REJECTED", rejection_reason="")

        # Valid rejection
        reviewed_app, academy = review_academy_application(
            app_rec.id,
            reviewer_user=superadmin,
            decision="REJECTED",
            rejection_reason="Insufficient facility proof and unverified phone contact."
        )

        self.assertEqual(reviewed_app.status, "REJECTED")
        self.assertIsNone(academy)
        self.assertEqual(reviewed_app.reviewed_by_id, superadmin.id)
        self.assertIn("Insufficient facility proof", reviewed_app.rejection_reason)

        # Applicant must have 0 academies and 0 academy admin memberships
        self.assertEqual(Academy.query.filter_by(owner_id=applicant.id).count(), 0)
        self.assertEqual(AcademyMember.query.filter_by(user_id=applicant.id).count(), 0)

    def test_05_platform_superadmin_approves_application(self):
        """Superadmin approves application; active Academy created and applicant appointed Owner."""
        applicant = self._create_user("applicant_frank", "frank@vanguard.test")
        superadmin = self._create_user("super_frank_rev", "super_rev@baseline.test", role="superadmin")
        db.session.commit()

        app_rec = submit_academy_application(applicant.id, {
            "name": "Vanguard Tennis Center",
            "description": "12 tournament-standard hard courts.",
            "address": "500 Grand Slam Way",
            "city": "Dallas",
            "state": "TX",
            "country": "USA",
            "contact_email": "contact@vanguard.test",
            "contact_phone": "+1 214-555-0199",
            "sports_offered": "Tennis",
            "website_url": "https://vanguard.test"
        })

        reviewed_app, academy = review_academy_application(
            app_rec.id,
            reviewer_user=superadmin,
            decision="APPROVED"
        )

        self.assertIsNotNone(academy)
        self.assertEqual(academy.status, "ACTIVE")
        self.assertEqual(academy.name, "Vanguard Tennis Center")
        self.assertEqual(academy.owner_id, applicant.id)
        self.assertEqual(academy.verified_by_id, superadmin.id)
        self.assertIsNotNone(academy.verified_at)

        # Verify applicant is enrolled as Owner
        membership = AcademyMember.query.filter_by(academy_id=academy.id, user_id=applicant.id).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, "owner")
        self.assertEqual(membership.membership_status, "ACTIVE")

        # Verify application record is updated
        self.assertEqual(reviewed_app.status, "APPROVED")
        self.assertEqual(reviewed_app.academy_id, academy.id)


if __name__ == '__main__':
    unittest.main()
