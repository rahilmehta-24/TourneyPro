import os
import tempfile
import unittest
from datetime import date

from app import create_app
from app.domain.models import (
    Category,
    Group,
    Match,
    Participant,
    Player,
    PlayerCategoryTier,
    Registration,
    TeamMember,
    Tournament,
    User,
    db,
)
from app.services.format_engine.group_stage.logic import GroupStageFormat


class GroupStructureAndLuckyLosersTestCase(unittest.TestCase):
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
            db.session.remove()
            Match.query.delete()
            TeamMember.query.delete()
            PlayerCategoryTier.query.delete()
            Registration.query.delete()
            Participant.query.delete()
            Group.query.delete()
            Category.query.delete()
            Tournament.query.delete()
            Player.query.delete()
            User.query.delete()
            db.session.commit()

            admin = User(username='struct_admin', email='struct_admin@test.com', role='admin')
            admin.set_password('password123')
            db.session.add(admin)
            db.session.flush()
            self.admin_id = admin.id

            tournament = Tournament(
                name='Structure Cup 2026',
                url_slug='structure-cup-2026',
                user_id=admin.id,
                start_date=date(2026, 12, 1),
                end_date=date(2026, 12, 5),
                num_courts=4,
                status='setup',
            )
            db.session.add(tournament)
            db.session.flush()
            self.tournament_id = tournament.id
            self.slug = tournament.url_slug
            db.session.commit()

        self.client = self.app.test_client()
        resp = self.client.post(
            '/login',
            data={'username': 'struct_admin', 'password': 'password123'},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)

    def _seed_players_and_tiers(self, category_id, total_players, k=5):
        letters = list('ABCDEFGH'[:k])
        for i in range(total_players):
            p = Player(
                name=f'Player {i + 1:02d}',
                gender='Male',
                age_category='Open',
            )
            db.session.add(p)
            db.session.flush()
            db.session.add(
                Registration(
                    tournament_id=self.tournament_id,
                    category_id=category_id,
                    user_id=self.admin_id,
                    player_id=p.id,
                    status='approved',
                    payment_status='paid',
                )
            )
            if i < (total_players // k) * k:
                tier = letters[i // (total_players // k)]
                db.session.add(
                    PlayerCategoryTier(
                        category_id=category_id,
                        player_id=p.id,
                        tier=tier,
                        role='captain' if tier == 'A' else ('vice_captain' if tier == 'B' else 'player'),
                    )
                )
        db.session.commit()

    def test_01_structure_planner_for_11_teams_and_generalized_brackets(self):
        """N=11 teams (55/5) offers 2 uneven groups [6+5] direct AND 3 groups [4+4+3] + 2 Lucky Losers."""
        opts_11 = GroupStageFormat.compute_group_structure_options(11, qualifiers_per_group=2)
        by_id = {o['option_id']: o for o in opts_11}

        self.assertIn('g2_ll0', by_id)
        self.assertEqual(by_id['g2_ll0']['group_sizes'], [6, 5])
        self.assertEqual(by_id['g2_ll0']['direct_qualifiers'], 4)
        self.assertEqual(by_id['g2_ll0']['target_bracket'], 4)
        self.assertEqual(by_id['g2_ll0']['lucky_losers_needed'], 0)
        self.assertEqual(by_id['g2_ll0']['group_ties'], 25)

        self.assertIn('g3_ll2', by_id)
        self.assertEqual(by_id['g3_ll2']['group_sizes'], [4, 4, 3])
        self.assertEqual(by_id['g3_ll2']['direct_qualifiers'], 6)
        self.assertEqual(by_id['g3_ll2']['target_bracket'], 8)
        self.assertEqual(by_id['g3_ll2']['lucky_losers_needed'], 2)
        self.assertEqual(by_id['g3_ll2']['group_ties'], 15)
        self.assertTrue(by_id['g3_ll2']['is_recommended'])

        # Degenerate G=4 [3, 3, 3, 2] (min size == Q) should be omitted by default
        self.assertFalse(any(o['num_groups'] == 4 for o in opts_11))

        # Larger tournament N=18, Q=2 -> G=6 [3x6] has 12 direct + 4 LL -> 16-Team Bracket
        opts_18 = GroupStageFormat.compute_group_structure_options(18, qualifiers_per_group=2)
        by_id_18 = {o['option_id']: o for o in opts_18}
        self.assertIn('g6_ll4', by_id_18)
        self.assertEqual(by_id_18['g6_ll4']['target_bracket'], 16)
        self.assertEqual(by_id_18['g6_ll4']['lucky_losers_needed'], 4)

    def test_02_draft_structure_switch_manual_group_swap_and_leftover_dummy_flow(self):
        """
        55 players (11 teams) & 57 players (11 teams + 2 leftover -> 3 Dummy -> Replace via Late Entry):
        tests structure configuration, auto-draft distribution, manual team group swap preservation.
        """
        # Create category via HTTP
        res = self.client.post(
            f'/tournaments/{self.slug}/categories/new',
            data={
                'name': 'Team Cup 11',
                'format': 'group_stage',
                'group_structure_mode': 'auto',
                'max_players_per_team': '5',
                'total_games': '7',
                'qualifiers_per_group': '2',
                'matches_per_team_pair': '1',
                'num_courts': '3',
                'avg_match_duration': '45',
            },
            follow_redirects=False,
        )
        self.assertIn(res.status_code, (302, 200))
        cat = Category.query.filter_by(tournament_id=self.tournament_id, name='Team Cup 11').first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.group_structure_mode, 'auto')

        # Seed 55 players (11 teams of 5)
        self._seed_players_and_tiers(cat.id, 55, k=5)

        draft_resp = self.client.get(f'/tournaments/{self.slug}/categories/{cat.id}/draft')
        self.assertEqual(draft_resp.status_code, 200)
        html = draft_resp.data.decode('utf-8')
        self.assertIn('2 Groups (6 + 5)', html)
        self.assertIn('3 Groups (4 + 4 + 3) + 2 Lucky Losers', html)

        # Configure 3 groups with Lucky Losers enabled
        cfg_resp = self.client.post(
            f'/tournaments/{self.slug}/categories/{cat.id}/configure-structure',
            data={
                'num_groups': '3',
                'allow_lucky_losers': 'true',
                'qualifiers_per_group': '2',
                'next_target': 'draft',
            },
            follow_redirects=True,
        )
        self.assertEqual(cfg_resp.status_code, 200)
        db.session.refresh(cat)
        self.assertEqual(cat.num_groups, 3)
        self.assertTrue(cat.allow_lucky_losers)
        groups = Group.query.filter_by(category_id=cat.id).order_by(Group.id).all()
        self.assertEqual([g.name for g in groups], ['Group A', 'Group B', 'Group C'])

        # Auto-create 11 teams -> check snake distribution [4, 4, 3]
        created = GroupStageFormat.auto_create_teams(cat.id)
        self.assertEqual(len(created), 11)
        sizes = sorted(
            [Participant.query.filter_by(category_id=cat.id, group_id=g.id).count() for g in groups],
            reverse=True,
        )
        self.assertEqual(sizes, [4, 4, 3])

        # Manually swap one team from Group A to Group C and verify generate() preserves it
        team_in_a = Participant.query.filter_by(category_id=cat.id, group_id=groups[0].id).first()
        swap_resp = self.client.post(
            f'/tournaments/{self.slug}/categories/{cat.id}/assign-team-group',
            data={'participant_id': str(team_in_a.id), 'group_id': str(groups[2].id)},
            follow_redirects=True,
        )
        self.assertEqual(swap_resp.status_code, 200)
        db.session.refresh(team_in_a)
        self.assertEqual(team_in_a.group_id, groups[2].id)

        all_teams = Participant.query.filter_by(category_id=cat.id).all()
        generated_matches = GroupStageFormat.generate(cat, all_teams)
        db.session.refresh(team_in_a)
        self.assertEqual(team_in_a.group_id, groups[2].id)
        # Sizes after swap are [3, 4, 4] -> C(3,2)+C(4,2)+C(4,2) = 15 parent ties
        self.assertEqual(len(generated_matches), 15)

        # Verify leftover + dummy + late-entry replacement on a second 57-player category
        cat2 = Category(
            tournament_id=self.tournament_id,
            name='Leftover Test League',
            format='group_stage',
            has_group_stage=True,
            max_players_per_team=5,
            num_groups=2,
            qualifiers_per_group=2,
            total_games=7,
            group_structure_mode='auto',
        )
        db.session.add(cat2)
        db.session.commit()
        self._seed_players_and_tiers(cat2.id, 57, k=5)

        draft2 = self.client.get(f'/tournaments/{self.slug}/categories/{cat2.id}/draft')
        html2 = draft2.data.decode('utf-8')
        self.assertIn('3 More Player(s) Required for Team 12', html2)
        self.assertIn('Fill 3 Dummy / TBD Slots', html2)

        # Fill 3 Dummy slots -> reaches 60 players (12 teams exact)
        dummy_resp = self.client.post(
            f'/tournaments/{self.slug}/categories/{cat2.id}/add-dummy-players',
            data={'count': '3'},
            follow_redirects=True,
        )
        self.assertEqual(dummy_resp.status_code, 200)
        dummy_player = Player.query.filter(Player.name.like('TBD / Dummy Player #%')).first()
        self.assertIsNotNone(dummy_player)
        self.assertNotIn('More Player(s) Required', dummy_resp.data.decode('utf-8'))

        # Replace that Dummy with a real Late-Entry player in place
        late_resp = self.client.post(
            f'/tournaments/{self.slug}/categories/{cat2.id}/quick-late-entry',
            data={
                'player_name': 'Rohan Late Entry',
                'player_mobile': '9876543210',
                'player_gender': 'Male',
                'replace_dummy_id': str(dummy_player.id),
            },
            follow_redirects=True,
        )
        self.assertEqual(late_resp.status_code, 200)
        db.session.refresh(dummy_player)
        self.assertEqual(dummy_player.name, 'Rohan Late Entry')

    def test_03_uneven_lucky_losers_manual_chit_draw_and_r1_rematch_avoidance(self):
        """
        3 uneven groups (4 + 4 + 3 = 11 teams), Q=2, allow_lucky_losers=True:
        - Normalizes Group C (2 ties) fairly against Group A/B (3 ties).
        - Supports organizer manual Chit Draw `lucky_loser_ids` in /start-knockout.
        - Produces 8-team Quarter-Finals (4 matches, 0 byes) with zero same-group R1 clashes.
        """
        cat = Category(
            tournament_id=self.tournament_id,
            name='Uneven 11-Team Cup',
            format='group_stage',
            has_group_stage=True,
            max_players_per_team=5,
            num_groups=3,
            qualifiers_per_group=2,
            allow_lucky_losers=True,
            total_games=7,
            status='in_progress',
        )
        db.session.add(cat)
        db.session.flush()

        ga = Group(category_id=cat.id, name='Group A')
        gb = Group(category_id=cat.id, name='Group B')
        gc = Group(category_id=cat.id, name='Group C')
        db.session.add_all([ga, gb, gc])
        db.session.flush()

        def make_team(name, grp):
            t = Participant(tournament_id=self.tournament_id, category_id=cat.id, group_id=grp.id, name=name)
            db.session.add(t)
            db.session.flush()
            return t

        a1, a2, a3, a4 = [make_team(f'A{i}', ga) for i in range(1, 5)]
        b1, b2, b3, b4 = [make_team(f'B{i}', gb) for i in range(1, 5)]
        c1, c2, c3 = [make_team(f'C{i}', gc) for i in range(1, 4)]

        m_num = [1]

        def add_tie(grp, t1, t2, s1, s2):
            m = Match(
                tournament_id=self.tournament_id,
                category_id=cat.id,
                group_id=grp.id,
                round=1,
                match_number=m_num[0],
                participant1_id=t1.id,
                participant2_id=t2.id,
                winner_id=t1.id if s1 > s2 else t2.id,
                score1=str(s1),
                score2=str(s2),
                status='completed',
                match_type='group_stage',
            )
            m_num[0] += 1
            db.session.add(m)

        # Group A (4 teams, 3 ties each): A1 3-0, A2 2-1, A3 1-2 (-3 diff), A4 0-3
        add_tie(ga, a1, a2, 14, 7)
        add_tie(ga, a1, a3, 15, 6)
        add_tie(ga, a1, a4, 16, 5)
        add_tie(ga, a2, a3, 13, 8)
        add_tie(ga, a2, a4, 14, 7)
        add_tie(ga, a3, a4, 12, 9)  # A3: 1W-2L, pts=26, conceded=31 (-5 diff -> -1.67 avg)

        # Group B (4 teams, 3 ties each): B1 3-0, B2 2-1, B3 1-2 (+1 diff), B4 0-3
        add_tie(gb, b1, b2, 13, 8)
        add_tie(gb, b1, b3, 11, 10)
        add_tie(gb, b1, b4, 15, 6)
        add_tie(gb, b2, b3, 11, 10)
        add_tie(gb, b2, b4, 14, 7)
        add_tie(gb, b3, b4, 15, 6)  # B3: 1W-2L, pts=35, conceded=28 (+7? Wait 10+10+15=35 vs 11+11+6=28 -> +7 -> +2.33 avg)

        # Group C (3 teams, 2 ties each): C1 2-0, C2 1-1, C3 0-2 -> OR make C3 1-1?
        # Wait: let C3 be 1W-1L (3-way tie on 1-1 resolved in Group C so C3 is 3rd on fewer games, but 50% win rate > 33.3%!)
        add_tie(gc, c1, c2, 15, 6)
        add_tie(gc, c2, c3, 13, 8)
        add_tie(gc, c3, c1, 11, 10)  # All 1-1! Pts: C1=25, C2=19, C3=19 -> H2H C2 beat C3 so C3 ranks 3rd with 1W-1L (50% win rate!)
        db.session.commit()

        preview = GroupStageFormat.get_knockout_qualification_preview(cat)
        self.assertTrue(preview['is_uneven_groups'])
        self.assertEqual(len(preview['direct_qualifiers']), 6)
        self.assertEqual(preview['target_bracket'], 8)
        self.assertEqual(preview['slots_to_fill'], 2)

        # Normalized per-tie check: C3 (1W-1L = 50% win rate in 2 ties, 19 raw pts) MUST rank ahead of A3/B3 (1W-2L = 33.3% win rate in 3 ties)!
        top_ll_ids = preview['recommended_ll_ids']
        self.assertEqual(len(top_ll_ids), 2)
        self.assertIn(c3.id, top_ll_ids)
        self.assertIn(b3.id, top_ll_ids)

        # Reject wrong number of manually selected Lucky Losers (1 instead of 2)
        bad_res = self.client.post(
            f'/tournaments/{self.slug}/categories/{cat.id}/start-knockout',
            data={'lucky_loser_ids': [str(c3.id)]},
            follow_redirects=True,
        )
        self.assertEqual(bad_res.status_code, 200)
        self.assertEqual(Match.query.filter_by(category_id=cat.id, match_type='knockout').count(), 0)

        # Organizer manually picks (via Chit Draw) A3 and C3 as the 2 Lucky Losers
        ok_res = self.client.post(
            f'/tournaments/{self.slug}/categories/{cat.id}/start-knockout',
            data={'lucky_loser_ids': [str(a3.id), str(c3.id)]},
            follow_redirects=True,
        )
        self.assertEqual(ok_res.status_code, 200)

        ko_parent_matches = Match.query.filter_by(
            category_id=cat.id, match_type='knockout', parent_match_id=None
        ).all()
        ko_r1 = [m for m in ko_parent_matches if m.round == 1]
        # 8-team Quarter-Finals -> 4 Round-1 matches, all with real teams (no Byes!)
        self.assertEqual(len(ko_r1), 4)
        for m in ko_r1:
            self.assertIsNotNone(m.participant1_id)
            self.assertIsNotNone(m.participant2_id)
            p1 = Participant.query.get(m.participant1_id)
            p2 = Participant.query.get(m.participant2_id)
            # Verify Round-1 same-group rematch avoidance eliminated intra-group R1 matches!
            self.assertNotEqual(p1.group_id, p2.group_id)

        # Selected Lucky Losers A3 and C3 are indeed in the knockout bracket (B3 is not)
        r1_team_ids = {m.participant1_id for m in ko_r1} | {m.participant2_id for m in ko_r1}
        self.assertIn(a3.id, r1_team_ids)
        self.assertIn(c3.id, r1_team_ids)
        self.assertNotIn(b3.id, r1_team_ids)

    def test_04_generalized_lucky_losers_16_bracket(self):
        """5 groups x Top 2 qualifiers (10 direct) + 6 Lucky Losers -> 16-Team Bracket (not capped at 8)."""
        cat = Category(
            tournament_id=self.tournament_id,
            name='Big 16-Team Qualifier Cup',
            format='group_stage',
            has_group_stage=True,
            max_players_per_team=1,
            num_groups=5,
            qualifiers_per_group=2,
            allow_lucky_losers=True,
            status='in_progress',
        )
        db.session.add(cat)
        db.session.flush()

        for g_idx in range(5):
            grp = Group(category_id=cat.id, name=f'Group {chr(65 + g_idx)}')
            db.session.add(grp)
            db.session.flush()
            teams = []
            for t_idx in range(4):
                p = Participant(tournament_id=self.tournament_id, category_id=cat.id, group_id=grp.id, name=f'G{g_idx}T{t_idx}')
                db.session.add(p)
                db.session.flush()
                teams.append(p)
            # Clear ranking order inside each group
            db.session.add(Match(
                tournament_id=self.tournament_id, category_id=cat.id, group_id=grp.id,
                round=1, match_number=g_idx * 2 + 1,
                participant1_id=teams[0].id, participant2_id=teams[1].id, winner_id=teams[0].id,
                score1='6', score2='2', status='completed', match_type='group_stage'
            ))
            db.session.add(Match(
                tournament_id=self.tournament_id, category_id=cat.id, group_id=grp.id,
                round=1, match_number=g_idx * 2 + 2,
                participant1_id=teams[2].id, participant2_id=teams[3].id, winner_id=teams[2].id,
                score1='6', score2='4', status='completed', match_type='group_stage'
            ))
        db.session.commit()

        ko_matches = GroupStageFormat.generate_knockout_from_groups(cat)
        r1 = [m for m in ko_matches if m.get('round') == 1]
        self.assertEqual(len(r1), 8)  # 16-team bracket => 8 Round-1 matches!


if __name__ == '__main__':
    unittest.main()

