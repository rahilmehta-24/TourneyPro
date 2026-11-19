# The Baseline Society Rulebook & Operating Manual

Welcome to the official rulebook and operating manual for The Baseline Society. This guide provides an in-depth look at how the tournament system operates, the formats supported, and how scoring and rankings are processed behind the scenes.

## 1. System Overview
The Baseline Society is a centralized, multi-tier tournament management system designed to host sports and gaming competitions. 

The architecture follows a strict hierarchy:
`Tournament -> Categories -> Matches & Participants`

- **Tournaments** act as the global container.
- **Categories** act as specific events inside the tournament (e.g. "Men's Singles", "Under 15"). Each category runs its own bracket format independently of the others.

## 2. Tournament Formats

For in-depth mathematical specifications, bracket trees, seeding algorithms, and progression rules, refer to the dedicated format guides in the [`docs/formats/`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/README.md) directory, or inspect the visual UI layout in **[FORMAT_DISPLAYS.md](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/FORMAT_DISPLAYS.md)**:
- [Single Elimination Logic](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/SINGLE_ELIMINATION.md)
- [Doubles Elimination Logic](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/DOUBLES_ELIMINATION.md)
- [Double Elimination Logic](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/DOUBLE_ELIMINATION.md)
- [Round Robin Logic](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/ROUND_ROBIN.md)
- [Doubles Round Robin Logic](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/DOUBLES_ROUND_ROBIN.md)
- [Group Stage + Knockout Logic](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/docs/formats/GROUP_STAGE.md)

### 2.1 Single Elimination (Knockout)
A standard knockout bracket where a player is eliminated after a single match loss.
- **Generation:** Bracket generation relies on mathematical powers of 2. If the number of participants is not a power of 2 (e.g. 8, 16, 32), the system automatically generates **Byes** for the top seeds, advancing them straight to the next round.
- **Seeding:** Supports manual numeric seeding. If unseeded, players are randomly distributed into the bracket.
- **Rankings:** The winner of the final gets Final Rank 1 (Champion). The loser gets Final Rank 2 (Runner-Up). The losers of the Semi-Finals both receive Final Rank 3 (tied Semi-Finalists, displayed as the "3-4" band). Quarter-Final losers are the tied "5-8" band. The bands are display labels; the stored `final_rank` for both semi-finalists is 3.

### 2.1.1 Doubles Elimination (Knockout)
Operates exactly like Single Elimination, but participants are registered as pairs (e.g. `Player 1 / Player 2`). 
- When the tournament concludes, leaderboard points are awarded to **both** players individually.
- The leaderboard accurately reflects who their partner was during that specific tournament run.

### 2.2 Round Robin (League)
In this format, every participant plays exactly one match against every other participant in the category.
- **Scoring System:** This format relies on a "Total Cumulative Points" system. Rather than determining rankings purely by Win/Loss ratio, every raw point scored in a match is accumulated.
- **Rankings:** At any time during the Round Robin phase, the leaderboard ranks players based on `total points`.
- **Knockout Stage Transition:** Round Robin categories allow organizers to click "Start Knockout Stage" after the matches conclude. The system will pull the top-ranked players directly into a Knockout bracket (e.g. Top 4 advance to Semi-Finals). The knockout stage points continue to be added to the cumulative total.

### 2.3 Group Stage Team League (Multi-Rubber Ties)
Specially engineered for club, corporate, and inter-team racquet sports leagues:
- **Team Structure & Drafting:** Teams consist of 5 tiered players (Tiers A through E). Tiers A, B, C, and D fill the three rubbers; Tier E is the reserve/substitute slot. Supports **Mode A** (manual chit draw with duplicate prevention) and **Mode B** (auto-balanced tier draft distributing 1 player from each tier into each team).
- **3-Rubber Fixture Structure:** Each team tie consists of 3 distinct rubbers:
  - *Rubber 1:* Singles 1 (Tier A vs Tier A)
  - *Rubber 2:* Doubles (Tier B + Tier C vs Tier B + Tier C)
  - *Rubber 3:* Singles 2 / Decider (Tier D vs Tier D)
