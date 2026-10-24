"""Draw Export Adapter for TourneyPro.

Converts saved Single Elimination and Knockout tournament matches into a
normalized, read-only presentation structure suitable for static HTML/PDF rendering.
STRICT DATA INTEGRITY:
Never generates, reseeds, shuffles, mutates, advances, or recalculates tournament data.
"""

from typing import Any, Dict, List, Optional
from app.domain.models import db, Tournament, Category, Match, Participant
from app.services.utils.scheduler import extract_participant_players


class DrawExportAdapter:
    """Read-only presentation adapter for saved tournament draws."""

    @staticmethod
    def get_round_name(round_num: int, total_rounds: int) -> str:
        """Return conventional round title based on proximity to the Final."""
        diff = total_rounds - round_num
        if diff == 0:
            return "Final"
        elif diff == 1:
            return "Semi-Finals"
        elif diff == 2:
            return "Quarter-Finals"
        elif diff == 3:
            return "Round of 16"
        elif diff == 4:
            return "Round of 32"
        elif diff == 5:
            return "Round of 64"
        elif diff == 6:
            return "Round of 128"
        return f"Round {round_num}"

    @staticmethod
    def format_participant_name(participant: Optional[Participant]) -> str:
        """Format singles player or doubles pair name cleanly."""
        if not participant:
            return "TBD"
        players = extract_participant_players(participant)
        names = [pl['name'] for pl in players if pl.get('name') and pl['name'] not in ('TBD', 'Bye')]
        if names:
            return " / ".join(names)
        return participant.name or "TBD"

    @staticmethod
    def format_participant_slot(participant: Optional[Participant], match: Match, is_p1: bool) -> Dict[str, Any]:
        """Build normalized display structure for a participant slot in a match."""
        is_bye = False
        p_name = ""
        seed = None

        if participant:
            p_name = DrawExportAdapter.format_participant_name(participant)
            seed = participant.manual_seed or participant.seed
        else:
            other_p = match.participant2 if is_p1 else match.participant1
            # Check if this slot represents a Bye
            is_bye_match = (
                (match.score1 == 'Bye' or match.score2 == 'Bye') or
                (match.round == 1 and other_p is not None and match.status == 'completed')
            )
            if is_bye_match:
                p_name = "Bye"
                is_bye = True
            else:
                p_name = "TBD"

        is_winner = False
        if match.winner_id and participant and match.winner_id == participant.id:
            is_winner = True

        raw_score = match.score1 if is_p1 else match.score2
        score_display = ""
        if raw_score:
            score_display = str(raw_score).strip()
        elif is_bye:
            score_display = "Bye"

        return {
            'id': participant.id if participant else None,
            'name': p_name,
            'seed': seed,
            'is_winner': is_winner,
            'is_bye': is_bye,
            'score': score_display
        }

    @staticmethod
    def format_match_card(match: Match, round_num: int, total_rounds: int) -> Dict[str, Any]:
        """Convert a database Match record into a normalized match card structure."""
        p1_data = DrawExportAdapter.format_participant_slot(match.participant1, match, is_p1=True)
        p2_data = DrawExportAdapter.format_participant_slot(match.participant2, match, is_p1=False)

        time_str = ""
        if match.scheduled_time:
            time_str = match.scheduled_time.strftime("%d/%m %I:%M %p")

        return {
            'id': match.id,
            'match_number': match.match_number,
            'round': match.round,
            'round_name': DrawExportAdapter.get_round_name(round_num, total_rounds),
            'status': match.status or 'pending',
            'court_name': match.court_name or '',
            'scheduled_time': time_str,
            'p1': p1_data,
            'p2': p2_data
        }

    @staticmethod
    def build_grid_cells(round_matches_list: List[List[Dict[str, Any]]], target_card: Optional[Dict[str, Any]] = None) -> List[List[Dict[str, Any]]]:
        """
        Generate mathematical table-grid cells for pixel-perfect bracket trees and connectors.
        Guarantees that match boxes and connectors align seamlessly without client-side JS.
        """
        num_rounds = len(round_matches_list)
        if num_rounds == 0 or len(round_matches_list[0]) == 0:
            return []

        num_r1_matches = len(round_matches_list[0])
        total_rows = num_r1_matches * 2

        rows_cells: List[List[Dict[str, Any]]] = [[] for _ in range(total_rows)]

        for r in range(num_rounds):
            span = 2 ** (r + 1)
            matches_in_r = round_matches_list[r]

            for m_idx, match in enumerate(matches_in_r):
                start_row = m_idx * span
                if start_row < total_rows:
                    rows_cells[start_row].append({
                        'type': 'match',
                        'data': match,
                        'rowspan': span,
                        'width': f"{max(12, int(72 / (num_rounds + (1 if target_card else 0))))}%"
                    })

            # Connectors between round r and round r+1
            if r < num_rounds - 1:
                half_sub = span // 2
                pairs_count = len(matches_in_r) // 2
                pair_span = 2 * span

                for p in range(pairs_count):
                    p_start = p * pair_span
                    if p_start + 3 * half_sub < total_rows:
                        # Sub-block 0: empty above top branch
                        rows_cells[p_start].append({'type': 'conn', 'rowspan': half_sub, 'classes': 'c-top-branch'})
                        rows_cells[p_start].append({'type': 'conn_stem', 'rowspan': half_sub, 'classes': 'c-empty'})

                        # Sub-block 1: top vertical bar
                        rows_cells[p_start + half_sub].append({'type': 'conn', 'rowspan': half_sub, 'classes': 'c-vert'})
                        rows_cells[p_start + half_sub].append({'type': 'conn_stem', 'rowspan': half_sub, 'classes': 'c-empty'})

                        # Sub-block 2: bottom vertical bar + stem to next round
                        rows_cells[p_start + 2 * half_sub].append({'type': 'conn', 'rowspan': half_sub, 'classes': 'c-vert'})
                        rows_cells[p_start + 2 * half_sub].append({'type': 'conn_stem', 'rowspan': half_sub, 'classes': 'c-stem'})

                        # Sub-block 3: empty below bottom branch
                        rows_cells[p_start + 3 * half_sub].append({'type': 'conn', 'rowspan': half_sub, 'classes': 'c-bot-branch'})
                        rows_cells[p_start + 3 * half_sub].append({'type': 'conn_stem', 'rowspan': half_sub, 'classes': 'c-empty'})

        # Target card (Champion or Section Advancer)
        if target_card:
            stem_start = total_rows // 2
            rows_cells[0].append({'type': 'target_stem_top', 'rowspan': stem_start, 'classes': 'c-empty'})
            rows_cells[stem_start].append({'type': 'target_stem', 'rowspan': total_rows - stem_start, 'classes': 'c-stem'})
            rows_cells[0].append({
                'type': 'target',
                'data': target_card,
                'rowspan': total_rows,
                'width': '16%'
            })

        return rows_cells

    @classmethod
    def adapt(cls, tournament: Tournament, category: Category) -> Dict[str, Any]:
        """
        Load authoritative persisted draw and adapt it into presentation pages.
        Does NOT alter or regenerate any records.
        """
        matches = Match.query.options(
            db.joinedload(Match.participant1),
            db.joinedload(Match.participant2),
            db.joinedload(Match.winner)
        ).filter(
            Match.category_id == category.id,
            Match.match_type == 'knockout',
            Match.parent_match_id.is_(None)
        ).order_by(Match.round, Match.match_number).all()

        if not matches:
            raise ValueError(
                f"No saved knockout draw exists for category '{category.name}' (ID {category.id}). "
                "Draw must be generated through the application workflow first."
            )

        # Organize matches by round
        rounds_dict: Dict[int, List[Match]] = {}
        for m in matches:
            rounds_dict.setdefault(m.round, []).append(m)

        for r in rounds_dict:
            rounds_dict[r].sort(key=lambda x: x.match_number)

        total_rounds = max(rounds_dict.keys())
        r1_matches = rounds_dict.get(1, [])
        num_r1_matches = len(r1_matches)
        bracket_size = num_r1_matches * 2

        # Tournament metadata
        venue = None
        if tournament.academy and tournament.academy.name:
            venue = tournament.academy.name
        elif tournament.game_info:
            venue = tournament.game_info

        dates_str = None
        s_date = category.start_date or tournament.start_date
        e_date = category.end_date or tournament.end_date
        if s_date:
            dates_str = s_date.strftime("%d %b %Y")
            if e_date and e_date != s_date:
                dates_str += f" – {e_date.strftime('%d %b %Y')}"

        scoring_summary = None
        if category.num_sets:
            scoring_summary = f"{category.num_sets} Sets ({category.games_per_set or 6} Games)"

        # Champion determination (strictly from persisted final match)
        champion_name: Optional[str] = None
        champion_seed: Optional[int] = None
        final_match_obj = rounds_dict[total_rounds][0] if total_rounds in rounds_dict and rounds_dict[total_rounds] else None
        if final_match_obj and final_match_obj.status == 'completed' and final_match_obj.winner:
            champion_name = cls.format_participant_name(final_match_obj.winner)
            champion_seed = final_match_obj.winner.manual_seed or final_match_obj.winner.seed

        # Convert matches to formatted card structures
        formatted_rounds: Dict[int, List[Dict[str, Any]]] = {}
        for r_num, m_list in rounds_dict.items():
            formatted_rounds[r_num] = [
                cls.format_match_card(m, r_num, total_rounds)
                for m in m_list
            ]

        # Multi-page layout generation based on draw size
        pages: List[Dict[str, Any]] = []

        if num_r1_matches <= 16:
            # CASE 1: 8, 16, or 32 participants -> Single Comprehensive Bracket Page
            round_matches_list = [formatted_rounds[r] for r in range(1, total_rounds + 1)]
            champ_target = {
                'type': 'champion',
                'title': 'CHAMPION',
                'name': champion_name,
                'seed': champion_seed
            }
            grid_cells = cls.build_grid_cells(round_matches_list, champ_target)
            round_headers = [cls.get_round_name(r, total_rounds) for r in range(1, total_rounds + 1)]

            pages.append({
                'page_num': 1,
                'total_pages': 1,
                'section_badge': 'Official Championship Draw',
                'section_title': f"{bracket_size}-Player Draw",
                'section_subtitle': 'Complete Bracket Progression',
                'round_headers': round_headers,
                'grid_cells': grid_cells,
                'is_final_page': True
            })

        elif num_r1_matches == 32:
            # CASE 2: 64 participants -> 5 Pages (4 Quarters + Finals Stage)
            total_pages = 5
            # Quarters 1 to 4
            for q in range(4):
                q_r1 = formatted_rounds[1][q * 8 : (q + 1) * 8]
                q_r2 = formatted_rounds[2][q * 4 : (q + 1) * 4]
                q_r3 = formatted_rounds[3][q * 2 : (q + 1) * 2]
                q_r4 = [formatted_rounds[4][q]]

                advances_to_sf = f"Semifinal {q // 2 + 1} (Page 5)"
                target = {
                    'type': 'qualifier',
                    'title': 'ADVANCES TO',
                    'name': advances_to_sf,
                    'seed': None
                }
                q_list = [q_r1, q_r2, q_r3, q_r4]
                grid_cells = cls.build_grid_cells(q_list, target)
                round_headers = [
                    cls.get_round_name(1, total_rounds),
                    cls.get_round_name(2, total_rounds),
                    cls.get_round_name(3, total_rounds),
                    "Quarter-Final"
                ]

                pages.append({
                    'page_num': q + 1,
                    'total_pages': total_pages,
                    'section_badge': f"Quarter {q + 1} of 4",
                    'section_title': f"Seeds {q * 16 + 1}–{(q + 1) * 16}",
                    'section_subtitle': f"Winner advances to {advances_to_sf}",
                    'round_headers': round_headers,
                    'grid_cells': grid_cells,
                    'is_final_page': False
                })

            # Page 5: Championship Stage (Quarterfinals to Final)
            qf_matches = formatted_rounds[4]
            sf_matches = formatted_rounds[5]
            f_matches = formatted_rounds[6]

            champ_target = {
                'type': 'champion',
                'title': 'CHAMPION',
                'name': champion_name,
                'seed': champion_seed
            }
            champ_list = [qf_matches, sf_matches, f_matches]
            champ_grid = cls.build_grid_cells(champ_list, champ_target)
            round_headers = ["Quarter-Finals", "Semi-Finals", "Final"]

            pages.append({
                'page_num': 5,
                'total_pages': total_pages,
                'section_badge': "Championship Finals Stage",
                'section_title': "Quarterfinals • Semifinals • Championship Final",
                'section_subtitle': "Official Tournament Climax & Podium",
                'round_headers': round_headers,
                'grid_cells': champ_grid,
                'is_final_page': True
            })

        elif num_r1_matches == 64:
            # CASE 3: 128 participants -> 9 Pages (8 Sections + Finals Stage)
            total_pages = 9
            for s in range(8):
                s_r1 = formatted_rounds[1][s * 8 : (s + 1) * 8]
                s_r2 = formatted_rounds[2][s * 4 : (s + 1) * 4]
                s_r3 = formatted_rounds[3][s * 2 : (s + 1) * 2]
                s_r4 = [formatted_rounds[4][s]]

                advances_to_qf = f"Quarterfinal {s // 2 + 1} (Page 9)"
                target = {
                    'type': 'qualifier',
                    'title': 'ADVANCES TO',
                    'name': advances_to_qf,
                    'seed': None
                }
                s_list = [s_r1, s_r2, s_r3, s_r4]
                grid_cells = cls.build_grid_cells(s_list, target)
                round_headers = [
                    cls.get_round_name(1, total_rounds),
                    cls.get_round_name(2, total_rounds),
                    cls.get_round_name(3, total_rounds),
                    cls.get_round_name(4, total_rounds)
                ]

                pages.append({
                    'page_num': s + 1,
                    'total_pages': total_pages,
                    'section_badge': f"Section {s + 1} of 8",
                    'section_title': f"Seeds {s * 16 + 1}–{(s + 1) * 16}",
                    'section_subtitle': f"Winner advances to {advances_to_qf}",
                    'round_headers': round_headers,
                    'grid_cells': grid_cells,
                    'is_final_page': False
                })

            # Page 9: Championship Stage
            qf_matches = formatted_rounds[5]
            sf_matches = formatted_rounds[6]
            f_matches = formatted_rounds[7]

            champ_target = {
                'type': 'champion',
                'title': 'CHAMPION',
                'name': champion_name,
                'seed': champion_seed
            }
            champ_list = [qf_matches, sf_matches, f_matches]
            champ_grid = cls.build_grid_cells(champ_list, champ_target)
            round_headers = ["Quarter-Finals", "Semi-Finals", "Final"]

            pages.append({
                'page_num': 9,
                'total_pages': total_pages,
                'section_badge': "Championship Finals Stage",
                'section_title': "Quarterfinals • Semifinals • Championship Final",
                'section_subtitle': "Official Tournament Climax & Podium",
                'round_headers': round_headers,
                'grid_cells': champ_grid,
                'is_final_page': True
            })

        else:
            # Fallback for arbitrary size: render all rounds on single scalable page
            round_matches_list = [formatted_rounds[r] for r in range(1, total_rounds + 1)]
            champ_target = {
                'type': 'champion',
                'title': 'CHAMPION',
                'name': champion_name,
                'seed': champion_seed
            }
            grid_cells = cls.build_grid_cells(round_matches_list, champ_target)
            round_headers = [cls.get_round_name(r, total_rounds) for r in range(1, total_rounds + 1)]

            pages.append({
                'page_num': 1,
                'total_pages': 1,
                'section_badge': 'Official Championship Draw',
                'section_title': f"{bracket_size}-Player Draw",
                'section_subtitle': 'Complete Bracket Progression',
                'round_headers': round_headers,
                'grid_cells': grid_cells,
                'is_final_page': True
            })

        return {
            'tournament_name': tournament.name,
            'category_name': category.name,
            'format_name': "Single Elimination" if category.format in ('single_elimination', 'doubles_elimination') else category.format.replace('_', ' ').title(),
            'gender': category.gender,
            'age_category': category.age_category,
            'total_participants': len(category.participants) if category.participants else bracket_size,
            'bracket_size': bracket_size,
            'dates': dates_str,
            'venue': venue,
            'status': category.status,
            'scoring_summary': scoring_summary,
            'champion_name': champion_name,
            'champion_seed': champion_seed,
            'pages': pages
        }
