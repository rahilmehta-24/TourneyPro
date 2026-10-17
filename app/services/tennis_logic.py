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


def validate_total_7_games_score(g1_val, g2_val, tb_pts_p1=None, tb_pts_p2=None, is_live_update=False):
    """
    Validates and formats a rubber score under the Total 7 Games format.
    
    Rules:
    - In completed rubbers, total games played MUST equal 7 (g1 + g2 == 7).
    - Valid non-tiebreak outcomes: 7-0, 6-1, 5-2 (and their reverses).
    - If 4-3 or 3-4, a 7-point match tiebreak (from 3-3) decided the 7th game.
      Tiebreak winner must score >= 7 points and lead by >= 2 points.
    
    Args:
        g1_val: Games scored by participant 1 (int or string)
        g2_val: Games scored by participant 2 (int or string)
        tb_pts_p1: Tiebreak points for participant 1 (required if 4-3/3-4)
        tb_pts_p2: Tiebreak points for participant 2 (required if 4-3/3-4)
        is_live_update: Boolean flag allowing in-progress scores
        
    Returns:
        tuple: (score1_str, score2_str, g1, g2, winner_participant_idx)
               where winner_participant_idx is 1 (P1 won), 2 (P2 won), or None (tie in live update).
    """
    if g1_val is None or str(g1_val).strip() == '' or g2_val is None or str(g2_val).strip() == '':
        if is_live_update:
            return "", "", 0, 0, None
        raise ValueError("Both game scores must be provided.")

    try:
        g1 = int(g1_val)
        g2 = int(g2_val)
    except ValueError:
        raise ValueError("Games must be integers.")

    if g1 < 0 or g2 < 0:
        raise ValueError("Games cannot be negative.")

    if is_live_update:
        if g1 + g2 > 7:
            raise ValueError("Total games cannot exceed 7.")
        winner_idx = 1 if g1 > g2 else (2 if g2 > g1 else None)
        return f"{g1}-{g2}", f"{g2}-{g1}", g1, g2, winner_idx

    # Completed rubber validation
    if g1 + g2 != 7:
        raise ValueError(
            f"Total games must equal 7 (current total: {g1 + g2}). "
            "Valid final scores are 7-0, 6-1, 5-2, or 4-3."
        )

    valid_pairs = {(7, 0), (0, 7), (6, 1), (1, 6), (5, 2), (2, 5), (4, 3), (3, 4)}
    if (g1, g2) not in valid_pairs:
        raise ValueError(
            f"Score {g1}-{g2} is invalid. "
            "Valid final scores are 7-0, 6-1, 5-2, or 4-3."
        )

    winner_idx = 1 if g1 > g2 else 2

    # If 4-3 or 3-4, validate tiebreak points
    if (g1, g2) in {(4, 3), (3, 4)}:
        if tb_pts_p1 is None or str(tb_pts_p1).strip() == '' or tb_pts_p2 is None or str(tb_pts_p2).strip() == '':
            raise ValueError(
                "A 4-3 score indicates a 3-3 tie decided by a tie-break. "
                "Tie-break points for both players are required."
            )
        try:
            tb1 = int(tb_pts_p1)
            tb2 = int(tb_pts_p2)
        except ValueError:
            raise ValueError("Tie-break points must be integers.")

        if tb1 < 0 or tb2 < 0:
            raise ValueError("Tie-break points cannot be negative.")

        tb_winner_pts = max(tb1, tb2)
        tb_loser_pts = min(tb1, tb2)

        if tb_winner_pts < 7:
            raise ValueError(f"Tie-break winner must score at least 7 points (entered: {tb1}-{tb2}).")

        if tb_winner_pts == 7:
            if tb_loser_pts > 5:
                raise ValueError(f"Invalid tie-break score {tb1}-{tb2}. Winner must lead by at least 2 points.")
        else:
            if tb_winner_pts - tb_loser_pts != 2:
                raise ValueError(f"Invalid tie-break score {tb1}-{tb2}. Beyond 7 points, winner must lead by exactly 2.")

        if winner_idx == 1 and tb1 <= tb2:
            raise ValueError(f"Player 1 won the match (4-3), but Player 2 has higher/equal tie-break points ({tb1}-{tb2}).")
        if winner_idx == 2 and tb2 <= tb1:
            raise ValueError(f"Player 2 won the match (3-4), but Player 1 has higher/equal tie-break points ({tb1}-{tb2}).")

        score1_str = f"{g1}-{g2}({tb2})" if winner_idx == 1 else f"{g1}-{g2}({tb1})"
        score2_str = f"{g2}-{g1}({tb1})" if winner_idx == 2 else f"{g2}-{g1}({tb2})"
    else:
        score1_str = f"{g1}-{g2}"
        score2_str = f"{g2}-{g1}"

    return score1_str, score2_str, g1, g2, winner_idx

