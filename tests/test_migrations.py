import unittest
import os
import tempfile
from app import create_app
from app.domain.models import (
    db, User, Tournament, Category, Participant, Match, Group, PlayerCategoryTier, TeamMember, Registration
)
from flask_migrate import upgrade


class MigrationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret'
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{cls.db_path}'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.mkdtemp()

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def test_01_migrations_baseline_head(self):
        """Verify that Flask-Migrate baseline head revision exists"""
        with self.app.app_context():
            # Apply upgrade to test database
            upgrade()
            # Verify tables exist
            self.assertTrue(hasattr(User, '__table__'))
            self.assertTrue(hasattr(Tournament, '__table__'))
            self.assertTrue(hasattr(Category, '__table__'))
            self.assertTrue(hasattr(Participant, '__table__'))
            self.assertTrue(hasattr(Match, '__table__'))
            self.assertTrue(hasattr(Group, '__table__'))
            self.assertTrue(hasattr(PlayerCategoryTier, '__table__'))
            self.assertTrue(hasattr(TeamMember, '__table__'))
            self.assertTrue(hasattr(Registration, '__table__'))

            # Verify columns added in Phase 1
            self.assertIn('start_time', Group.__table__.columns)
            self.assertIn('assigned_courts', Group.__table__.columns)
            self.assertIn('parent_match_id', Match.__table__.columns)
            self.assertIn('rubber_type', Match.__table__.columns)
            self.assertIn('rubber_number', Match.__table__.columns)
            self.assertIn('p1_player1_id', Match.__table__.columns)
            self.assertIn('p1_player2_id', Match.__table__.columns)
            self.assertIn('p2_player1_id', Match.__table__.columns)
            self.assertIn('p2_player2_id', Match.__table__.columns)
            self.assertIn('payment_method', Registration.__table__.columns)
            self.assertIn('payment_method', Participant.__table__.columns)
            self.assertIn('payment_status', Participant.__table__.columns)

            # Verify category scheduling columns from 21e2eb139372
            self.assertIn('start_date', Category.__table__.columns)
            self.assertIn('end_date', Category.__table__.columns)
            self.assertIn('start_time', Category.__table__.columns)
            self.assertIn('end_time', Category.__table__.columns)
            self.assertIn('daily_schedule', Category.__table__.columns)

    def test_02_sqlite_batch_mode_enabled(self):
        """Verify that render_as_batch is enabled on the migrate extension"""
        migrate = self.app.extensions.get('migrate')
        self.assertIsNotNone(migrate)
        self.assertTrue(migrate.configure_args.get('render_as_batch'))
