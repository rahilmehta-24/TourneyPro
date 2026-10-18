import unittest
import os
import tempfile
from app import create_app
from app.domain.models import db, User, Tournament, Category, Participant, Match
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

    def test_02_sqlite_batch_mode_enabled(self):
        """Verify that render_as_batch is enabled on the migrate extension"""
        migrate = self.app.extensions.get('migrate')
        self.assertIsNotNone(migrate)
        self.assertTrue(migrate.configure_args.get('render_as_batch'))