- **Summation Scoring Rule ($T=7$):** Every rubber is played to exactly 7 total games ($G_1 + G_2 = 7$). At 3–3, an automatic tiebreak decides the 7th game (winning score 4–3). Walkovers and mid-match retirements award all remaining unplayed games to the non-retiring team.
- **Tie Win Condition:** Exactly 21 games are contested across the 3 rubbers ($3 \times 7 = 21$). The first team to accumulate 11 games wins the tie.
- **Standings Tiebreakers:** 1) Total Team Match Wins, 2) Head-to-Head between tied teams, 3) Total Games Differential, 4) Total Games Won.

## 3. Match Scoring Modes

When creating a category, you can choose how scores are inputted:

### 3.1 Total Games Scoring
- A minimalist score input system where the Admin inputs the total points/games won by Player 1 and Player 2. 
- Useful for formats where only cumulative totals matter (like custom Round Robin scoring).

### 3.2 Standard Tennis Set Scoring
- A granular UI allowing input for Set 1, Set 2, Set 3, Set 4, and Set 5.
- Allows for precise Tiebreak point tracking for each set.
- A player must win the majority of the sets (e.g., 2 out of 3) to be declared the match winner.

## 4. Leaderboards & Global Rankings

### 4.1 Smart Guest Registration
Unauthenticated (guest) users are seamlessly accommodated through the Smart Registration flow. The system intelligently captures their data, maps their specific registration record to a secure internal `anonymous_registrations` dummy account, and generates a standalone Player profile entirely unlinked to standard authentication.

### 4.2 Global Player Registry
The system keeps a centralized `Player` database. Even if a player participates in 10 different tournaments (including guests), their overarching statistics (Total Wins, Total Losses, Win Rate) are tracked globally.

### 4.3 Tournament Podium
When a tournament finishes, the "Overall Leaderboard" will parse the finalized results for all categories and declare:
- **🥇 Champion:** Player with Final Rank 1
- **🥈 Runner-Up:** Player with Final Rank 2
- **🥉 Semi-Finalists:** The top 2 players with Final Rank 3 or 4.

## 5. Official Roles & Delegated Tournament Operations

The Baseline Society enforces a strict, fail-closed role hierarchy for operational security and sporting integrity:

1. **Tournament Organizer / Director (`owner`):** Controls the entire tournament lifecycle, court rosters, financial settings, staff appointments, Court PINs, and draw publication. Only the owner (or a superadmin) can do these.
2. **Tournament Manager (`manager`; legacy `tournament_admin`, `desk`):** Day-to-day check-in, seed assignments, court scheduling, and score verification. Cannot appoint staff or publish draws.
3. **Match Official (`official`):** Chief referee: walkovers, retirements, disputes, score corrections.
4. **Scorer (`scorer`; legacy `umpire`):** Reports game and set scores on assigned courts via mobile or tablet.
5. **Court PIN Scorekeeper:** Dedicated on-court tablets unlocked with a **6-digit, expiring PIN tied to one court**. Scoring only; no account is needed, and every action is audit-logged under the scorer's display name.
6. **Team League Captain (`captain`):** Submits 3-rubber lineups before the cutoff.
7. **Competitors & Spectators:** Public view-only access for published draws, standings, and order of play.

## 6. Bracket Publication Workflow (Draft vs. Published)

1. **Draft Phase (`draw_published = False`):**
   - When brackets are generated, they remain in **Draft** status.
   - Only Tournament Organizers and Desk Managers can view matches, verify seedings, and test progression.
   - Spectators and players see an informational banner indicating that draws are being finalized.
   - Vector PDF draw export is disabled until publication.
2. **Published Phase (`draw_published = True`):**
   - The Organizer reviews the draw and toggles the category to **Published**.
   - Brackets, seed positions, match times, and PDF draw sheets become immediately accessible to all users.

## 7. Match Integrity & Conflict of Interest Rules

