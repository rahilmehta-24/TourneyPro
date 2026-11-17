"""
Unit and Integration Tests for Phase 2:
Platform Roles, Permissions, Scoped Evaluator, and Anti-Conflict Self-Scoring Defense.
"""

import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from app import create_app, db
from app.domain.models import (
    User, Player, Tournament, Category, Match, Participant,
    TournamentStaff, Academy, AcademyMember
)
from app.domain.constants import (
    PLATFORM_ROLE_SUPERADMIN,
    PLATFORM_ROLE_SUPPORT,
    PLATFORM_ROLE_USER,
    PERM_PLATFORM_ACADEMIES_VERIFY,
    PERM_PLATFORM_ACADEMIES_VIEW,
    PERM_PLATFORM_USERS_VIEW,
    PERM_PLATFORM_USERS_MANAGE,
    PERM_PLATFORM_AUDIT_VIEW,
    PERM_PLATFORM_CONFIG_MANAGE,
    PERM_ACADEMY_MANAGE,
    PERM_ACADEMY_MEMBERS_MANAGE,
    PERM_ACADEMY_MEMBERS_VIEW,
    PERM_ACADEMY_COACHES_ASSIGN,
    PERM_TOURNAMENT_CREATE,
    PERM_TOURNAMENT_MANAGE,
    PERM_TOURNAMENT_DRAW_MANAGE,
    PERM_TOURNAMENT_SCORE_SUBMIT,
)
from app.services.rbac_service import (
    has_permission, check_scoring_conflict_of_interest, check_scoring_authorization
)


