import unittest
import os
import tempfile
from datetime import date
from app import create_app
from app.domain.models import db, User, Tournament, Category, Participant, Player, Registration


class AdminApprovalBoxTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix='.db')
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = 'test-secret-key'
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
        self.client = self.app.test_client()
        Registration.query.delete()
        Participant.query.delete()
        Player.query.delete()
        Category.query.delete()
        Tournament.query.delete()
        User.query.delete()
        db.session.commit()

        # Create admin user
        self.admin = User(username='admin_tester', email='admin_tester@example.com', role='admin')
        self.admin.set_password('pass123')
        db.session.add(self.admin)
        db.session.commit()

        # Create tournament
        self.tournament = Tournament(
            name='Summer Tennis Championship',
            url_slug='summer-tennis-championship',
            user_id=self.admin.id,
            status='setup',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
            tournament_type='open',
        )
        db.session.add(self.tournament)
        db.session.commit()

        # Create category
        self.category = Category(
            tournament_id=self.tournament.id,
            name="Men's Singles",
            format='knockout',
            entry_fee=500.0,
            gender='Male',
            age_category='Open',
        )
        db.session.add(self.category)
        db.session.commit()

        # Log in client as admin
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.admin.id)
            sess['user_id'] = self.admin.id
            sess['role'] = 'admin'

    def tearDown(self):
        db.session.rollback()

    def test_01_approve_registration_online(self):
        """Admin approves registration with Online payment method and transaction ID"""
        player = Player(
            name='Rohan Bopanna',
            contact_number='9876543210',
            email='rohan@example.com',
            gender='Male',
            age_category='Open',
            dob=date(1995, 1, 1),
        )
        db.session.add(player)
        db.session.commit()

        reg = Registration(
            tournament_id=self.tournament.id,
            category_id=self.category.id,
            user_id=self.admin.id,
            player_id=player.id,
            status='pending',
            amount_due=500.0,
            transaction_id='UPI987654321012',
            payment_status='pending',
            payment_method='online',
        )
        db.session.add(reg)
        db.session.commit()

        # Post approval via Online
        resp = self.client.post(
            f'/t/{self.tournament.url_slug}/manage',
            data={
                'action': 'approve_registration',
                'registration_id': reg.id,
                'payment_method': 'online',
                'transaction_id': 'VERIFIED_UPI_12345',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers['Location'].endswith('#players'))

        # Verify DB records
        updated_reg = db.session.get(Registration, reg.id)
        self.assertEqual(updated_reg.status, 'approved')
        self.assertEqual(updated_reg.payment_status, 'paid')
        self.assertEqual(updated_reg.payment_method, 'online')
        self.assertEqual(updated_reg.transaction_id, 'VERIFIED_UPI_12345')

        participant = Participant.query.filter_by(
            tournament_id=self.tournament.id, player_id=player.id
        ).first()
        self.assertIsNotNone(participant)
        self.assertEqual(participant.payment_method, 'online')
        self.assertEqual(participant.payment_status, 'paid')
        self.assertEqual(participant.mobile, '9876543210')
        self.assertEqual(participant.email, 'rohan@example.com')

    def test_02_approve_registration_cash(self):
        """Admin approves registration with Cash payment method and optional receipt note"""
        player = Player(
            name='Sania Mirza',
            contact_number='9123456780',
            email='sania@example.com',
            gender='Female',
            age_category='Open',
            dob=date(1996, 5, 15),
        )
        db.session.add(player)
        db.session.commit()

        reg = Registration(
            tournament_id=self.tournament.id,
            category_id=self.category.id,
            user_id=self.admin.id,
            player_id=player.id,
            status='pending',
            amount_due=500.0,
            transaction_id=None,
            payment_status='pending',
        )
        db.session.add(reg)
        db.session.commit()

        # Post approval via Cash
        resp = self.client.post(
            f'/t/{self.tournament.url_slug}/manage',
            data={
                'action': 'approve_registration',
                'registration_id': reg.id,
                'payment_method': 'cash',
                'cash_notes': 'Receipt #Desk-101',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers['Location'].endswith('#players'))

        # Verify DB records
        updated_reg = db.session.get(Registration, reg.id)
        self.assertEqual(updated_reg.status, 'approved')
        self.assertEqual(updated_reg.payment_status, 'paid')
        self.assertEqual(updated_reg.payment_method, 'cash')
        self.assertIn('Receipt #Desk-101', updated_reg.transaction_id)

        participant = Participant.query.filter_by(
            tournament_id=self.tournament.id, player_id=player.id
        ).first()
        self.assertIsNotNone(participant)
        self.assertEqual(participant.payment_method, 'cash')
        self.assertEqual(participant.payment_status, 'paid')

    def test_03_manage_page_renders_approval_modal_and_payment_badges(self):
        """Manage page includes the approval modal elements and data attributes"""
        player = Player(
            name='Leander Paes',
            contact_number='9988776655',
            gender='Male',
            age_category='Open',
        )
        db.session.add(player)
        db.session.commit()

        reg = Registration(
            tournament_id=self.tournament.id,
            category_id=self.category.id,
            user_id=self.admin.id,
            player_id=player.id,
            status='pending',
            amount_due=500.0,
            transaction_id='UTR9988776655',
            payment_status='pending',
        )
        db.session.add(reg)
        db.session.commit()

        # Create an existing enrolled player with cash payment
        existing_p = Participant(
            tournament_id=self.tournament.id,
            category_id=self.category.id,
            name='Mahesh Bhupathi',
            payment_method='cash',
            payment_status='paid',
        )
        db.session.add(existing_p)
        db.session.commit()

        resp = self.client.get(f'/t/{self.tournament.url_slug}/manage')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Check modal existence
        self.assertIn('id="approveRegistrationModal"', html)
        self.assertIn('modalPayMethodOnline', html)
        self.assertIn('modalPayMethodCash', html)
        self.assertIn('open-approval-modal-btn', html)
        self.assertIn('UTR9988776655', html)
        # Check enrolled player cash badge
        self.assertIn('💵 Cash', html)

    def test_04_add_late_player_with_payment_method(self):
        """Admin adds late player with selected payment method"""
        resp = self.client.post(
            f'/t/{self.tournament.url_slug}/manage',
            data={
                'action': 'add_participant',
                'participant_name': 'Somdev Devvarman',
                'participant_age': '28',
                'participant_mobile': '9876501234',
                'participant_gender': 'Male',
                'category_id': self.category.id,
                'payment_method': 'online',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers['Location'].endswith('#players'))

        participant = Participant.query.filter_by(
            tournament_id=self.tournament.id, name='Somdev Devvarman'
        ).first()
        self.assertIsNotNone(participant)
        self.assertEqual(participant.payment_method, 'online')
        self.assertEqual(participant.payment_status, 'paid')

    def test_05_manage_page_renders_switch_dashboard_tab_and_tab_buttons(self):
        """Dashboard page contains working switchDashboardTab script and tab buttons"""
        resp = self.client.get(f'/t/{self.tournament.url_slug}/manage')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Tab buttons
        self.assertIn('id="tabBtnCategories"', html)
        self.assertIn('id="tabBtnSchedule"', html)
        self.assertIn('id="tabBtnPlayers"', html)
        self.assertIn('id="tabBtnSettings"', html)

        # Tab contents
        self.assertIn('id="tabContentCategories"', html)
        self.assertIn('id="tabContentSchedule"', html)
        self.assertIn('id="tabContentPlayers"', html)
        self.assertIn('id="tabContentSettings"', html)

        # Global switchDashboardTab definition
        self.assertIn('function switchDashboardTab(tabName)', html)
        self.assertIn("switchDashboardTab('categories')", html)

    def test_06_public_registration_renders_online_and_cash_options(self):
        """Public registration page offers Online (with QR) and Cash options when fee > 0"""
        self.tournament.status = 'registration'
        self.tournament.payment_upi_id = 'tourney@okhdfcbank'
        db.session.commit()

        resp = self.client.get(f'/t/{self.tournament.url_slug}/register')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn('playerPayMethodOnlineLabel', html)
        self.assertIn('playerPayMethodCashLabel', html)
        self.assertIn('id="online_payment_section"', html)
        self.assertIn('id="cash_payment_section"', html)
        self.assertIn('setRegPaymentMethod', html)

    def test_07_public_registration_submit_online_with_utr(self):
        """Public user registers choosing Online payment and providing valid UTR"""
        self.tournament.status = 'registration'
        self.tournament.payment_upi_id = 'tourney@okhdfcbank'
        db.session.commit()

        resp = self.client.post(
            f'/t/{self.tournament.url_slug}/register',
            data={
                'category_id': [self.category.id],
                'guest_name': 'Yuki Bhambri',
                'guest_age': '30',
                'guest_mobile': '9876543211',
                'guest_gender': 'Male',
                'payment_method': 'online',
                'transaction_id': 'UTR9876543211',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)

        reg = Registration.query.filter_by(
            tournament_id=self.tournament.id, category_id=self.category.id
        ).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.payment_method, 'online')
        self.assertEqual(reg.status, 'pending')
        self.assertEqual(reg.transaction_id, 'UTR9876543211')

    def test_08_public_registration_submit_cash_without_utr(self):
        """Public user registers choosing Cash payment without requiring UTR"""
        self.tournament.status = 'registration'
        self.tournament.payment_upi_id = 'tourney@okhdfcbank'
        db.session.commit()

        resp = self.client.post(
            f'/t/{self.tournament.url_slug}/register',
            data={
                'category_id': [self.category.id],
                'guest_name': 'Ramkumar Ramanathan',
                'guest_age': '29',
                'guest_mobile': '9876543212',
                'guest_gender': 'Male',
                'payment_method': 'cash',
            },
            follow_redirects=False,
        )
        self.assertEqual(resp.status_code, 302)

        reg = Registration.query.filter_by(
            tournament_id=self.tournament.id, category_id=self.category.id
        ).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.payment_method, 'cash')
        self.assertEqual(reg.status, 'pending')
        self.assertIn('CASH', reg.transaction_id)

    def test_09_manage_page_renders_cash_badge_for_pending_cash_registration(self):
        """Manage page shows '💵 Cash on Arrival' badge for registrations submitted via cash"""
        player = Player(
            name='Prajnesh Gunneswaran',
            contact_number='9876543213',
            gender='Male',
            age_category='Open',
        )
        db.session.add(player)
        db.session.commit()

        reg = Registration(
            tournament_id=self.tournament.id,
            category_id=self.category.id,
            user_id=self.admin.id,
            player_id=player.id,
            status='pending',
            amount_due=500.0,
            payment_method='cash',
            transaction_id='CASH / Pay at Venue',
            payment_status='pending',
        )
        db.session.add(reg)
        db.session.commit()

        resp = self.client.get(f'/t/{self.tournament.url_slug}/manage')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn('💵 Cash on Arrival', html)
        self.assertIn('data-payment-method="cash"', html)

    def test_10_create_tournament_renders_accessible_duration_tabs(self):
        """Create tournament page contains accessible quick duration tab pills and handlers"""
        resp = self.client.get('/tournaments/new')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Tablist and tabs
        self.assertIn('role="tablist"', html)
        self.assertIn('id="durationTab1"', html)
        self.assertIn('id="durationTab2"', html)
        self.assertIn('id="durationTab3"', html)
        self.assertIn('onclick="selectDurationDays(1)"', html)
        self.assertIn('onclick="selectDurationDays(2)"', html)

        # Global JS handler and turbo load listener
        self.assertIn('function selectDurationDays(days)', html)
        self.assertIn("addEventListener('turbo:load', initCreateTournamentPage)", html)

    def test_11_manage_tournament_renders_duration_presets(self):
        """Manage tournament schedule settings contains duration preset pills and handler"""
        resp = self.client.get(f'/t/{self.tournament.url_slug}/manage')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        self.assertIn('manage-dur-pill', html)
        self.assertIn('setManageDurationDays(1)', html)
        self.assertIn('function setManageDurationDays(days)', html)


if __name__ == '__main__':
    unittest.main()
