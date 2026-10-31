# TourneyPro — Product Requirements Document (PRD)

**Document Status:** Approved & Baseline Source of Truth  
**Product Version:** 1.1 (Phase 1 Complete, Phase 2 In-Progress)  
**Target Domain:** Sports (Lawn Tennis, Pickleball, Badminton, Padel, Table Tennis) & Esports Competitions  
**Owner:** Product & Engineering Team  
**Last Updated:** October 2026  

---

## 1. Executive Summary & Vision

**TourneyPro** is an enterprise-grade, end-to-end tournament operations and competition management web platform. Designed from the ground up to solve the operational chaos of paper draw sheets, manual WhatsApp coordination, and fragmented tournament tools, TourneyPro provides a unified operating system for tournament organizers, academy directors, players, and spectators.

The platform orchestrates the complete tournament lifecycle:
1. Multi-category event creation with customizable rules and entry fees.
2. Participant registration, seed allotment, and unauthenticated guest onboarding.
3. Automated mathematical bracket generation (Single Elimination, Doubles Elimination, Round Robin Leagues, and Group Stage Team Leagues with 3-rubber ties).
4. Intelligent multi-court scheduling with rest interval enforcement and match progression locking.
5. Live digital scorekeeping, tiebreak management, and cumulative ranking calculation.
6. Public spectator portals, interactive bracket viewers, and high-fidelity vector PDF exports.

---

## 2. Target Personas & Use Cases

### 2.1 Tournament Organizer / Director (`admin`)
* **Goals:** Create multi-event tournaments quickly, seed participants, generate balanced draws, schedule hundreds of matches across finite courts without player clashes, and report live scores without math errors.
* **Pain Points:** Duplicate matches, players scheduled on two courts simultaneously, calculating complex head-to-head tiebreakers in leagues, dealing with walkovers and mid-match retirements.
* **Key Tasks:**
  * Configure tournament parameters, start/end dates, daily operating hours, and court rosters.
  * Manage player check-ins, manual seed assignments, and draft team rosters.
  * Record live games, rubber scores, and finalize category champions.

### 2.2 Academy Director / Club Manager (`academy_admin`)
* **Goals:** Host closed or open club tournaments, maintain internal student rankings, publish club announcements, and cultivate a community player base.
* **Pain Points:** Separate software needed for club announcements vs tournament fixtures.
* **Key Tasks:** Create an Academy portal (`/academy/<slug>`), manage club rosters, and restrict tournament registration to internal academy members.

### 2.3 Competitive Player / Participant (`player` / `user`)
* **Goals:** Register for upcoming events, submit entry fees, view bracket assignments, track scheduled match times ("Not Before" notices), inspect opponent statistics, and monitor lifetime rankings.
* **Pain Points:** Having to create full user accounts just to sign up for a weekend tournament; uncertainty over when their next match starts.
* **Key Tasks:** Self-register with or without an account ("Smart Guest Registration"), view live bracket progression, download official PDF draw sheets.

### 2.4 Spectator / Fan (Public Viewer)
* **Goals:** Follow live tournament scores in real-time on mobile or desktop without logging in.
* **Key Tasks:** Check live tournament standings, view Order of Play court schedules, and view match history.

### 2.5 Platform Super Administrator (`superadmin`)
* **Goals:** System-wide governance, global player registry auditing, user role elevation, and infrastructure monitoring.

---

## 3. Product Scope & Functional Hierarchy

The system enforces a strict operational domain hierarchy:

```
Platform (Superadmin & Global Player Registry)
  └── Academies / Clubs (Optional Umbrella Organization)
        └── Tournament (Multi-day, Multi-court Event Container)
              ├── Settings & Configuration (Registration fields, self-reg, check-in)
              ├── Categories / Events (e.g., Men's Singles, Under-14 Girls, Corporate Team League)
              │     ├── Groups (Pools for Group Stage / Round Robin)
              │     ├── Participants (Players, Doubles Pairs, or Teams)
              │     └── Matches (Fixtures, Sets, Games, Rubbers, Statuses)
              └── Order of Play (Daily Court Scheduling & Progression Pipeline)
```

