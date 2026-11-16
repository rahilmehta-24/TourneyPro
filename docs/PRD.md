# The Baseline Society — Product Requirements Document (PRD)

**Document Status:** Approved & Baseline Source of Truth  
**Product Version:** 2.0 (Phase 1 & Phase 2 Core RBAC Complete)  
**Target Domain:** Sports (Lawn Tennis, Pickleball, Badminton, Padel, Table Tennis) & Esports Competitions  
**Owner:** Product & Engineering Team  
**Last Updated:** November 2026  

---

## 1. Executive Summary & Vision

**The Baseline Society** is an enterprise-grade, end-to-end tournament operations and competition management web platform. Designed from the ground up to solve the operational chaos of paper draw sheets, manual WhatsApp coordination, and fragmented tournament tools, The Baseline Society provides a unified operating system for tournament organizers, academy directors, players, and spectators.

The platform orchestrates the complete tournament lifecycle:
1. Multi-category event creation with customizable rules and entry fees.
2. Participant registration, seed allotment, and unauthenticated guest onboarding.
3. Automated mathematical bracket generation (Single Elimination, Doubles Elimination, Round Robin Leagues, and Group Stage Team Leagues with 3-rubber ties).
4. Intelligent multi-court scheduling with rest interval enforcement and match progression locking.
5. Live digital scorekeeping, tiebreak management, and cumulative ranking calculation.
6. Public spectator portals, interactive bracket viewers, and high-fidelity vector PDF exports.
7. Enterprise role-based access control, delegated tournament staff, on-court PIN scorekeeping, and draft draw publication workflows.

---

## 2. Target Personas & Use Cases

### 2.1 Tournament Organizer / Director (`owner`)
* **Goals:** Create multi-event tournaments quickly, seed participants, generate balanced draws, schedule hundreds of matches across finite courts without player clashes, appoint tournament desk staff and umpires, publish finalized draws, and report live scores without math errors.
* **Pain Points:** Duplicate matches, players scheduled on two courts simultaneously, calculating complex head-to-head tiebreakers in leagues, dealing with walkovers and mid-match retirements, delegating desk duties without sharing master admin credentials.
* **Key Tasks:**
  * Configure tournament parameters, start/end dates, daily operating hours, and court rosters.
  * Manage player check-ins, manual seed assignments, and draft team rosters.
  * Delegate operational responsibilities to tournament staff via `/tournaments/<slug>/staff`.
  * Toggle category draw publication state (`Draft` vs `Published`).
  * Record live games, rubber scores, and finalize category champions.

### 2.2 Academy Director / Club Manager (`academy_admin`)
* **Goals:** Host closed or open club tournaments, maintain internal student rankings, publish club announcements, and cultivate a community player base.
* **Pain Points:** Separate software needed for club announcements vs tournament fixtures.
* **Key Tasks:** Create an Academy portal (`/academy/<slug>`), manage club rosters, and restrict tournament registration to internal academy members.

### 2.3 Tournament Desk / Operations Manager (`manager` staff; legacy name `desk`)
* **Goals:** Execute day-to-day court desk logistics without altering tournament financial or staff configuration.
* **Key Tasks:** Check in arriving participants, assign seeds, schedule matches to available courts, enter match scores, and verify scorecards.

### 2.4 Match Official / Chair Umpire (`official` / `scorer` staff; legacy name `umpire`)
* **Goals:** Officiate assigned matches, report live game and rubber scores from court-side smartphones/tablets, and mark matches completed.
* **Key Tasks:** Open assigned match scoring modals, record game progression, and submit final scorelines. Strictly guarded against scoring matches in which they compete.

### 2.5 Quick Court Scorekeeper (Court PIN mode)
* **Goals:** Enable dedicated on-court tablets to enter scores instantly using a 6-digit, expiring, court-bound PIN without requiring individual user accounts.
* **Key Tasks:** Unlock the court scoring interface with the PIN and a display name, report game scores, and advance live scores for that court only.

