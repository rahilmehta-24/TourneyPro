# TourneyPro — Functional Feature Matrix & Algorithmic Specifications (FEATURES.md)

**Document Status:** Approved  
**Source of Truth:** Inherits from [`PRD.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/PRD.md), [`DESIGN.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/DESIGN.md), and [`ARCHITECTURE.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/ARCHITECTURE.md)  
**Feature Set Version:** 2.0  
**Last Updated:** October 2026  

---

## 1. Feature Matrix Summary

| Feature Module | Implementation Status | Primary Service / Controller | Key Models Involved |
| :--- | :---: | :--- | :--- |
| **Single Elimination Knockout** | ✅ Production | `app/services/format_engine/single_elimination/` | `Tournament`, `Category`, `Match`, `Participant` |
| **Doubles Elimination** | ✅ Production | `app/services/format_engine/doubles_elimination/` | `Tournament`, `Category`, `Match`, `Participant`, `Player` |
| **Round Robin League** | ✅ Production | `app/services/format_engine/round_robin/` | `Category`, `Match`, `Participant` |
| **Group Stage Team League** | ✅ Production | `app/services/format_engine/group_stage/` | `Category`, `Group`, `Match`, `PlayerCategoryTier`, `TeamMember` |
| **Team Draft (Modes A & B)** | ✅ Production | `app/web/controllers/category.py` | `PlayerCategoryTier`, `TeamMember`, `Participant` |
| **3-Rubber Tie Scoring ($T=7$)** | ✅ Production | `app/services/format_engine/group_stage/` | `Match` (sub-fixtures & rubbers) |
| **Constraint Court Scheduler** | ✅ Production | `app/services/utils/scheduler.py` | `Tournament`, `Category`, `Match` |
| **Match Progression Locking** | ✅ Production | `app/services/utils/scheduler.py` | `Match` |
| **Smart Guest Registration** | ✅ Production | `app/web/controllers/tournament.py` | `Registration`, `Player`, `Participant` |
| **Global Player Registry** | ✅ Production | `app/web/controllers/player.py` | `Player`, `PlayerTournamentRecord` |
| **Academy Portals** | ✅ Production | `app/web/controllers/academy.py` | `Academy`, `AcademyMember`, `AcademyAnnouncement` |
| **Vector PDF Export Suite** | ✅ Production | `app/services/pdf/` | `DrawExportAdapter`, `DrawPdfService` |
| **Live Score Polling Feed** | ✅ Production | `app/api/live.py` | `Match`, `Tournament` |
| **Mobile Web App & Touch Engine** | ✅ Production | `app/web/static/css/style.css`, `base.html` | All Views / Presentation |
| **WebSocket Score Push** | ⚡ Phase 2 Active | `app/services/live_stream/` | `Match` |

---

## 2. In-Depth Algorithmic Specifications

### 2.1 Single Elimination & Bye Allocation Algorithm
* **Bracket Sizing:** For $N$ registered participants, the bracket capacity is determined by:
  $$C = 2^{\lceil \log_2 N \rceil}$$
* **Bye Computation:** When $N < C$, the number of Byes is:
  $$B = C - N$$
* **Seeding & Bye Placement Rules:**
  1. Participants with manual seeds (`manual_seed`) are ordered by rank ($1, 2, 3 \dots$).
  2. Seed 1 is pinned to top of upper half (Match 1, Slot 1).
  3. Seed 2 is pinned to bottom of lower half (Last Match, Slot 2).
  4. Seeds 3 and 4 are placed in alternating internal quadrants.
  5. Byes ($B$) are systematically granted to top seeds in priority order ($1 \to B$).
  6. Participants awarded a Bye advance automatically to Round 2 without a played match.
* **Winner Advancement:**
  When match at Round $R$, Match Number $M$ completes with winner $W$:
  $$\text{Next Round} = R + 1, \quad \text{Next Match Number} = \lceil M / 2 \rceil$$
  If $M$ is odd, $W$ is assigned to `participant1_id`. If $M$ is even, $W$ is assigned to `participant2_id`.

---

### 2.2 Doubles Elimination & Dual Player Linkage
* Operates on identical geometric power-of-2 bracket math as Single Elimination.
* **Dual Player Tracking:** Each participant entry maintains two foreign keys:
  * `player_id`: Primary athlete.
  * `player2_id`: Partner athlete.
* **Ranking Points Credit:** Upon tournament completion, final ranking points are calculated according to round achieved and credited independently to both athletes' global records.

---

### 2.3 Round Robin League Engine
* **Fixture Generation:** Implements cyclic polygon rotation algorithm to generate $N(N-1)/2$ pairings across $N-1$ rounds (for even $N$) or $N$ rounds (for odd $N$ with byes).
* **Cumulative Scoring:** Every point or game won in a match is summed into `Participant.group_points`.
* **Knockout Stage Transition:** Organizers can transition top $K$ finishers into a knockout stage. Top seeds in the knockout bracket are seeded directly by total accumulated points from pool play.

---

### 2.4 Group Stage Team League with 3-Rubber Fixtures

#### 2.4.1 Team Drafting Models
* **Mode A (Manual Chit Draw):**
  * Physical drawing replicated in digital UI.
  * Organizers select players from available roster.
  * Dynamic validation validates that no player is drafted into more than one team.
* **Mode B (Auto-Balanced Tier Draft):**
  * System ranks registered players into 5 skill tiers: Tier A (Elite), Tier B (Advanced), Tier C (Intermediate), Tier D (Developing), Tier E (Novice).
  * System distributes exactly 1 player from each of the 5 tiers into each team, ensuring equal skill distribution across all teams.

#### 2.4.2 3-Rubber Match Composition
Each team tie between Team Alpha and Team Beta consists of 3 distinct rubber fixtures:
* **Rubber 1:** Tier A Singles
* **Rubber 2:** Doubles (Tier B + Tier C)
* **Rubber 3:** Tier D Singles

#### 2.4.3 Rubber Scoring ($T=7$ Summation Rule)
* Every rubber is played up to exactly 7 total games:
  $$G_1 + G_2 = 7$$
* **Tiebreak at 3–3:** If a rubber reaches 3–3, a 7-point tiebreak is played to decide the 7th game. The winning scoreline is recorded as `4-3`.
* **Retirement & Walkover Remainder Rule:** If a player retires mid-match (e.g. at 2–1), all remaining unplayed games required to reach 7 are automatically awarded to the opposition. Example: Score `2-1` becomes `2-5` (total games = 7).

#### 2.4.4 Team Fixture Win Condition (First to 11 / 21 Total Games)
* Total possible games across 3 rubbers: $3 \times 7 = 21$ games.
* **First-to-11 Principle:** The first team to accumulate 11 games across the rubbers is officially declared the tie winner.

#### 2.4.5 Group Standings Tiebreakers
In pool play, teams are ranked by:
1. **Total Matches Won** (Team ties won).
2. **Head-to-Head Result** (Direct head-to-head winner between tied teams).
3. **Total Game Differential** ($\text{Games Won} - \text{Games Lost}$).
4. **Total Games Won**.

---

### 2.5 Court Scheduling & Order of Play Engine

The scheduling engine solves resource constraints across multiple tournament days:

1. **Prerequisite Match Locking:**
   Downstream matches evaluate `check_match_progression_allowed(match)`. If either feeder match is `pending` or `in_progress`, the downstream match cannot be scheduled or played.
2. **Player Rest Buffers (`min_rest_minutes`):**
   When an athlete finishes a match, the scheduler enforces a minimum rest window (default: 30 minutes) before that player can take the court for another event (e.g. Singles vs Doubles).
3. **Safety Daily Caps (`max_matches_per_player_day`):**
   Prevents any player from being scheduled for more than 3 matches in a single calendar day.
4. **"Not Before" Timing:**
   Matches can be marked as `is_not_before=True` with a designated start time, allowing matches to start after the assigned time if previous court matches overrun, but never before.

---

### 2.6 Smart Guest Registration Flow
* **Zero Barrier Entry:** Players register without prior account creation or password setup.
* **Automatic Profile Provisioning:**
  1. Input name, contact number, email, and DOB.
  2. System checks `Player` registry for matching mobile/email; reuses existing athlete profile if found or creates a new `Player` record.
  3. The registration is mapped internally to a system `anonymous_registrations` user account.
* **Account Claiming:** If the athlete later registers an account with matching credentials, all historical tournament records and statistics automatically link to their user profile.

---

### 2.7 High-Fidelity Vector PDF Exports
* **Draw Sheets:** Vector bracket rendered via `DrawPdfService`, including tournament title, category name, seeds, participant names, match scores, and progression connectors.
* **Order of Play:** Multi-court matrix displaying daily match schedules, court assignments, and estimated match durations.
* **HTTP 304 Caching:** PDF responses compute an MD5 hash of the PDF byte stream, returning `304 Not Modified` on unchanged requests to conserve server bandwidth.

---

### 2.8 Mobile Web App Experience & Touch Navigation Engine
* **Touch-Enabled Bracket Navigation:** Native `touchstart`, `touchmove`, `touchend` event bindings with momentum pan scrolling and pill-tab round selectors (`Round of 16` → `Quarterfinals` → `Semifinals` → `Finals`) that preserve SVG connector math.
* **Ergonomic Bottom Sheet Modals:** Converts centered dialogs on `≤ 640px` screens to bottom sheets using dynamic viewport units (`dvh`) with sticky action buttons and numeric keypads (`inputmode="numeric"`).
* **Deep-Linked Mobile UPI Intent:** Auto-detects mobile environments to render 1-tap `upi://pay` links and 1-tap clipboard copy helpers.
* **Auto-Collapsing Fluid Grids:** Global CSS safeguards for `repeat(auto-fit, minmax(...))` rules that prevent horizontal page wobble and viewport blowouts on narrow screens.
* **Zero Desktop Regression:** All mobile behaviors are strictly encapsulated in responsive media queries (`@media (max-width: ...)`), keeping the desktop experience 100% pixel-perfect and untouched.