class Phase2RolesAndPermissionsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-phase2-secret"
            JWT_SECRET_KEY = "test-phase2-jwt-secret"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{cls.db_path}"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            WTF_CSRF_ENABLED = False
            UPLOAD_FOLDER = tempfile.mkdtemp()

        cls.app = create_app(TestConfig)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        cls.app_context.pop()
        try:
            if os.path.exists(cls.db_path):
                os.remove(cls.db_path)
        except OSError:
            pass

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.rollback()
        db.drop_all()

    def _login(self, username, password="password123"):
        return self.client.post("/login", data={
            "username": username,
            "password": password
        }, follow_redirects=False)

    def _create_user(self, username, email, role="user", password="password123"):
        u = User(username=username, email=email, role=role, profile_completed=True, completion_percentage=100)
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
        return u

    def test_01_platform_superadmin_universal_permissions(self):
        """Superadmin has universal governance permissions across all layers."""
        superadmin = self._create_user("super_gov", "super@baseline.test", role="superadmin")
        db.session.commit()

        self.assertTrue(has_permission(superadmin, PERM_PLATFORM_ACADEMIES_VERIFY))
        self.assertTrue(has_permission(superadmin, PERM_PLATFORM_USERS_MANAGE))
        self.assertTrue(has_permission(superadmin, PERM_PLATFORM_AUDIT_VIEW))
        self.assertTrue(has_permission(superadmin, PERM_ACADEMY_MANAGE))
        self.assertTrue(has_permission(superadmin, PERM_TOURNAMENT_MANAGE))
        self.assertTrue(has_permission(superadmin, PERM_TOURNAMENT_SCORE_SUBMIT))

    def test_02_platform_support_strict_boundary_enforcement(self):
        """Platform Support can view users/academies but CANNOT verify academies or score matches."""
        support_user = self._create_user("support_agent_1", "support1@baseline.test", role="support")
        db.session.commit()

        # Permitted support capabilities
        self.assertTrue(has_permission(support_user, PERM_PLATFORM_USERS_VIEW))
        self.assertTrue(has_permission(support_user, PERM_PLATFORM_ACADEMIES_VIEW))

        # Strictly forbidden boundaries
        self.assertFalse(has_permission(support_user, PERM_PLATFORM_ACADEMIES_VERIFY))
        self.assertFalse(has_permission(support_user, PERM_PLATFORM_USERS_MANAGE))
        self.assertFalse(has_permission(support_user, PERM_PLATFORM_CONFIG_MANAGE))
        self.assertFalse(has_permission(support_user, PERM_ACADEMY_MANAGE))
        self.assertFalse(has_permission(support_user, PERM_TOURNAMENT_SCORE_SUBMIT))

        # Web Route Verification: Support can view /admin/users
        self._login("support_agent_1")
        res_view = self.client.get("/admin/users")
        self.assertEqual(res_view.status_code, 200)

        # Web Route Verification: Support CANNOT create, modify role, or delete users (403)
        res_create = self.client.post("/admin/users/create", data={"username": "hacker", "email": "hacker@test.com", "password": "pass"})
        self.assertEqual(res_create.status_code, 403)

        target_user = self._create_user("target_u", "target@baseline.test", role="user")
        db.session.commit()

        res_role = self.client.post(f"/admin/users/{target_user.id}/role", data={"role": "admin"})
        self.assertEqual(res_role.status_code, 403)

        res_del = self.client.post(f"/admin/users/{target_user.id}/delete")
        self.assertEqual(res_del.status_code, 403)

    def test_03_scoped_academy_permissions_and_tenant_isolation(self):
        """Enforces tenant isolation: Academy A admin cannot administer Academy B."""
        owner_a = self._create_user("owner_a", "owner_a@test.com", role="admin")
        admin_a = self._create_user("admin_a", "admin_a@test.com", role="user")
        coach_a = self._create_user("coach_a", "coach_a@test.com", role="user")
        member_a = self._create_user("member_a", "member_a@test.com", role="user")
        owner_b = self._create_user("owner_b", "owner_b@test.com", role="admin")

        academy_a = Academy(name="Apex Academy", url_slug="apex-academy", owner_id=owner_a.id, status="ACTIVE")
        academy_b = Academy(name="Beacon Academy", url_slug="beacon-academy", owner_id=owner_b.id, status="ACTIVE")
        db.session.add_all([academy_a, academy_b])
        db.session.flush()

        # Memberships
        db.session.add_all([
            AcademyMember(academy_id=academy_a.id, user_id=admin_a.id, role="admin", membership_status="ACTIVE"),
            AcademyMember(academy_id=academy_a.id, user_id=coach_a.id, role="coach", membership_status="ACTIVE"),
            AcademyMember(academy_id=academy_a.id, user_id=member_a.id, role="member", membership_status="ACTIVE"),
        ])
        db.session.commit()

        scope_a = {"academy_id": academy_a.id, "academy": academy_a}
        scope_b = {"academy_id": academy_b.id, "academy": academy_b}

        # Owner A
        self.assertTrue(has_permission(owner_a, PERM_ACADEMY_MANAGE, scope=scope_a))
        self.assertTrue(has_permission(owner_a, PERM_ACADEMY_MEMBERS_MANAGE, scope=scope_a))
        self.assertFalse(has_permission(owner_a, PERM_ACADEMY_MANAGE, scope=scope_b))

        # Admin A
        self.assertTrue(has_permission(admin_a, PERM_ACADEMY_MANAGE, scope=scope_a))
        self.assertTrue(has_permission(admin_a, PERM_ACADEMY_MEMBERS_MANAGE, scope=scope_a))
        self.assertFalse(has_permission(admin_a, PERM_ACADEMY_MANAGE, scope=scope_b))

        # Coach A
        self.assertFalse(has_permission(coach_a, PERM_ACADEMY_MANAGE, scope=scope_a))
        self.assertFalse(has_permission(coach_a, PERM_ACADEMY_MEMBERS_MANAGE, scope=scope_a))
        self.assertTrue(has_permission(coach_a, PERM_ACADEMY_MEMBERS_VIEW, scope=scope_a))

        # Member A
        self.assertFalse(has_permission(member_a, PERM_ACADEMY_MANAGE, scope=scope_a))
        self.assertTrue(has_permission(member_a, PERM_ACADEMY_MEMBERS_VIEW, scope=scope_a))

    def test_04_scoped_tournament_roles_and_capabilities(self):
        """Validates granular Tournament Director, Manager, Draw Admin, and Scorer capabilities."""
        owner = self._create_user("t_owner", "towner@test.com", role="admin")
        director = self._create_user("t_dir", "tdir@test.com", role="user")
        draw_admin = self._create_user("t_draw", "tdraw@test.com", role="user")
        scorer = self._create_user("t_scorer", "tscorer@test.com", role="user")
        viewer = self._create_user("t_viewer", "tviewer@test.com", role="user")

        tournament = Tournament(name="City Open", url_slug="city-open", user_id=owner.id, status="in_progress")
        db.session.add(tournament)
        db.session.flush()

        db.session.add_all([
            TournamentStaff(tournament_id=tournament.id, user_id=director.id, role="director"),
            TournamentStaff(tournament_id=tournament.id, user_id=draw_admin.id, role="draw_admin"),
            TournamentStaff(tournament_id=tournament.id, user_id=scorer.id, role="scorer"),
        ])
        db.session.commit()

        scope = {"tournament_id": tournament.id, "tournament": tournament}

        # Owner has full rights
        self.assertTrue(has_permission(owner, PERM_TOURNAMENT_MANAGE, scope=scope))
        self.assertTrue(has_permission(owner, PERM_TOURNAMENT_DRAW_MANAGE, scope=scope))
        self.assertTrue(has_permission(owner, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope))

        # Director has full management rights
        self.assertTrue(has_permission(director, PERM_TOURNAMENT_MANAGE, scope=scope))
        self.assertTrue(has_permission(director, PERM_TOURNAMENT_DRAW_MANAGE, scope=scope))
        self.assertTrue(has_permission(director, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope))

        # Draw Admin can manage draws, but CANNOT score matches or manage tournament settings
        self.assertTrue(has_permission(draw_admin, PERM_TOURNAMENT_DRAW_MANAGE, scope=scope))
        self.assertFalse(has_permission(draw_admin, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope))
        self.assertFalse(has_permission(draw_admin, PERM_TOURNAMENT_MANAGE, scope=scope))

        # Scorer can submit scores, but CANNOT alter draws or manage settings
        self.assertTrue(has_permission(scorer, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope))
        self.assertFalse(has_permission(scorer, PERM_TOURNAMENT_DRAW_MANAGE, scope=scope))
        self.assertFalse(has_permission(scorer, PERM_TOURNAMENT_MANAGE, scope=scope))

        # Plain viewer has zero management rights
        self.assertFalse(has_permission(viewer, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope))
        self.assertFalse(has_permission(viewer, PERM_TOURNAMENT_DRAW_MANAGE, scope=scope))

    def test_05_anti_conflict_self_scoring_ban(self):
        """Fail-Closed Defense: An admin/host playing in a match CANNOT score their own match."""
        host = self._create_user("host_player", "hostp@test.com", role="admin")
        opponent_u = self._create_user("opp_player", "opp@test.com", role="user")
        neutral_scorer = self._create_user("neutral_ref", "ref@test.com", role="user")

        p_host = Player(user_id=host.id, name="Host Player", email="hostp@test.com", gender="Male", age_category="Open")
        p_opp = Player(user_id=opponent_u.id, name="Opponent Player", email="opp@test.com", gender="Male", age_category="Open")
        db.session.add_all([p_host, p_opp])
        db.session.flush()

        tournament = Tournament(name="Host Club Trophy", url_slug="host-club-trophy", user_id=host.id, status="in_progress")
        db.session.add(tournament)
        db.session.flush()

        category = Category(tournament_id=tournament.id, name="Men's Singles", gender="Male", age_category="Open", format="knockout")
        db.session.add(category)
        db.session.flush()

        part1 = Participant(tournament_id=tournament.id, category_id=category.id, player_id=p_host.id, name="Host Player")
        part2 = Participant(tournament_id=tournament.id, category_id=category.id, player_id=p_opp.id, name="Opponent Player")
        db.session.add_all([part1, part2])
        db.session.flush()

        match = Match(
            tournament_id=tournament.id,
            category_id=category.id,
            round="Final",
            match_number=1,
            participant1_id=part1.id,
            participant2_id=part2.id,
            status="pending"
        )
        db.session.add(match)

        # Neutral scorer staff appointment
        db.session.add(TournamentStaff(tournament_id=tournament.id, user_id=neutral_scorer.id, role="official"))
        db.session.commit()

        # 1. Host has permission to score tournament generally
        scope = {"tournament_id": tournament.id, "tournament": tournament}
        self.assertTrue(has_permission(host, PERM_TOURNAMENT_SCORE_SUBMIT, scope=scope))

        # 2. But for THIS match where Host is participant, check_scoring_conflict_of_interest must fail!
        with self.assertRaises(PermissionError) as ctx:
            check_scoring_conflict_of_interest(match, host)
        self.assertIn("Conflict of interest", str(ctx.exception))

        # check_scoring_authorization must also reject the host
        with self.assertRaises(PermissionError):
            check_scoring_authorization(match, host)

        # 3. Neutral referee CAN score the match without conflict
        self.assertTrue(check_scoring_authorization(match, neutral_scorer))

        # 4. Same check holds for Doubles: Partner cannot score match either
        partner_u = self._create_user("partner_u", "partner@test.com", role="user")
        p_partner = Player(user_id=partner_u.id, name="Partner Player", email="partner@test.com", gender="Male", age_category="Open")
        db.session.add(p_partner)
        db.session.flush()

        part1.player2_id = p_partner.id
        db.session.commit()

        with self.assertRaises(PermissionError):
            check_scoring_conflict_of_interest(match, partner_u)


if __name__ == '__main__':
    unittest.main()