To maintain absolute competitive fairness:
- **Active Competitor Lockout:** An athlete scheduled to play in a match cannot officiate or submit scores for that match. The system automatically inspects participant accounts and raises an immediate `HTTP 403 Forbidden` error if a conflict is detected.
- **Team Restriction:** Team captains and every rostered player (including lineup players of a rubber) cannot score or report results for ties involving their own team.
- **PIN Scorers:** A Court PIN scorer should not be a competitor in the matches on that court. PIN scoring is audit-logged so organizers can review it.
- **Optimistic Concurrency Lock:** Matches maintain a mandatory `lock_version` counter checked atomically. If two referees or officials attempt to modify the same match simultaneously, the second submission is rejected with `HTTP 409 Conflict`, preventing data corruption or accidental overwrites.

## 8. Administration & Lifecycle

The system utilizes a **Unified Step-by-Step Wizard** to prevent workflow fragmentation:

1. **Step 1: Setup Phase:** Admin defines the tournament name, rules, and fundamental parameters.
2. **Step 2: Category Generation:** Admin seamlessly creates as many distinct sub-events (e.g. Men's Singles) as required without leaving the workflow.
3. **Step 3: Registration & Deadlines:** Admin defines a `Registration Closes At` deadline. The system handles all Timezone translations securely, converting the Admin's local time natively into UTC.
4. **Step 4: Execution & Match Reporting:** Admin clicks "Start Tournament". The system intelligently cascades generation to all unstarted categories. Admins then use the interactive grid/bracket to report results on the fly.
5. **Completion:** When all matches in a category end, the "Finish Category" button is clicked. This locks the results and assigns Final Ranks.
6. **Reset:** If a mistake is made, Admins can completely wipe the tournament bracket back to the Setup Phase without losing registered participants. A reset requires typing the category name and a reason, and it is written to the audit log. Note: Double-execution safeguards prevent overlapping generation.

## 9. Points Distribution (Leaderboard)

When a Knockout category concludes, the players earn points toward their global ranking based on the round they reached:

- **Champion (Rank 1):** 650 Points
- **Runner-Up (Rank 2):** 400 Points
- **Semi-Finals (Rank 3-4):** 250 Points
- **Quarter-Finals (Rank 5-8):** 160 Points
- **Round 4 (Top 16):** 100 Points
- **Round 3 (Top 32):** 60 Points
- **Round 2 (Top 64):** 30 Points
- **Round 1 (Participation):** 10 Points

*Rank bands such as "Semi-Finals (Rank 3-4)" are display labels; both semi-final losers are stored with `final_rank = 3` and earn the same points.*

These points accumulate indefinitely to determine the global Leaderboard rankings across all tournaments.

## 10. Mobile Responsive Web & Touch Experience

The Baseline Society features a first-class mobile web architecture providing an app-like experience on iOS Safari and Android Chrome without requiring app store installation.

### 10.1 Role Segregation on Mobile
- **Normal Users / Fans:** Read-only dashboard with live scores, Order of Play schedules, and swipeable bracket rounds.
- **Tournament Staff & Umpires:** Off-canvas menu, quick scoring bottom sheet modals, and court PIN fast login mode.

### 10.2 Web vs. Desktop Workflow Integration
To ensure maximum stability, certain complex actions are restricted exclusively to the **Web Dashboard** and are not available in the mobile web experience:
- Initial Tournament and Category creation.
- Bulk CSV Participant Imports/Exports.
- Generating and Reseting the geometric tournament brackets.
- Assigning specific numeric Seeds. 

The mobile web experience is optimized strictly for **live-event consumption** and **on-the-fly score reporting**.

## 11. Data Privacy & Fair Play
- Only display names, avatars, statistics, and results are public. Contact details, date of birth, address, and blood group are visible to tournament staff only. Players under 18 appear by display name only.
- Guest registrants must verify their email or mobile number before a profile can be linked to an account; this prevents others from claiming a player's history.
- Entry fees paid by UPI require a unique 12-digit transaction reference per tournament; organizers approve each payment and approvals are logged.
- Players can request correction or deletion of their personal data from the organizer or platform administrator.
