import os
import tempfile
import unittest
from datetime import date, datetime, time
from app import create_app
from app.domain.models import db, Tournament, Category, Participant, Match, Group
from app.services.format_engine.round_robin.logic import RoundRobinFormat
from app.services.format_engine.group_stage.logic import GroupStageFormat
from app.services.utils.scheduler import auto_schedule_tournament


class RoundRobinTournamentDesignTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(cls.db_fd)

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret"
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
            os.unlink(cls.db_path)

    def setUp(self):
        db.session.begin_nested()

    def tearDown(self):
        db.session.rollback()

    def test_01_circle_method_even_and_odd_group_rounds(self):
        """Test Berger / circle method pairing, round assignments, and bye handling."""
        # 1. Even group of 4 players -> 3 rounds, 2 matches per round, each plays once per round
        p_even = [Participant(id=i + 1, name=f"P{i + 1}") for i in range(4)]
        fixtures_even = RoundRobinFormat.generate_fixtures_circle_method(p_even)
        self.assertEqual(len(fixtures_even), 6)

        rounds_even = {}
        for f in fixtures_even:
            r = f["round"]
            rounds_even.setdefault(r, []).append(f)

        self.assertEqual(len(rounds_even), 3)  # 3 rounds
        for r, m_list in rounds_even.items():
            self.assertEqual(len(m_list), 2)  # 2 matches per round
            players_in_round = set()
            for m in m_list:
                players_in_round.add(m["participant1_id"])
                players_in_round.add(m["participant2_id"])
            self.assertEqual(len(players_in_round), 4)  # Everyone plays once

        # Final round flag
        self.assertTrue(all(m["is_final_group_round"] for m in rounds_even[3]))
        self.assertFalse(any(m["is_final_group_round"] for m in rounds_even[1]))

        # 2. Odd group of 3 players -> 3 rounds, 1 match per round (1 bye per round)
        p_odd = [Participant(id=i + 10, name=f"U{i + 1}") for i in range(3)]
        fixtures_odd = RoundRobinFormat.generate_fixtures_circle_method(p_odd)
        self.assertEqual(len(fixtures_odd), 3)  # 3 matches total
        rounds_odd = {f["round"]: f for f in fixtures_odd}
        self.assertEqual(len(rounds_odd), 3)
        self.assertTrue(rounds_odd[3]["is_final_group_round"])

    def test_02_points_mode_a_standings_and_tiebreakers(self):
        """Test Mode A points-based standings: 1 game to 21, win by 2, cap 25, 2-way H2H, 3-way mini-table."""
        t = Tournament(name="City Open", url_slug="city-open-pts", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(
            tournament_id=t.id,
            name="Men's Singles",
            format="round_robin",
            scoring_format="points",
            points_to_win=21,
            win_by_margin=2,
            score_cap=25,
            status="in_progress",
        )
        db.session.add(cat)
        db.session.flush()

        p1 = Participant(tournament_id=t.id, category_id=cat.id, name="P1", manual_seed=1)
        p2 = Participant(tournament_id=t.id, category_id=cat.id, name="P2", manual_seed=2)
        p3 = Participant(tournament_id=t.id, category_id=cat.id, name="P3", manual_seed=3)
        p4 = Participant(tournament_id=t.id, category_id=cat.id, name="P4", manual_seed=4)
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # P1 beat P2: 21-17
        # P1 beat P3: 21-14
        # P1 beat P4: 21-19
        # P2 beat P3: 21-18
        # P2 beat P4: 21-16
        # P3 beat P4: 25-23 (cap reached)
        m1 = Match(tournament_id=t.id, category_id=cat.id, round=1, match_number=1, participant1_id=p1.id, participant2_id=p2.id, winner_id=p1.id, score1="21-17", status="completed", match_type="round_robin", scoring_format="points")
        m2 = Match(tournament_id=t.id, category_id=cat.id, round=1, match_number=2, participant1_id=p1.id, participant2_id=p3.id, winner_id=p1.id, score1="21-14", status="completed", match_type="round_robin", scoring_format="points")
        m3 = Match(tournament_id=t.id, category_id=cat.id, round=2, match_number=3, participant1_id=p1.id, participant2_id=p4.id, winner_id=p1.id, score1="21-19", status="completed", match_type="round_robin", scoring_format="points")
        m4 = Match(tournament_id=t.id, category_id=cat.id, round=2, match_number=4, participant1_id=p2.id, participant2_id=p3.id, winner_id=p2.id, score1="21-18", status="completed", match_type="round_robin", scoring_format="points")
        m5 = Match(tournament_id=t.id, category_id=cat.id, round=3, match_number=5, participant1_id=p2.id, participant2_id=p4.id, winner_id=p2.id, score1="21-16", status="completed", match_type="round_robin", scoring_format="points")
        m6 = Match(tournament_id=t.id, category_id=cat.id, round=3, match_number=6, participant1_id=p3.id, participant2_id=p4.id, winner_id=p3.id, score1="25-23", status="completed", match_type="round_robin", scoring_format="points")
        db.session.add_all([m1, m2, m3, m4, m5, m6])
        db.session.commit()

        standings = RoundRobinFormat.calculate_final_rankings(cat)
        db.session.refresh(p1)
        db.session.refresh(p2)
        db.session.refresh(p3)
        db.session.refresh(p4)

        self.assertEqual(p1.group_wins, 3)
        self.assertEqual(p1.group_points, 63)  # 21 + 21 + 21
        self.assertEqual(p1.group_points_conceded, 50)  # 17 + 14 + 19
        self.assertEqual(p1.group_point_diff, 13)
        self.assertEqual(p1.final_rank, 1)

        self.assertEqual(p2.group_wins, 2)
        self.assertEqual(p2.final_rank, 2)

        self.assertEqual(p3.group_wins, 1)
        self.assertEqual(p3.final_rank, 3)

        self.assertEqual(p4.group_wins, 0)
        self.assertEqual(p4.final_rank, 4)

    def test_03_walkover_and_retirement_target_completion(self):
        """Test walkover and retirement credit full target for differential calculations."""
        t = Tournament(name="City Open", url_slug="city-open-wo", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(
            tournament_id=t.id,
            name="Points Walkover",
            format="round_robin",
            scoring_format="points",
            points_to_win=21,
            status="in_progress",
        )
        db.session.add(cat)
        db.session.flush()

        p1 = Participant(tournament_id=t.id, category_id=cat.id, name="P1")
        p2 = Participant(tournament_id=t.id, category_id=cat.id, name="P2")
        db.session.add_all([p1, p2])
        db.session.commit()

        # Walkover match
        m_wo = Match(
            tournament_id=t.id,
            category_id=cat.id,
            round=1,
            match_number=1,
            participant1_id=p1.id,
            participant2_id=p2.id,
            winner_id=p1.id,
            score1="W/O",
            status="completed",
            match_type="round_robin",
            scoring_format="points",
        )
        sw, sl, gw, gl, pw, pl, is_wo = RoundRobinFormat.parse_match_score(m_wo, p1.id, category=cat)
        self.assertTrue(is_wo)
        self.assertEqual(pw, 21)
        self.assertEqual(pl, 0)

        # Retirement match at 12-8
        m_ret = Match(
            tournament_id=t.id,
            category_id=cat.id,
            round=2,
            match_number=2,
            participant1_id=p1.id,
            participant2_id=p2.id,
            winner_id=p1.id,
            score1="12-8 RET",
            status="completed",
            match_type="round_robin",
            scoring_format="points",
        )
        sw, sl, gw, gl, pw, pl, is_ret = RoundRobinFormat.parse_match_score(m_ret, p1.id, category=cat)
        self.assertTrue(is_ret)
        self.assertEqual(pw, 21)  # Winner credited to target
        self.assertEqual(pl, 8)

    def test_04_group_stage_deterministic_cross_pairing_and_stage_targets(self):
        """Test deterministic cross-pairing (A1 vs B2, B1 vs A2) and elevated targets for SF and Final."""
        t = Tournament(name="City Open", url_slug="city-open-ko", status="in_progress")
        db.session.add(t)
        db.session.flush()

        cat = Category(
            tournament_id=t.id,
            name="Men's Singles GS",
            format="group_stage",
            has_group_stage=True,
            num_groups=2,
            qualifiers_per_group=2,
            scoring_format="points",
            points_to_win=21,
            knockout_scoring_format="points",
            semifinal_target=25,
            final_target=31,
            has_third_place_match=True,
            status="in_progress",
        )
        db.session.add(cat)
        db.session.flush()

        gA = Group(category_id=cat.id, name="Group A")
        gB = Group(category_id=cat.id, name="Group B")
        db.session.add_all([gA, gB])
        db.session.flush()

        # Group A
        a1 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gA.id, name="A1")
        a2 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gA.id, name="A2")
        a3 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gA.id, name="A3")
        # Group B
        b1 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gB.id, name="B1")
        b2 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gB.id, name="B2")
        b3 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gB.id, name="B3")
        db.session.add_all([a1, a2, a3, b1, b2, b3])
        db.session.commit()

        # Simulate Group A matches: a1 wins 2, a2 wins 1
        m_a1 = Match(tournament_id=t.id, category_id=cat.id, group_id=gA.id, round=1, match_number=1, participant1_id=a1.id, participant2_id=a2.id, winner_id=a1.id, score1="21-15", status="completed", match_type="group_stage")
        m_a2 = Match(tournament_id=t.id, category_id=cat.id, group_id=gA.id, round=2, match_number=2, participant1_id=a1.id, participant2_id=a3.id, winner_id=a1.id, score1="21-10", status="completed", match_type="group_stage")
        m_a3 = Match(tournament_id=t.id, category_id=cat.id, group_id=gA.id, round=3, match_number=3, participant1_id=a2.id, participant2_id=a3.id, winner_id=a2.id, score1="21-12", status="completed", match_type="group_stage")

        # Simulate Group B matches: b1 wins 2, b2 wins 1
        m_b1 = Match(tournament_id=t.id, category_id=cat.id, group_id=gB.id, round=1, match_number=4, participant1_id=b1.id, participant2_id=b2.id, winner_id=b1.id, score1="21-18", status="completed", match_type="group_stage")
        m_b2 = Match(tournament_id=t.id, category_id=cat.id, group_id=gB.id, round=2, match_number=5, participant1_id=b1.id, participant2_id=b3.id, winner_id=b1.id, score1="21-11", status="completed", match_type="group_stage")
        m_b3 = Match(tournament_id=t.id, category_id=cat.id, group_id=gB.id, round=3, match_number=6, participant1_id=b2.id, participant2_id=b3.id, winner_id=b2.id, score1="21-14", status="completed", match_type="group_stage")
        db.session.add_all([m_a1, m_a2, m_a3, m_b1, m_b2, m_b3])
        db.session.commit()

        ko_matches = GroupStageFormat.generate_knockout_from_groups(cat)
        self.assertEqual(len(ko_matches), 4)  # 2 SF + 1 Final + 1 Third Place

        # Semifinal 1: A1 vs B2 (Target 25)
        sf1 = next(m for m in ko_matches if m["round"] == 1 and m["match_number"] == 1)
        self.assertEqual(sf1["participant1_id"], a1.id)
        self.assertEqual(sf1["participant2_id"], b2.id)
        self.assertEqual(sf1["match_stage"], "semifinal")
        self.assertEqual(sf1["points_to_win"], 25)

        # Semifinal 2: B1 vs A2 (Target 25)
        sf2 = next(m for m in ko_matches if m["round"] == 1 and m["match_number"] == 2)
        self.assertEqual(sf2["participant1_id"], b1.id)
        self.assertEqual(sf2["participant2_id"], a2.id)
        self.assertEqual(sf2["match_stage"], "semifinal")
        self.assertEqual(sf2["points_to_win"], 25)

        # Final: Winner SF1 vs Winner SF2 (Target 31)
        final = next(m for m in ko_matches if m["round"] == 2 and m["match_number"] == 1)
        self.assertEqual(final["match_stage"], "final")
        self.assertEqual(final["points_to_win"], 31)

        # Third Place match
        tp = next(m for m in ko_matches if m["bracket_type"] == "third_place")
        self.assertEqual(tp["match_stage"], "third_place")

    def test_05_scheduler_synchronizes_final_group_round(self):
        """Test scheduler assigns concurrent start times for group final round on available courts."""
        t = Tournament(
            name="Schedule Sync Open",
            url_slug="sched-sync-open",
            num_courts=2,
            court_names="Court 1, Court 2",
            court_operating_start="08:00",
            court_operating_end="18:00",
            min_rest_minutes=30,
            avg_match_duration=60,
            status="in_progress",
        )
        db.session.add(t)
        db.session.flush()

        cat = Category(
            tournament_id=t.id,
            name="Group Final Sync",
            format="group_stage",
            has_group_stage=True,
            num_groups=1,
            status="in_progress",
        )
        db.session.add(cat)
        db.session.flush()

        grp = Group(category_id=cat.id, name="Group A")
        db.session.add(grp)
        db.session.flush()

        p = [Participant(tournament_id=t.id, category_id=cat.id, group_id=grp.id, name=f"Player {i + 1}") for i in range(4)]
        db.session.add_all(p)
        db.session.commit()

        fixtures = GroupStageFormat.generate(cat, p)
        created_matches = []
        for f in fixtures:
            m = Match(**f, tournament_id=t.id)
            db.session.add(m)
            created_matches.append(m)
        db.session.commit()

        # Run scheduler
        res = auto_schedule_tournament(t.id)
        self.assertEqual(res.get("scheduled"), 6)

        # Check final round matches (round 3)
        final_round_matches = [m for m in created_matches if m.round == 3]
        self.assertEqual(len(final_round_matches), 2)
        # Verify both final round matches share the exact same start time on different courts!
        self.assertEqual(final_round_matches[0].scheduled_time, final_round_matches[1].scheduled_time)
        self.assertNotEqual(final_round_matches[0].court_name, final_round_matches[1].court_name)

    def test_06_matrix_score_entry_and_rendering(self):
        """Test interactive matrix grid rendering and batch score updates via update_grid."""
        from app.domain.models import User

        # Create admin user
        admin = User.query.filter_by(username="matrix_admin").first()
        if not admin:
            admin = User(username="matrix_admin", email="admin@test.com", role="admin")
            admin.set_password("pass123")
            db.session.add(admin)
            db.session.flush()

        t = Tournament(
            name="Matrix Test Open",
            url_slug="matrix-test-open",
            user_id=admin.id,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 1),
            status="in_progress",
        )
        db.session.add(t)
        db.session.flush()

        cat = Category(
            tournament_id=t.id,
            name="Men's Points RR",
            format="group_stage",
            scoring_format="points",
            points_to_win=21,
            has_group_stage=True,
            num_groups=1,
            status="in_progress",
        )
        db.session.add(cat)
        db.session.flush()

        grp = Group(category_id=cat.id, name="Group A")
        db.session.add(grp)
        db.session.flush()

        p1 = Participant(tournament_id=t.id, category_id=cat.id, group_id=grp.id, name="A10")
        p2 = Participant(tournament_id=t.id, category_id=cat.id, group_id=grp.id, name="F10")
        p3 = Participant(tournament_id=t.id, category_id=cat.id, group_id=grp.id, name="G10")
        db.session.add_all([p1, p2, p3])
        db.session.commit()

        fixtures = GroupStageFormat.generate(cat, [p1, p2, p3])
        created_matches = []
        for f in fixtures:
            m = Match(**f, tournament_id=t.id)
            db.session.add(m)
            created_matches.append(m)
        db.session.commit()

        # 1. Test GET category view: verify Results Matrix Grid contains editable inputs for admin
        with self.app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = admin.id
                sess["_fresh"] = True

            resp = client.get(f"/tournaments/{t.url_slug}/categories/{cat.id}")
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertIn("Results Matrix Grid", html)
            self.assertIn("matrix-score-input", html)
            self.assertIn("Save Grid Scores", html)
            self.assertIn(f"match_{created_matches[0].id}_p1", html)

            # 2. Test POST /update_grid with separate p1 and p2 scores
            m0 = next(m for m in created_matches if m.participant1_id == p1.id)
            update_data = {
                f"match_{m0.id}_p1": "21",
                f"match_{m0.id}_p2": "17",
            }
            post_resp = client.post(
                f"/tournaments/{t.url_slug}/categories/{cat.id}/update_grid",
                data=update_data,
                follow_redirects=True,
            )
            self.assertEqual(post_resp.status_code, 200)

            db.session.refresh(m0)
            self.assertEqual(m0.status, "completed")
            self.assertEqual(m0.score1, "21")
            self.assertEqual(m0.score2, "17")
            self.assertEqual(m0.winner_id, m0.participant1_id)

            # Check participant points and differential updated
            db.session.refresh(p1)
            self.assertEqual(p1.group_wins, 1)
            self.assertEqual(p1.group_points, 21)
            self.assertEqual(p1.group_points_conceded, 17)
            self.assertEqual(p1.group_point_diff, 4)

            # 3. Test POST /update_grid with combined score "21-15"
            m1 = next(m for m in created_matches if m.id != m0.id)
            update_data2 = {
                f"match_{m1.id}_p1": "21-15",
            }
            post_resp2 = client.post(
                f"/tournaments/{t.url_slug}/categories/{cat.id}/update_grid",
                data=update_data2,
                follow_redirects=True,
            )
            self.assertEqual(post_resp2.status_code, 200)

            db.session.refresh(m1)
            self.assertEqual(m1.status, "completed")
            self.assertEqual(m1.score1, "21")
            self.assertEqual(m1.score2, "15")
            self.assertEqual(m1.winner_id, m1.participant1_id)

    def test_07_knockout_generation_order_of_play_and_winner_advancement(self):
        """Test knockout generation from round robin / groups, auto-scheduling onto Order of Play, and winner advancement to next round."""
        from app.services.utils.scheduler import get_order_of_play
        from app.web.controllers.category import sync_knockout_advancement

        t = Tournament(
            name="RR Knockout Advance Tournament",
            url_slug="rr-ko-advance-tourn",
            format="round_robin",
            num_courts=2,
            court_names="Court 1, Court 2",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 2),
            user_id=1,
        )
        db.session.add(t)
        db.session.flush()

        cat = Category(
            tournament_id=t.id,
            name="Open Singles",
            format="round_robin",
            has_group_stage=True,
            qualifiers_per_group=2,
            scoring_format="points",
            knockout_scoring_format="points",
            points_to_win=21,
            win_by_margin=2,
            semifinal_target=21,
            final_target=25,
            status="in_progress",
        )
        db.session.add(cat)
        db.session.flush()

        gA = Group(category_id=cat.id, name="Group A")
        gB = Group(category_id=cat.id, name="Group B")
        db.session.add_all([gA, gB])
        db.session.flush()

        pA1 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gA.id, name="A1")
        pA2 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gA.id, name="A2")
        pB1 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gB.id, name="B1")
        pB2 = Participant(tournament_id=t.id, category_id=cat.id, group_id=gB.id, name="B2")
        db.session.add_all([pA1, pA2, pB1, pB2])
        db.session.flush()

        # Complete group matches
        m_ga = Match(
            tournament_id=t.id,
            category_id=cat.id,
            group_id=gA.id,
            participant1_id=pA1.id,
            participant2_id=pA2.id,
            round=1,
            match_number=1,
            match_type="group_stage",
            status="completed",
            score1="21",
            score2="10",
            winner_id=pA1.id,
            scheduled_date=date(2026, 6, 1),
            scheduled_time=datetime.combine(date(2026, 6, 1), time(9, 0)),
            court_name="Court 1",
        )
        m_gb = Match(
            tournament_id=t.id,
            category_id=cat.id,
            group_id=gB.id,
            participant1_id=pB1.id,
            participant2_id=pB2.id,
            round=1,
            match_number=1,
            match_type="group_stage",
            status="completed",
            score1="21",
            score2="12",
            winner_id=pB1.id,
            scheduled_date=date(2026, 6, 1),
            scheduled_time=datetime.combine(date(2026, 6, 1), time(9, 0)),
            court_name="Court 2",
        )
        db.session.add_all([m_ga, m_gb])
        db.session.commit()

        # Calculate standings
        GroupStageFormat.calculate_group_standings(gA.id)
        GroupStageFormat.calculate_group_standings(gB.id)

        # Generate knockout from groups
        matches_data = GroupStageFormat.generate_knockout_from_groups(cat)
        created_ko = []
        for m_data in matches_data:
            m = Match(**m_data, tournament_id=t.id)
            db.session.add(m)
            created_ko.append(m)
        db.session.commit()

        # Verify auto-scheduling handles knockout matches
        auto_schedule_tournament(t.id)

        for m in created_ko:
            db.session.refresh(m)
            self.assertIsNotNone(m.court_name, f"Match {m.id} should have court assigned")
            self.assertIsNotNone(m.scheduled_time, f"Match {m.id} should have scheduled_time assigned")
            # Must be strictly after group match end (10:00 AM) + rest buffer (>= 10:45 AM)
            self.assertGreaterEqual(
                m.scheduled_time,
                datetime(2026, 6, 1, 10, 45),
                f"Knockout match {m.id} must be scheduled strictly after completion of league matches",
            )

        # Verify get_order_of_play includes knockout matches
        oop_data = get_order_of_play(t.url_slug)
        total_oop_matches = sum(len(matches) for matches in oop_data["courts"].values())
        self.assertGreaterEqual(total_oop_matches, 3)

        # Identify SF1, SF2, and Final
        sf1 = next(m for m in created_ko if m.round == 1 and m.match_number == 1)
        sf2 = next(m for m in created_ko if m.round == 1 and m.match_number == 2)
        final_m = next(m for m in created_ko if m.round == 2 and m.match_number == 1)

        self.assertIsNone(final_m.participant1_id)
        self.assertIsNone(final_m.participant2_id)

        # Complete SF1 with winner A1
        sf1.score1 = "21"
        sf1.score2 = "15"
        sf1.winner_id = sf1.participant1_id
        sf1.status = "completed"
        RoundRobinFormat.advance_match(sf1, cat, sf1.winner_id)
        db.session.commit()

        db.session.refresh(final_m)
        self.assertEqual(final_m.participant1_id, sf1.winner_id, "Winner of SF1 must advance to Final participant1")
        self.assertIsNone(final_m.participant2_id, "SF2 not yet played so participant2 remains None")

        # Complete SF2 with winner B1
        sf2.score1 = "21"
        sf2.score2 = "18"
        sf2.winner_id = sf2.participant1_id
        sf2.status = "completed"
        RoundRobinFormat.advance_match(sf2, cat, sf2.winner_id)
        db.session.commit()

        db.session.refresh(final_m)
        self.assertEqual(final_m.participant2_id, sf2.winner_id, "Winner of SF2 must advance to Final participant2")

        # Test self-healing sync_knockout_advancement if a match slot was somehow cleared
        final_m.participant1_id = None
        db.session.commit()
        sync_knockout_advancement(cat)
        db.session.refresh(final_m)
        self.assertEqual(final_m.participant1_id, sf1.winner_id, "sync_knockout_advancement must self-heal unpopulated next round slots")

    def test_08_per_person_entry_fee_multiplier(self):
        """Verify fees configured per person result in team_entry_fee = fee * 2 for doubles."""
        cat_singles = Category(
            name="Men's Singles",
            format="round_robin",
            entry_fee=500.0,
        )
        self.assertFalse(cat_singles.is_doubles)
        self.assertEqual(cat_singles.fee_multiplier, 1)
        self.assertEqual(cat_singles.team_entry_fee, 500.0)

        cat_doubles = Category(
            name="Men's Doubles",
            format="round_robin",
            entry_fee=500.0,
        )
        self.assertTrue(cat_doubles.is_doubles)
        self.assertEqual(cat_doubles.fee_multiplier, 2)
        self.assertEqual(cat_doubles.team_entry_fee, 1000.0)


if __name__ == "__main__":
    unittest.main()
