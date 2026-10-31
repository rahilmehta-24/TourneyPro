# TourneyPro Rulebook & Operating Manual

Welcome to the official rulebook and operating manual for TourneyPro. This guide provides an in-depth look at how the tournament system operates, the formats supported, and how scoring and rankings are processed behind the scenes.

## 1. System Overview
TourneyPro is a centralized, multi-tier tournament management system designed to host sports and gaming competitions. 

The architecture follows a strict hierarchy:
`Tournament -> Categories -> Matches & Participants`

- **Tournaments** act as the global container.
- **Categories** act as specific events inside the tournament (e.g. "Men's Singles", "Under 15"). Each category runs its own bracket format independently of the others.

## 2. Tournament Formats

### 2.1 Single Elimination (Knockout)
A standard knockout bracket where a player is eliminated after a single match loss.
- **Generation:** Bracket generation relies on mathematical powers of 2. If the number of participants is not a power of 2 (e.g. 8, 16, 32), the system automatically generates **Byes** for the top seeds, advancing them straight to the next round.
- **Seeding:** Supports manual numeric seeding. If unseeded, players are randomly distributed into the bracket.
- **Rankings:** The winner of the final gets Final Rank 1 (Champion). The loser gets Final Rank 2 (Runner-Up). The losers of the Semi-Finals both receive Final Rank 3 (Semi-Finalists).

### 2.1.1 Doubles Elimination (Knockout)
Operates exactly like Single Elimination, but participants are registered as pairs (e.g. `Player 1 / Player 2`). 
- When the tournament concludes, leaderboard points are awarded to **both** players individually.
- The leaderboard accurately reflects who their partner was during that specific tournament run.

### 2.2 Round Robin (League)
In this format, every participant plays exactly one match against every other participant in the category.
- **Scoring System:** This format relies on a "Total Cumulative Points" system. Rather than determining rankings purely by Win/Loss ratio, every raw point scored in a match is accumulated.
- **Rankings:** At any time during the Round Robin phase, the leaderboard ranks players based on `total points`.
- **Knockout Stage Transition:** Round Robin categories allow organizers to click "Start Knockout Stage" after the matches conclude. The system will pull the top-ranked players directly into a Knockout bracket (e.g. Top 4 advance to Semi-Finals). The knockout stage points continue to be added to the cumulative total.

### 2.3 Group Stage + Knockout (Coming Soon)
Participants are divided into multiple smaller pools/groups.
- They play a mini Round Robin inside their specific group.
- Top players from each group advance to a centralized Knockout bracket.
- *(Note: This feature is currently in active development and disabled for production)*

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

## 5. Administration & Lifecycle

The system utilizes a **Unified Step-by-Step Wizard** to prevent workflow fragmentation:

1. **Step 1: Setup Phase:** Admin defines the tournament name, rules, and fundamental parameters.
2. **Step 2: Category Generation:** Admin seamlessly creates as many distinct sub-events (e.g. Men's Singles) as required without leaving the workflow.
3. **Step 3: Registration & Deadlines:** Admin defines a `Registration Closes At` deadline. The system handles all Timezone translations securely, converting the Admin's local time natively into UTC.
4. **Step 4: Execution & Match Reporting:** Admin clicks "Start Tournament". The system intelligently cascades generation to all unstarted categories. Admins then use the interactive grid/bracket to report results on the fly.
5. **Completion:** When all matches in a category end, the "Finish Category" button is clicked. This locks the results and assigns Final Ranks.
6. **Reset:** If a mistake is made, Admins can completely wipe the tournament bracket back to the Setup Phase without losing registered participants. Note: Double-execution safeguards prevent overlapping generation.

## 6. Points Distribution (Leaderboard)

When a Knockout category concludes, the players earn points toward their global ranking based on the round they reached:

- **Champion (Rank 1):** 650 Points
- **Runner-Up (Rank 2):** 400 Points
- **Semi-Finals (Rank 3-4):** 250 Points
- **Quarter-Finals (Rank 5-8):** 160 Points
- **Round 4 (Top 16):** 100 Points
- **Round 3 (Top 32):** 60 Points
- **Round 2 (Top 64):** 30 Points
- **Round 1 (Participation):** 10 Points

These points accumulate indefinitely to determine the global Leaderboard rankings across all tournaments.

## 7. Mobile App Companion

TourneyPro features a dedicated React Native mobile application designed to act as a companion to the core web platform. 

### 7.1 Role Segregation on Mobile
- **Normal Users / Fans:** The mobile app provides a read-only "dashboard" experience. Users can browse upcoming tournaments, view live brackets (rendered as a scrollable list of matches), check live scores, and follow the global leaderboards.
- **Tournament Admins:** Admins log into the mobile app to receive enhanced "management" permissions. By tapping a match, Admins can securely edit the match status, adjust the scheduled time, and submit live scores on-the-go without needing to access the main web dashboard.

### 7.2 Web vs. Mobile Feature Split
To ensure maximum stability, certain complex actions are restricted exclusively to the **Web Dashboard** and are not available in the mobile app:
- Initial Tournament and Category creation.
- Bulk CSV Participant Imports/Exports.
- Generating and Reseting the geometric tournament brackets.
- Assigning specific numeric Seeds. 

The mobile app is optimized strictly for **live-event consumption** and **on-the-fly score reporting**.
