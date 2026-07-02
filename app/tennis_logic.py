def validate_and_format_score(winner_id, p1_id, p2_id, num_sets, games_per_set, form_data):
    """
    Validate set-by-set tennis scores against standard Lawn Tennis rules and return
    formatted score strings for both players.
    
    Args:
        winner_id: ID of the declared winner
        p1_id: ID of participant 1
        p2_id: ID of participant 2
        num_sets: Total sets in match format (3 or 5)
        games_per_set: Games needed to win a set (4, 6, or 8)
        form_data: Dictionary containing form fields:
            set1_p1, set1_p2, tb1_p1, tb1_p2,
            set2_p1, set2_p2, tb2_p1, tb2_p2, etc.
            
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
            # If we haven't reached target wins, this set was required
            if sets_won_p1 < target_wins and sets_won_p2 < target_wins:
                raise ValueError(f"Set {s} score is incomplete. The match is not yet decided.")
            # If the match was already decided, subsequent sets must not have scores
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

        # Tennis set scoring rules:
        if W == 1:
            if gw != 1 or gl != 0:
                raise ValueError(f"Set {s} score of {g1}-{g2} is invalid. With 1 game per set, score must be 1-0.")
        elif gw == W:
            # E.g. 6-4, 6-3, 6-2, 6-1, 6-0
            if gl > W - 2:
                raise ValueError(f"Set {s} score of {g1}-{g2} is invalid. Must win by 2 games.")
        elif gw == W + 1:
            if gl == W - 1:
                # E.g. 7-5
                pass
            elif gl == W:
                # E.g. 7-6 tie-break set
                is_tb_set = True
                tb1_val = form_data.get(f'tb{s}_p1')
                tb2_val = form_data.get(f'tb{s}_p2')

                if not tb1_val or not tb2_val:
                    raise ValueError(f"Set {s} reached a tie-break ({g1}-{g2}). Tie-break points are required.")

                try:
                    tb_pts_p1 = int(tb1_val)
                    tb_pts_p2 = int(tb2_val)
                except ValueError:
                    raise ValueError(f"Set {s} tie-break points must be integers.")

                if tb_pts_p1 < 0 or tb_pts_p2 < 0:
                    raise ValueError(f"Set {s} tie-break points cannot be negative.")

                tbw = max(tb_pts_p1, tb_pts_p2)
                tbl = min(tb_pts_p1, tb_pts_p2)

                # Check set winner matches tiebreak winner
                if (g1 > g2 and tb_pts_p1 < tb_pts_p2) or (g2 > g1 and tb_pts_p2 < tb_pts_p1):
                    raise ValueError(f"Set {s} winner must win the tie-break.")

                # Tiebreak scoring: first to 7 by 2
                if tbw == 7:
                    if tbl > 5:
                        raise ValueError(f"Set {s} tie-break score {tb_pts_p1}-{tb_pts_p2} is invalid. Winner must lead by 2.")
                elif tbw > 7:
                    if tbl != tbw - 2:
                        raise ValueError(f"Set {s} tie-break score {tb_pts_p1}-{tb_pts_p2} is invalid. Winner must lead by exactly 2.")
                else:
                    raise ValueError(f"Set {s} tie-break score {tb_pts_p1}-{tb_pts_p2} is invalid. Must reach at least 7 points.")
            else:
                raise ValueError(f"Set {s} score of {g1}-{g2} is invalid.")
        else:
            raise ValueError(f"Set {s} score of {g1}-{g2} is invalid. Winning player must reach {W} or {W+1} games.")

        # Register set win
        if g1 > g2:
            sets_won_p1 += 1
            if is_tb_set:
                set_results_p1.append(f"{g1}-{g2}({tb_pts_p2})")
                set_results_p2.append(f"{g2}-{g1}({tb_pts_p2})")
            else:
                set_results_p1.append(f"{g1}-{g2}")
                set_results_p2.append(f"{g2}-{g1}")
        else:
            sets_won_p2 += 1
            if is_tb_set:
                set_results_p1.append(f"{g1}-{g2}({tb_pts_p1})")
                set_results_p2.append(f"{g2}-{g1}({tb_pts_p1})")
            else:
                set_results_p1.append(f"{g1}-{g2}")
                set_results_p2.append(f"{g2}-{g1}")

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