---

## 4. Tournament Format Specifications

TourneyPro natively supports four primary competition formats:

### 4.1 Single Elimination (Knockout)
* **Mathematical Basis:** Generates brackets based on the smallest power of 2 greater than or equal to $N$ participants ($2^{\lceil \log_2 N \rceil}$).
* **Automatic Bye Distribution:**
  * When $N \neq 2^k$, exactly $B = 2^k - N$ byes are generated.
  * Byes are systematically awarded to the highest-seeded participants (Seed 1, Seed 2, Seed 3, etc.) and placed in alternating bracket quadrants to preserve bracket balance.
  * Top seeds receive automatic advances to Round 2 without playing a Round 1 match.
* **Seeding:** Manual seeds (assigned by organizer) take precedence over auto-generated seeds. Unseeded participants are randomized.
* **Ranking & Points:**
  * Final Rank 1: Champion (Winner of Final)
  * Final Rank 2: Runner-up (Loser of Final)
  * Final Rank 3–4: Semi-Finalists
  * Final Rank 5–8: Quarter-Finalists

### 4.2 Doubles Elimination (Knockout)
* **Pair Representation:** Formatted as `Player 1 / Player 2` with dual database references (`player_id` and `player2_id`).
* **Scoring & Progression:** Follows identical mathematical bracket progression to Single Elimination.
* **Points Distribution:** Lifetime ranking points earned from the tournament are credited independently to **both** individual player profiles.

### 4.3 Round Robin (League)
* **Schedule Generation:** Exhaustive round-robin fixture matrix where every participant plays every other participant once ($N(N-1)/2$ matches).
* **Cumulative Points Ranking:** Players are ranked based on total cumulative points/games won across all matches, incentivizing competitive effort in every game.
* **Knockout Transition:** Organizers can trigger "Start Knockout Stage" to advance the top $K$ ranked players (e.g., Top 4 into Semi-Finals). Points accumulated in the league phase carry forward.

### 4.4 Group Stage Team League with 3-Rubber Fixtures
Specially engineered for club, corporate, and inter-team tennis/badminton leagues:
* **Team Structure:** Teams consist of 5 tiered players (Tiers A, B, C, D, E) or a designated captain and team members.
* **Drafting Modes:**
  * **Mode A (Manual Chit Draw):** Organizers conduct a physical draw; UI validates and blocks duplicate player selections across teams.
  * **Mode B (Auto-Balanced Tier Draft):** System automatically distributes 1 player from each of the 5 skill tiers (A through E) into each team.
* **Fixture Composition (3 Rubbers per Team Tie):**
  * Rubber 1: Singles (e.g., Tier A vs Tier A)
  * Rubber 2: Doubles (e.g., Tier B + Tier C vs Tier B + Tier C)
  * Rubber 3: Singles / Decider (e.g., Tier D vs Tier D)
* **Rubber Scoring (Summation Rule $T=7$):**
  * Each rubber is played up to 7 total games ($G_1 + G_2 = 7$).
  * If a rubber reaches 3–3, an automatic tiebreaker is played to decide the 7th game (winning score is 4–3).
  * Mid-match retirements / walkovers: The non-retiring team is automatically awarded all remaining games required to reach 7.
* **Team Fixture Win Rule (First to 11 / 21 Total Games):**
  * A team tie consists of exactly 21 games across the 3 rubbers ($3 \times 7 = 21$).
  * The first team to accumulate 11 games secures the tie victory.
* **Tiebreakers for Group Standings:**
  1. Total Team Match Wins
  2. Head-to-Head result between tied teams
  3. Total Games Differential (Games Won minus Games Lost)
  4. Total Games Won

---

## 5. Match Scoring Modes

Categories support two granular scoring models:

