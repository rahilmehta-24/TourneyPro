def validate_and_format_score(winner_id, p1_id, p2_id, num_sets, games_per_set, form_data, is_live_update=False):
    """
    Validate set-by-set tennis scores against standard Lawn Tennis rules and return
    formatted score strings for both players.
    
    Args:
        winner_id: ID of the declared winner (can be None for live updates)
        p1_id: ID of participant 1
        p2_id: ID of participant 2
        num_sets: Total sets in match format (3 or 5)
        games_per_set: Games needed to win a set (4, 6, or 8)
        form_data: Dictionary containing form fields
        is_live_update: Boolean flag to bypass strict completion validations
            
    Returns:
        tuple: (score1_str, score2_str) of formatted scorelines.
    """
    W = games_per_set
    target_wins = (num_sets // 2) + 1

    sets_won_p1 = 0
    sets_won_p2 = 0

    set_results_p1 = []
    set_results_p2 = []

    for s in range(1, num_sets + 1):
        g1_val = form_data.get(f'set{s}_p1')
        g2_val = form_data.get(f'set{s}_p2')

        # Check if set was played
        if g1_val is None or g2_val is None or g1_val == '' or g2_val == '':
            if not is_live_update:
                # If we haven't reached target wins, this set was required
                if sets_won_p1 < target_wins and sets_won_p2 < target_wins:
                    raise ValueError(f"Set {s} score is incomplete. The match is not yet decided.")
            # If the match was already decided, or it's a live update, subsequent sets must not have scores
            continue

        try:
            g1 = int(g1_val)
            g2 = int(g2_val)
        except ValueError:
            raise ValueError(f"Set {s} games must be integers.")

        if g1 < 0 or g2 < 0:
            raise ValueError(f"Set {s} games cannot be negative.")

        gw = max(g1, g2)
        gl = min(g1, g2)

        is_tb_set = False
        tb_pts_p1 = 0
        tb_pts_p2 = 0

        tb1_val = form_data.get(f'tb{s}_p1')
        tb2_val = form_data.get(f'tb{s}_p2')
        if tb1_val and tb2_val:
            is_tb_set = True
            try:
                tb_pts_p1 = int(tb1_val)
                tb_pts_p2 = int(tb2_val)
            except ValueError:
                raise ValueError(f"Set {s} tie-break points must be integers.")

        if not is_live_update:
            # Tennis set scoring rules:
            if W == 1:
                if gw != 1 or gl != 0:
                    raise ValueError(f"Set {s} score of {g1}-{g2} is invalid. With 1 game per set, score must be 1-0.")
            else:
                if W == 4:
                    tb_win_games = 4
                    tb_lose_games = 3
                else:
                    tb_win_games = W + 1
                    tb_lose_games = W

                if gw == W and (W != 4 or gl < tb_lose_games):
                    if gl > W - 2:
                        raise ValueError(f"Set {s} score of {g1}-{g2} is invalid. Must win by 2 games.")
                elif gw == W + 1 and gl == W - 1 and W != 4:
                    pass
                elif gw == tb_win_games and gl == tb_lose_games:
                    if not is_tb_set:
                        raise ValueError(f"Set {s} reached a tie-break ({g1}-{g2}). Tie-break points are required.")

                    if tb_pts_p1 < 0 or tb_pts_p2 < 0:
                        raise ValueError(f"Set {s} tie-break points cannot be negative.")

                    tbw = max(tb_pts_p1, tb_pts_p2)
                    tbl = min(tb_pts_p1, tb_pts_p2)

                    if (g1 > g2 and tb_pts_p1 < tb_pts_p2) or (g2 > g1 and tb_pts_p2 < tb_pts_p1):
                        raise ValueError(f"Set {s} winner must win the tie-break.")

                    tb_target = 10 if s == num_sets else 7
                    
                    if tbw == tb_target:
                        if tbl > tb_target - 2:
                            raise ValueError(f"Set {s} tie-break score {tb_pts_p1}-{tb_pts_p2} is invalid. Winner must lead by 2.")
                    elif tbw > tb_target:
                        if tbl != tbw - 2:
                            raise ValueError(f"Set {s} tie-break score {tb_pts_p1}-{tb_pts_p2} is invalid. Winner must lead by exactly 2.")
                    else:
                        raise ValueError(f"Set {s} tie-break score {tb_pts_p1}-{tb_pts_p2} is invalid. Must reach at least {tb_target} points.")
                else:
                    raise ValueError(f"Set {s} score of {g1}-{g2} is invalid.")
        # Register set win (for live updates, we just record whoever has more, or tie)
        if g1 > g2:
            sets_won_p1 += 1
            if is_tb_set:
                set_results_p1.append(f"{g1}-{g2}({tb_pts_p2})")
                set_results_p2.append(f"{g2}-{g1}({tb_pts_p2})")
            else:
                set_results_p1.append(f"{g1}-{g2}")
                set_results_p2.append(f"{g2}-{g1}")
        elif g2 > g1:
            sets_won_p2 += 1
            if is_tb_set:
                set_results_p1.append(f"{g1}-{g2}({tb_pts_p1})")
                set_results_p2.append(f"{g2}-{g1}({tb_pts_p1})")
            else:
                set_results_p1.append(f"{g1}-{g2}")
                set_results_p2.append(f"{g2}-{g1}")
        else:
            # Tied set (only possible in live updates)
            if is_tb_set:
                set_results_p1.append(f"{g1}-{g2}({tb_pts_p2})")
                set_results_p2.append(f"{g2}-{g1}({tb_pts_p1})")
            else:
                set_results_p1.append(f"{g1}-{g2}")
                set_results_p2.append(f"{g2}-{g1}")

    if not is_live_update:
        # Validate match outcome
        if sets_won_p1 == target_wins and sets_won_p2 == target_wins:
            raise ValueError("Invalid match outcome. Both players cannot reach the winning set target.")

        if sets_won_p1 != target_wins and sets_won_p2 != target_wins:
            raise ValueError(f"Match is incomplete. A player must win {target_wins} sets.")

        actual_winner_id = p1_id if sets_won_p1 == target_wins else p2_id
        if winner_id != actual_winner_id:
            raise ValueError("The selected winner does not match the actual set scores.")

    score1_str = ", ".join(set_results_p1)
    score2_str = ", ".join(set_results_p2)

    return score1_str, score2_str


def award_walkover_or_retirement_rubber(p1_games=0, p2_games=0, retiring_player=1, total_games=7):
    """
    Award remaining games to complete the T-game rubber (e.g. 7 games) to the opposition.
    Per tournament organizer rule:
    - If Player 1 retires at 2-3, remaining games (7 - 5 = 2) are awarded to Player 2 -> 2-5.
    - If Player 2 retires at 3-2, remaining games (7 - 5 = 2) are awarded to Player 1 -> 5-2.
    - If walkover before match starts (0-0): retiring player gets 0, opponent gets 7 -> 7-0 (or 0-7).

    Returns:
        tuple: (score1_str, score2_str, winner_indicator)
    """
    T = int(total_games or 7)
    try:
        g1 = int(p1_games or 0)
        g2 = int(p2_games or 0)
    except (TypeError, ValueError):
        g1, g2 = 0, 0

    if g1 < 0: g1 = 0
    if g2 < 0: g2 = 0

    played = g1 + g2
    remaining = max(0, T - played)

    if retiring_player == 1:
        # Opponent (Player 2) gets all remaining games
        g2 += remaining
        winner_indicator = 2
    else:
        # Opponent (Player 1) gets all remaining games
        g1 += remaining
        winner_indicator = 1

    score1_str = f"{g1}-{g2}"
    score2_str = f"{g2}-{g1}"
    return score1_str, score2_str, winner_indicator


def validate_team_rubber_score(p1_games, p2_games, p1_tb_pts=None, p2_tb_pts=None, total_games=7, is_live_update=False, is_walkover=False, is_retired=False, retiring_player=None):
    """
    Validates and formats scores for individual team rubbers under the configured total-games rule.
    Per tournament organizer rules:
    - Total Games Target (T): default 7 games per rubber.
    - In a completed match, the sum of games MUST equal T (g1 + g2 == T).
    - If a walkover or retirement occurs, the opposition is awarded all remaining games to reach T.
    """
    T = int(total_games or 7)
    if is_walkover or is_retired:
        r_player = int(retiring_player or 2)
        return award_walkover_or_retirement_rubber(p1_games, p2_games, retiring_player=r_player, total_games=T)

    if T % 2 == 0 or T < 1:
        raise ValueError(f"Total games target must be a positive odd integer (e.g. 5, 7, 9). Received {T}.")

    tb_trigger = (T - 1) // 2       # e.g. 3 for T=7
    tb_winner_games = (T + 1) // 2  # e.g. 4 for T=7

    try:
        g1 = int(p1_games)
        g2 = int(p2_games)
    except (TypeError, ValueError):
        raise ValueError("Rubber game scores must be valid integers.")

    if g1 < 0 or g2 < 0:
        raise ValueError("Games cannot be negative.")

    # Parse tiebreak points if provided
    is_tb_provided = False
    tb_pts_p1 = None
    tb_pts_p2 = None

    if p1_tb_pts not in (None, '') and p2_tb_pts not in (None, ''):
        is_tb_provided = True
        try:
            tb_pts_p1 = int(p1_tb_pts)
            tb_pts_p2 = int(p2_tb_pts)
        except ValueError:
            raise ValueError("Tiebreak points must be valid integers.")
        if tb_pts_p1 < 0 or tb_pts_p2 < 0:
            raise ValueError("Tiebreak points cannot be negative.")
        if tb_pts_p1 == tb_pts_p2:
            raise ValueError("Tiebreak cannot end in a draw. A player must win by at least 2 points.")

    # Handle case where user entered 3-3 with tiebreak points to decide the final 7th game:
    if g1 == tb_trigger and g2 == tb_trigger and is_tb_provided:
        tbw = max(tb_pts_p1, tb_pts_p2)
        tbl = min(tb_pts_p1, tb_pts_p2)
        tb_target = 7
        if tbw == tb_target:
            if tbl > tb_target - 2:
                raise ValueError(f"Invalid tiebreak score {tb_pts_p1}-{tb_pts_p2}. Winner must lead by at least 2 points.")
        elif tbw > tb_target:
            if tbl != tbw - 2:
                raise ValueError(f"Invalid tiebreak score {tb_pts_p1}-{tb_pts_p2}. Must lead by exactly 2 points when extending past {tb_target}.")
        else:
            raise ValueError(f"Tiebreak winner must reach at least {tb_target} points.")

        # Tiebreak winner is awarded the final game to make sum = T (4-3 or 3-4)
        if tb_pts_p1 > tb_pts_p2:
            g1 = tb_winner_games
            g2 = tb_trigger
        else:
            g1 = tb_trigger
            g2 = tb_winner_games

    # Validation rules
    if not is_live_update:
        # Sum of games MUST equal total_games T
        if g1 + g2 != T:
            if g1 == tb_trigger and g2 == tb_trigger and not is_tb_provided:
                raise ValueError(f"Score reached {tb_trigger}–{tb_trigger}. A 7-point tiebreak must be played to decide the final game ({tb_winner_games}–{tb_trigger}). Please enter the tiebreak points.")
            raise ValueError(f"Total games must sum to {T}. For example: 6–1, 5–2, 7–0, or 4–3. You entered {g1} and {g2} (sum: {g1 + g2}).")

        # When score is 4-3 or 3-4 and tiebreak points WERE provided, validate them:
        if is_tb_provided and ((g1 == tb_winner_games and g2 == tb_trigger) or (g2 == tb_winner_games and g1 == tb_trigger)):
            tbw = max(tb_pts_p1, tb_pts_p2)
            tbl = min(tb_pts_p1, tb_pts_p2)

            if (g1 > g2 and tb_pts_p1 <= tb_pts_p2) or (g2 > g1 and tb_pts_p2 <= tb_pts_p1):
                raise ValueError("The rubber winner must match the tiebreak winner.")

            tb_target = 7
            if tbw == tb_target:
                if tbl > tb_target - 2:
                    raise ValueError(f"Invalid tiebreak score {tb_pts_p1}-{tb_pts_p2}. Winner must lead by at least 2 points.")
            elif tbw > tb_target:
                if tbl != tbw - 2:
                    raise ValueError(f"Invalid tiebreak score {tb_pts_p1}-{tb_pts_p2}. Must lead by exactly 2 points when extending past {tb_target}.")
            else:
                raise ValueError(f"Tiebreak winner must reach at least {tb_target} points.")
    else:
        # In-progress matches cannot exceed total_games
        if g1 + g2 > T:
            raise ValueError(f"Total games in progress cannot exceed {T}. You entered {g1} and {g2} (sum: {g1 + g2}).")

    winner_indicator = None
    if g1 + g2 == T or not is_live_update:
        if g1 > g2:
            winner_indicator = 1
        elif g2 > g1:
            winner_indicator = 2
    elif is_live_update and (g1 > g2 or g2 > g1):
        winner_indicator = 1 if g1 > g2 else 2

    if is_tb_provided and ((g1 == tb_winner_games and g2 == tb_trigger) or (g2 == tb_winner_games and g1 == tb_trigger)):
        tb_loser = tb_pts_p2 if g1 > g2 else tb_pts_p1
        score1_str = f"{g1}-{g2}({tb_loser})"
        score2_str = f"{g2}-{g1}({tb_loser})"
    else:
        score1_str = f"{g1}-{g2}"
        score2_str = f"{g2}-{g1}"

    return score1_str, score2_str, winner_indicator


def calculate_team_fixture_status(rubbers, total_games=7):
    """
    Calculate the overall outcome of a 3-rubber team fixture.

    Args:
        rubbers: List of Match objects or dicts representing the rubbers
        total_games: T (default 7)

    Returns:
        dict: {
            'g1': total_games_team1,
            'g2': total_games_team2,
            'rubbers_won_p1': int,
            'rubbers_won_p2': int,
            'target_games_to_win': int,
            'is_decided': bool,
            'winner_indicator': 1, 2, or None,
            'summary_score1': str,
            'summary_score2': str
        }
    """
    T = int(total_games or 7)
    target_to_win = ((3 * T) // 2) + 1  # e.g., 11 for T=7 (21 total games)

    g1_total = 0
    g2_total = 0
    rubbers_won_p1 = 0
    rubbers_won_p2 = 0
    completed_rubbers = 0

    for r in rubbers:
        score1 = getattr(r, 'score1', None) if not isinstance(r, dict) else r.get('score1')
        score2 = getattr(r, 'score2', None) if not isinstance(r, dict) else r.get('score2')
        status = getattr(r, 'status', None) if not isinstance(r, dict) else r.get('status')
        winner_id = getattr(r, 'winner_id', None) if not isinstance(r, dict) else r.get('winner_id')
        p1_id = getattr(r, 'participant1_id', None) if not isinstance(r, dict) else r.get('participant1_id')

        if score1:
            try:
                main_part = score1.split('(')[0].strip()
                if '-' in main_part:
                    s1, s2 = main_part.split('-')
                    g1_total += int(s1)
                    g2_total += int(s2)
                elif score1.isdigit():
                    g1_total += int(score1)
                    if score2 and score2.isdigit():
                        g2_total += int(score2)
            except (ValueError, TypeError):
                pass

        if status == 'completed':
            completed_rubbers += 1
            if winner_id and p1_id:
                if winner_id == p1_id:
                    rubbers_won_p1 += 1
                else:
                    rubbers_won_p2 += 1

    is_decided = (g1_total >= target_to_win or g2_total >= target_to_win or completed_rubbers >= 3)
    winner_ind = None
    if g1_total >= target_to_win or (completed_rubbers >= 3 and g1_total > g2_total):
        winner_ind = 1
    elif g2_total >= target_to_win or (completed_rubbers >= 3 and g2_total > g1_total):
        winner_ind = 2

    return {
        'g1': g1_total,
        'g2': g2_total,
        'rubbers_won_p1': rubbers_won_p1,
        'rubbers_won_p2': rubbers_won_p2,
        'completed_rubbers': completed_rubbers,
        'target_games_to_win': target_to_win,
        'is_decided': is_decided,
        'winner_indicator': winner_ind,
        'summary_score1': str(g1_total),
        'summary_score2': str(g2_total)
    }