### 2.6 Team League Captain (`captain`)
* **Goals:** Manage club/corporate team rosters, submit 3-rubber tie lineups before match cutoffs, and monitor group standings.
* **Key Tasks:** Submit Singles 1, Doubles, and Singles 2 player nominations via the team lineup modal before match commencement.

### 2.7 Competitive Player / Participant (`player` / `user`)
* **Goals:** Register for upcoming events, submit entry fees, view bracket assignments, track scheduled match times ("Not Before" notices), inspect opponent statistics, and monitor lifetime rankings.
* **Pain Points:** Having to create full user accounts just to sign up for a weekend tournament; uncertainty over when their next match starts.
* **Key Tasks:** Self-register with or without an account ("Smart Guest Registration"), view live bracket progression, download official PDF draw sheets.

### 2.8 Spectator / Fan (Public Viewer)
* **Goals:** Follow live tournament scores in real-time on mobile or desktop without logging in.
* **Key Tasks:** Check live tournament standings, view Order of Play court schedules, and view match history.

### 2.9 Platform Super Administrator (`superadmin`)
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

The Baseline Society natively supports four primary competition formats:

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
  * Final Rank 3 (displayed "3–4"): both Semi-Finalists, tied
  * Final Rank 5 (displayed "5–8"): Quarter-Finalists, tied

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
  * Tier E is the reserve/substitute slot and plays only when replacing an unavailable team member.
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
* If the user subsequently registers an official `User` account with the same email or mobile number, their lifetime player profile and tournament history are reconciled **only after the email or mobile number has been verified** (verification link or OTP).

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

The Baseline Society delivers publication-ready vector documents:
1. **Dynamic Draw PDF:** Vector-rendered knockout brackets with seed indicators, participant names, match scores, and progression connectors.
2. **Order of Play PDF:** Comprehensive daily schedule organized by court columns, match start times, category headers, and estimated match durations.
3. **Participants Roster PDF & Excel:** Check-in sheets, contact rosters, seed tables, and payment statuses.

---

## 9. Non-Functional Requirements (NFRs)

### 9.1 Performance & Responsiveness
* SSR pages: Largest Contentful Paint under 1.2 seconds on desktop broadband and under 2.5 seconds on a mid-range phone over 4G.
* Live score polling endpoint (`/api/v1/live/<slug>/scores`): origin response under 60 ms at the 95th percentile, served through a short-lived CDN cache (`max-age=3`) with ETag, sized for 1,000 concurrent spectators polling every 5 seconds.
* PDF generation for 64-player brackets under 2.5 seconds, and `304` responses without rendering when nothing changed.

### 9.2 Security & Data Integrity
* **CSRF Defense:** `CSRFProtect` enforced on all web mutations.
* **API Security:** stateless JWT bearer tokens (`HS256` with a dedicated secret, or `RS256`), 60-minute default expiry, per-request user validation.
* **Authorization:** fail-closed `check_tournament_access()` honoring owner, delegated staff (`manager`, `official`, `scorer`), expiring court-bound PIN sessions, and audited superadmin override. Organizers are locked to tournaments they own or are appointed to.
* **Brute-force and abuse protection:** shared-storage rate limits on login, registration, PIN entry, and public endpoints.
* **Transport and headers:** HTTPS only, HSTS, CSP, `nosniff`, secure/HttpOnly/SameSite cookies, `ProxyFix` behind proxies.
* **Secrets:** no default credentials in production; startup validation; separate secrets per environment.
* **Integrity:** atomic optimistic locking, complete audit trail (including scores and PIN actions), and foreign key rules that avoid orphaned matches or participants.
* **Input/output safety:** escaped templates and PDFs, formula-safe spreadsheet exports, size- and type-restricted uploads stored outside the web root.

### 9.3 Availability & Hosting
* Dual database support: zero-dependency local SQLite for testing; Supabase PostgreSQL with transaction pooling (PgBouncer) for production.
* Serverless WSGI compatibility targeting Vercel (`@vercel/python`) and containerized Gunicorn servers. Real-time push requires a non-serverless or managed-realtime option (see [`ARCHITECTURE.md`](ARCHITECTURE.md) §7); polling is the baseline.