| Scoring Mode | Description | UI Input | Winner Determination |
| :--- | :--- | :--- | :--- |
| **Total Games / Points** | Cumulative numeric integer scoring. | Numeric score inputs ($S_1, S_2$). | Highest score or first to target points. |
| **Standard Tennis Sets** | Granular set-by-set tennis match scoring (Best of 1, 3, or 5 sets). | Set 1, Set 2, Set 3, Set 4, Set 5 with tiebreak superscripts (e.g. `7-6(5)`). | Majority of sets won (e.g., 2 out of 3 sets). |

---

## 6. Court Scheduling & Order of Play Engine

The integrated multi-court scheduling engine solves complex resource allocation problems:

1. **Operating Calendar & Daily Windows:** Tournaments define start/end dates, daily opening/closing hours (`08:00` to `20:00`), and court rosters (`Court 1`, `Court 2`, etc.).
2. **Match Progression Locks:** Downstream matches (e.g., Quarter-Finals) cannot be scheduled or played until both upstream feeder matches (Round 1) are marked `completed`.
3. **Player Conflict Prevention:** A player registered in multiple categories (e.g., Men's Singles and Men's Doubles) cannot be scheduled for simultaneous matches.
4. **Mandatory Rest Buffers:** An organizer-configurable rest buffer (`min_rest_minutes`, default: 30 minutes) is automatically enforced between consecutive matches for any single player.
5. **Daily Match Caps:** A safety match limit (`max_matches_per_player_day`, default: 3 matches) prevents player overexertion.
6. **"Not Before" Scheduling:** Matches can be flagged as "Not Before [Time]" (Followed-By logic), maintaining schedule flexibility if earlier matches run long.

---

## 7. Registration & Player Ecosystem

### 7.1 Smart Guest Registration Flow
* Allows players to register without undergoing a traditional account creation workflow.
* The system automatically creates a global `Player` profile and links the entry to an internal `anonymous_registrations` account.
* If the user subsequently registers an official `User` account with the same email or mobile number, their lifetime player profile and tournament history are seamlessly reconciled.

### 7.2 Lifetime Player Registry & Statistics
* Global tracking across all tournaments:
  * Total Matches Played, Won, and Lost
  * Win Percentage (%)
  * Cumulative Ranking Points
  * Career Tournament Records (Champion, Runner-up, Semi-finalist)

### 7.3 Multi-Channel Payment Tracking
* Supports manual UPI payments (displaying organizer's UPI ID, collecting user transaction IDs, and manual admin verification workflow).
* Supports cash-on-arrival and free entry statuses.
* Prepared for automated payment gateway webhooks (Stripe / Razorpay).

---

## 8. Document Generation & Export Engine

TourneyPro delivers publication-ready vector documents:
1. **Dynamic Draw PDF:** Vector-rendered knockout brackets with seed indicators, participant names, match scores, and progression connectors.
2. **Order of Play PDF:** Comprehensive daily schedule organized by court columns, match start times, category headers, and estimated match durations.
3. **Participants Roster PDF & Excel:** Check-in sheets, contact rosters, seed tables, and payment statuses.

---

## 9. Non-Functional Requirements (NFRs)

### 9.1 Performance & Responsiveness
* SSR pages must achieve Largest Contentful Paint (LCP) under 1.2 seconds.
* Live score polling endpoint (`/api/v1/live/<slug>/scores`) must respond in < 60ms under standard loads.
* PDF generation for 64-player brackets must complete in under 2.5 seconds.

### 9.2 Security & Data Integrity
* **CSRF Defense:** `CSRFProtect` enforced on all web mutations.
* **API Security:** Stateless JWT bearer tokens (`HS256` or `RS256`) with expiration.
* **BOLA / IDOR Protection:** Organizers are strictly locked to tournaments where `tournament.user_id == current_user.id` (with superadmin bypass).
* **Database Relational Integrity:** Full foreign key cascade handling to avoid orphaned matches or participants.

### 9.3 Availability & Hosting
* Dual database support: Zero-dependency local SQLite for rapid testing; Supabase PostgreSQL with transaction pooling (PgBouncer) for production.
* Serverless WSGI compatibility targeting Vercel (`@vercel/python`) and containerized Gunicorn servers.
