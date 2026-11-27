import unittest
import os
import tempfile
from app import create_app
from app.domain.models import (
    db, Tournament, Category, Participant, Match, Group, Registration,
    DeviceRegistration, InAppNotification, UserNotificationPreferences, ParticipantImportBatch
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
            # Verify tables exist in physical database schema
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            db_tables = set(inspector.get_table_names())
            for expected_table in (
                'users', 'tournaments', 'categories', 'participants', 'matches',
                'groups', 'player_category_tiers', 'team_members', 'registrations'
            ):
                # Account for table name variants or direct table inspection
                matching = [t for t in db_tables if expected_table.rstrip('s') in t]
                self.assertTrue(bool(matching), f"Table {expected_table} missing from schema")

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

            # Verify mobile notification and device tables from b7e2d91f4a01
            for notif_table in ('device_registrations', 'in_app_notifications', 'user_notification_preferences'):
                matching = [t for t in db_tables if notif_table.rstrip('s') in t]
                self.assertTrue(bool(matching), f"Notification table {notif_table} missing from schema")
            self.assertIn('device_token', DeviceRegistration.__table__.columns)
            self.assertIn('platform', DeviceRegistration.__table__.columns)
            self.assertIn('notification_type', InAppNotification.__table__.columns)
            self.assertIn('notify_match_called', UserNotificationPreferences.__table__.columns)

            # Verify flexible registration and bulk import columns and tables
            self.assertIn('format_status', Tournament.__table__.columns)
            self.assertIn('registration_status', Tournament.__table__.columns)
            self.assertIn('registration_opens_at', Tournament.__table__.columns)
            self.assertIn('is_published', Tournament.__table__.columns)

            self.assertIn('format_status', Category.__table__.columns)
            self.assertIn('registration_status', Category.__table__.columns)
            self.assertIn('is_registration_open', Category.__table__.columns)
            self.assertTrue(Category.__table__.columns['format'].nullable)

            matching_import = [t for t in db_tables if 'import_batch' in t]
            self.assertTrue(bool(matching_import), "Participant import batch table missing from schema")
            self.assertIn('file_hash', ParticipantImportBatch.__table__.columns)
            self.assertIn('error_data', ParticipantImportBatch.__table__.columns)

            # Verify dual stage scoring, targets, and group stats columns from f4a5b6c7d8e9
            self.assertIn('knockout_scoring_format', Category.__table__.columns)
            self.assertIn('win_by_margin', Category.__table__.columns)
            self.assertIn('score_cap', Category.__table__.columns)
            self.assertIn('semifinal_target', Category.__table__.columns)
            self.assertIn('final_target', Category.__table__.columns)
            self.assertIn('has_third_place_match', Category.__table__.columns)
            self.assertIn('tiebreak_at', Category.__table__.columns)
            self.assertIn('tiebreak_points', Category.__table__.columns)
            self.assertIn('final_num_sets', Category.__table__.columns)

            self.assertIn('group_points_conceded', Participant.__table__.columns)
            self.assertIn('group_point_diff', Participant.__table__.columns)
            self.assertIn('group_sets_won', Participant.__table__.columns)
            self.assertIn('group_sets_lost', Participant.__table__.columns)

            self.assertIn('match_stage', Match.__table__.columns)
            self.assertIn('is_final_group_round', Match.__table__.columns)
            self.assertIn('win_by_margin', Match.__table__.columns)
            self.assertIn('score_cap', Match.__table__.columns)

    def test_02_sqlite_batch_mode_enabled(self):
        """Verify that render_as_batch is enabled on the migrate extension"""
        migrate = self.app.extensions.get('migrate')
        self.assertIsNotNone(migrate)
        self.assertTrue(migrate.configure_args.get('render_as_batch'))