### 9.4 Responsive, Touch & Accessibility Requirements
* **Phones:** viewports from 320 px to 480 px (including 440 px-wide phones such as the largest current iPhones) with full native-style web app support.
* **Tablets and desktops:** 481 to 640 px, 641 to 1023 px (tablet portrait, explicitly designed), 1024 to 1599 px (desktop baseline), and 1600 px and above (venue display mode).
* **Orientation and zoom:** landscape phones (height 500 px or less) and 200 % browser zoom must work without horizontal page scroll.
* **Safe-Area Inset Handling:** notches, Dynamic Island, and gesture bars via `viewport-fit=cover` and dynamic viewport units (`dvh`) with a `vh` fallback.
* **Touch Target Standards:** all interactive controls keep at least 44 × 44 px hit areas.
* **Input Usability:** no iOS Safari auto-zoom (16 px minimum on mobile) and `inputmode="numeric"` on score inputs.
* **Accessibility:** WCAG 2.2 AA (contrast, focus visibility, keyboard operation, reduced-motion support).
* **Zero Desktop Alteration:** mobile styling stays behind responsive breakpoints (`@media (max-width: ...)`), preserving the desktop layout.

### 9.5 Privacy
* Public pages and APIs expose names, results, and statistics only; contact, address, date of birth, and blood group are staff-only.
* Minors' data (U10 to U18) is minimized and guardian consent is recorded; deletion and export requests are supported. Counsel should confirm obligations under India's Digital Personal Data Protection Act, 2023 before launch.

---

## 10. Operational Governance & Enterprise RBAC

### 10.1 Staff Delegation Lifecycle
* Organizers (`owner`) can appoint registered platform users to dedicated tournament staff roles (`manager`, `official`, `scorer`) via `/tournaments/<slug>/staff`. Legacy names `tournament_admin`, `desk`, and `umpire` map to `manager`, `manager`, and `scorer`.
* Appointed staff gain scoped access to that tournament only. They can never appoint staff, generate PINs, or publish draws.
* Platform Superadmins retain platform-wide authority, and their overrides are always audit-logged.

### 10.2 Court PIN Fast Scoring Mode
* Owners generate 6-digit PINs with a validity of 8, 24, or 48 hours, optionally bound to a court.
* Court-side tablets authenticate at `/tournaments/<slug>/court-pin` with the PIN and the scorer's display name.
* PIN sessions can score only (no exports, staff, or settings), only on the assigned court, are rate-limited and audit-logged, and are never accepted by the REST API.

### 10.3 Draw Publication State Machine (Draft vs. Published)
* Newly created categories and generated brackets start in **Draft** state (`draw_published = False`).
* During draft mode, tournament organizers and desk staff can view bracket geometry, adjust seedings, test progression, and verify schedules.
* Public viewers, unauthenticated spectators, and players navigating to the category see a friendly status banner: *"Draws for this event are being finalized by the tournament committee"*.
* Bracket PDF generation is locked until the organizer explicitly toggles the category to **Published** via `/categories/<id>/toggle-publish`.
* The REST API and the live-score feed apply the same rule: unpublished categories return `403` (or are omitted) and expose no participants or fixtures.

### 10.4 Match Integrity & Anti-Conflict of Interest
* Active competitors (players or doubles pairs) participating in a match are strictly blocked from scoring or officiating that specific fixture.
* In team leagues, competing team captains and every rostered or lineup player are prevented from reporting results for ties involving their own team.
* Matches must be officiated by neutral chair umpires, desk managers, or tournament directors.

### 10.5 Optimistic Concurrency Control
* Match entities maintain a monotonic `lock_version` integer.
* Score submission requests must include the client's current version, and it is validated atomically against the database record. If another desk official or umpire submitted a score change in the interim, the system rejects the transaction with `HTTP 409 Conflict`, prompting the user to refresh and verify the current score state before reapplying changes.

