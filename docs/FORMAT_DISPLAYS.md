# TourneyPro Format Display & UI Guide

This document visualizes and describes how each of the **6 tournament formats** is presented in the TourneyPro web interface (`/tournaments/<slug>/categories/<category_id>`).

---

## Master Format Display Matrix

| Format Key | Primary View Layout | Secondary / Supporting Views | Interactive Features |
|---|---|---|---|
| **`single_elimination`** | **Binary Tree Bracket** (R16 $\rightarrow$ QF $\rightarrow$ SF $\rightarrow$ Final) | Printable Draw PDF, Schedule View | Hover path highlighting, Match Report modal, Seed badges |
| **`doubles_elimination`** | **Binary Tree Bracket** (Pairs) | Order of Play, PDF Draw Sheet | Dual-player badges, Partner profile links |
| **`double_elimination`** | **Dual Split Bracket** (Winners + Losers + Grand Finals) | Losers drop-in indicators (⇄ mirrored rounds), Reset Match, Rankings bands | Winners/Losers bracket toggle, Grand Finals Reset |
| **`round_robin`** | **League Table + Cross Matrix Grid** | Fixture Cards list, Standings table, Tiebreak notes | Inline score editing grid, Report modal |
| **`doubles_round_robin`** | **Pairs League Table + Cross Matrix** | Fixture Cards list, Standings table | Team pair stats, Dual-player sync |
| **`group_stage`** | **Group Cards (A–D) + Knockout Tree** | 3-Rubber Team ties, Standings tables | Expandable rubbers accordion, Qualification badges |

---

## 1. Single Elimination (Knockout) View

### 1.1 Visual Wireframe (8-Player / 16-Player Bracket)
```
  Round of 16 (R1)          Quarter-Finals (R2)        Semi-Finals (R3)           Final (R4)
┌──────────────────────┐
│ #1 C. Alcaraz    6 6 │──┐
│ #16 S. Korda     2 3 │  │  ┌──────────────────────┐
└──────────────────────┘  ├──│ #1 C. Alcaraz    6 7 │──┐
┌──────────────────────┐  │  │ #8 H. Rune       4 5 │  │
│ #8 H. Rune       6 6 │──┘  └──────────────────────┘  │  ┌──────────────────────┐
│ #9 T. Fritz      3 4 │                               ├──│ #1 C. Alcaraz    6 6 │──┐
└──────────────────────┘                               │  │ #4 D. Medvedev   3 4 │  │
┌──────────────────────┐                               │  └──────────────────────┘  │
│ #4 D. Medvedev   7 6 │──┐                            │                            │  ┌──────────────────────┐
│ #13 T. Paul      6 3 │  │  ┌──────────────────────┐  │                            ├──│ #1 C. Alcaraz    6 7 │
└──────────────────────┘  ├──│ #4 D. Medvedev   6 6 │──┘                            │  │ #2 J. Sinner     4 6 │
┌──────────────────────┐  │  │ #5 A. Zverev     4 4 │                               │  └──────────────────────┘
│ #5 A. Zverev     6 6 │──┘  └──────────────────────┘                               │  🏆 CHAMPION: C. Alcaraz
│ #12 H. Hurkacz   3 2 │                                                            │
└──────────────────────┘                                                            │
  ... (Bottom Half: Djokovic, Tsitsipas, Dimitrov, Sinner) ─────────────────────────┘
```

### 1.2 Match Card Component Anatomy
```
┌──────────────────────────────────────────────────────────────┐
│ Match #3                     [Center Court]  [● In Progress] │ <── Status Badge
├──────────────────────────────────────────────────────────────┤
│ #1  Carlos Alcaraz                      [ 6 ] [ 4 ] [ 2 ]    │ <── Set Scores
│ #4  Daniil Medvedev                     [ 3 ] [ 6 ] [ 1 ]    │
└──────────────────────────────────────────────────────────────┘
  ▲         ▲                                     ▲
Seed   Player Name                            Set Breakdown
```

- **Interactive Hover Path**: Hovering the cursor over any match card dynamically traces and illuminates the athlete's route through past and future rounds (`highlightPlayerPath`).
- **Score Display**: Set scores are rendered in distinct boxes with the winner's set highlighted in forest green (`var(--primary)`).

### 1.3 Bye Display (non-power-of-2 fields)
When $N < B$, empty Round 1 slots render as **dimmed Bye cards**. The seed advances automatically, and the card shows no court or time. Byes are not counted in the fixture total ($N-1$).

```
┌──────────────────────┐
│ #1  C. Alcaraz       │──► advances (Bye)     [ muted card, no score ]
│     BYE              │
└──────────────────────┘
```

### 1.4 Podium Panel
| Position | Band shown | Stored `final_rank` |
|---|---|:---:|
| Champion | 1st | `1` |
| Runner-up | 2nd | `2` |
| Semi-finalists | 3–4 | `3` |
| Quarter-finalists | 5–8 | `5` |
| Round of 16 | 9–16 | `9` |

---

## 2. Doubles Elimination View

### 2.1 Visual Wireframe
```
       Quarter-Finals (R1)                      Semi-Finals (R2)                      Final (R3)
┌──────────────────────────────────┐
│ #1 R. Bopanna / M. Ebden     6 6 │────┐
│    H. Heliovaara / H. Patten 3 4 │    │  ┌──────────────────────────────────┐
└──────────────────────────────────┘    ├──│ #1 R. Bopanna / M. Ebden     7 6 │────┐
┌──────────────────────────────────┐    │  │ #4 W. Koolhof / N. Mektic    6 4 │    │
│ #4 W. Koolhof / N. Mektic    7 6 │────┘  └──────────────────────────────────┘    │  ┌──────────────────────────────────┐
│    M. Purcell / J. Thompson  5 4 │                                               ├──│ #1 R. Bopanna / M. Ebden     6 7 │
└──────────────────────────────────┘                                               │  │ #2 R. Ram / J. Salisbury     4 5 │
┌──────────────────────────────────┐                                               │  └──────────────────────────────────┘
│ #3 M.Granollers / H.Zeballos 6 4 │────┐                                          │  🏆 CHAMPIONS: Bopanna / Ebden
│    S. Bolelli / A. Vavassori 7 6 │    │  ┌──────────────────────────────────┐    │
└──────────────────────────────────┘    ├──│ #2 R. Ram / J. Salisbury     6 6 │────┘
┌──────────────────────────────────┐    │  │    S. Bolelli / A. Vavassori 3 4 │
│ #2 R. Ram / J. Salisbury     6 6 │────┘  └──────────────────────────────────┘
│    K. Krawietz / T. Puetz    4 3 │
└──────────────────────────────────┘
```

### 2.2 Key Display Details
- **Dual Name Anchor**: Renders both partner names separated by a slash (`/`). Clicking either name opens that athlete's verified profile.
- **Badge Indicators**: Seed tags reflect the combined team seed.
- **Podium**: Both partners are listed per place, with the same bands as Single Elimination (1, 2, 3, 5, 9).
- **Validation badge**: A player already registered in another pair in the same category is flagged at registration, not at draw time.

---

## 3. Double Elimination View

The Double Elimination view renders **three dedicated bracket tiers** on a single canvas:

```
========================================================================================
                                 🏆 WINNERS BRACKET
========================================================================================
     Winners Round 1                Winners Semi-Final               Winners Final
┌──────────────────────┐
│ #1 Aryan Shah    6 6 │──┐
│ #8 Vansh Nandal  2 3 │  │  ┌──────────────────────┐
└──────────────────────┘  ├──│ #1 Aryan Shah    6 6 │──┐
┌──────────────────────┐  │  │ #4 Rethin Pranav 4 3 │  │
│ #4 Rethin Pranav 7 6 │──┘  └──────────────────────┘  │  ┌──────────────────────┐
│ #5 Kriish Tyagi  5 4 │                               ├──│ #1 Aryan Shah    6 6 │──► To Grand Finals
└──────────────────────┘                               │  │ #2 Manas Dhamne  4 4 │    (Participant 1)
┌──────────────────────┐                               │  └──────────────────────┘
│ #3 Yuvan Nandal  6 6 │──┐                            │
│ #6 Rushil Khosla 3 4 │  │  ┌──────────────────────┐  │
└──────────────────────┘  ├──│ #2 Manas Dhamne  6 6 │──┘
┌──────────────────────┐  │  │ #3 Yuvan Nandal  3 4 │
│ #2 Manas Dhamne  6 6 │──┘  └──────────────────────┘
│ #7 Daksh Prasad  2 2 │
└──────────────────────┘

========================================================================================
                                 🛡️ LOSERS BRACKET
========================================================================================
     Losers Round 1           Losers Round 2           Losers Round 3        Losers Final
┌──────────────────────┐   ┌──────────────────────┐
│ #8 Vansh Nandal  6 6 │───│ #8 Vansh Nandal  4 3 │
│ #5 Kriish Tyagi  3 4 │   │ #3 Yuvan Nandal  6 6 │──┐
└──────────────────────┘   └──────────────────────┘  │  ┌──────────────────┐  ┌──────────────────┐
                                                     ├──│ #3 Yuvan Nandal  │──│ #2 Manas Dhamne  │──► To Grand Finals
┌──────────────────────┐   ┌──────────────────────┐  │  │ #4 Rethin Pranav │  │ #3 Yuvan Nandal  │    (Participant 2)
│ #6 Rushil Khosla 6 6 │───│ #6 Rushil Khosla 3 4 │──┘  └──────────────────┘  └──────────────────┘
│ #7 Daksh Prasad  2 3 │   │ #4 Rethin Pranav 6 6 │
└──────────────────────┘   └──────────────────────┘

========================================================================================
                             👑 GRAND FINALS CHAMPIONSHIP
========================================================================================
             Grand Finals (Match 1)                  Grand Finals Reset (Match 2)
     ┌────────────────────────────────────┐             ┌────────────────────────────────────┐
     │ P1: #1 Aryan Shah (Winners Champ)  │             │ P1: #1 Aryan Shah                  │
     │ P2: #2 Manas Dhamne (Losers Champ) │             │ P2: #2 Manas Dhamne                │
     │ Status: [Completed] (6-4, 6-3)     │             │ Status: [Completed - N/A]          │
     └────────────────────────────────────┘             └────────────────────────────────────┘
```

### 3.1 Drop-In Indicators
- Players dropping from Winners carry a **↓WRn** tag (e.g. `↓WR2`) and occupy the **top slot** (`participant1`) of the Losers match.
- Mirrored rounds (even Winners rounds, such as WR2) show a **⇄** icon in the round header. This is the anti-rematch ordering.
- Byes in the Losers Bracket render as dimmed Bye cards. Void matches (both feeders were byes) are hidden.

### 3.2 Rankings Panel (example above, $B = 8$)
| Place | Competitor | Round lost | `final_rank` |
|:---:|---|---|:---:|
| 1st | Aryan Shah | n/a (champion) | `1` |
| 2nd | Manas Dhamne | Grand Finals | `2` |
| 3rd | Yuvan Nandal | Losers Final (LR4) | `3` |
| 4th | Rethin Pranav | LR3 | `4` |
| 5th–6th | Vansh Nandal, Rushil Khosla | LR2 | `5` |
| 7th–8th | Kriish Tyagi, Daksh Prasad | LR1 | `7` |

---

## 4. Round Robin (League) View

The Round Robin category display is divided into a **Live Standings Table**, a **Cross-Matrix Grid**, and the **Upcoming Fixtures List**.

### 4.1 Standings Leaderboard Table
**Ranking order:** matches won first. `Pts` (3 per win) is for display only and is not a ranking criterion. The Tiebreak column states how a tie was broken.
```
┌────────┬──────────────────────────┬──────────┬───────┬────────┬──────────┬───────────┬────────┬──────────────┐
│  Rank  │ Competitor               │  Played  │  Won  │  Lost  │   Sets   │   Games   │  Pts   │   Tiebreak   │
├────────┼──────────────────────────┼──────────┼───────┼────────┼──────────┼───────────┼────────┼──────────────┤
│   🥇1   │ Somdev Devvarman         │    4     │   4   │   0    │   8–0    │   48–24   │   12   │      —       │
│   🥈2   │ Ramkumar Ramanathan      │    4     │   3   │   1    │   6–2    │   45–34   │   9    │      —       │
│   🥉3   │ Saketh Myneni            │    4     │   2   │   2    │   4–4    │   41–39   │   6    │      —       │
│   4    │ Jeevan Nedunchezhiyan    │    4     │   1   │   3    │   2–6    │   31–44   │   3    │      —       │
│   5    │ Yuki Bhambri             │    4     │   0   │   4    │   0–8    │   24–48   │   0    │      —       │
└────────┴──────────────────────────┴──────────┴───────┴────────┴──────────┴───────────┴────────┴──────────────┘
```

### 4.2 Cross-Matrix Results Grid
```
┌────────────────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Player                 │ S. Devvarman │ R. Ramanathan│  S. Myneni   │ J. Nedunche. │  Y. Bhambri  │
├────────────────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Somdev Devvarman       │      ██      │   6-4, 6-4   │   6-3, 6-4   │   6-2, 6-3   │   6-2, 6-2   │
│ Ramkumar Ramanathan    │   4-6, 4-6   │      ██      │   7-6, 6-4   │   6-3, 6-4   │   6-3, 6-2   │
│ Saketh Myneni          │   3-6, 4-6   │   6-7, 4-6   │      ██      │   6-4, 6-3   │   6-4, 6-3   │
│ Jeevan Nedunchezhiyan  │   2-6, 3-6   │   3-6, 4-6   │   4-6, 3-6   │      ██      │   6-4, 6-4   │
│ Yuki Bhambri           │   2-6, 2-6   │   3-6, 2-6   │   4-6, 3-6   │   4-6, 4-6   │      ██      │
└────────────────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

### 4.3 Tiebreak Display (3-way tie example)
Asha beat Ben, Ben beat Chen, Chen beat Asha. Head-to-head runs in a circle, so the **mini-league** (set difference) decides.

```
┌──────┬──────────┬─────┬────────┬─────────┬──────────────────────┐
│ Rank │ Player   │  W  │ Sets ± │ Games ± │ Tiebreak             │
├──────┼──────────┼─────┼────────┼─────────┼──────────────────────┤
│  1   │ Asha     │  1  │   +1   │   +6    │ Mini-league (sets)   │
│  2   │ Ben      │  1  │    0   │   −4    │ Mini-league (sets)   │
│  3   │ Chen     │  1  │   −1   │   −2    │ Mini-league (sets)   │
└──────┴──────────┴─────┴────────┴─────────┴──────────────────────┘
```
Tiebreak labels: `Head-to-head` (two-way), `Mini-league` (three or more), `Overall`, `Lots`.

- **Interactive Admin Matrix**: Tournament directors and superadmins can input scores directly into empty grid cells and click **"Save Entries"** to recalculate standings in real time.

---

## 5. Doubles Round Robin View

Combines pair names with the league standings format. Ranking and tiebreak labels follow Round Robin (wins first):

```
┌──────┬──────────────────────────────────┬────┬───┬───┬────────┬────────┬───────┐
│ Rank │ Pair                             │ MP │ W │ L │  Sets  │ Games  │ Points│
├──────┼──────────────────────────────────┼────┼───┼───┼────────┼────────┼───────┤
│  🥇1 │ Sania Mirza / Mahesh Bhupathi    │  3 │ 3 │ 0 │  6–1   │  40–22 │   9   │
│  🥈2 │ Karman Kaur Thandi / Leander Paes│  3 │ 2 │ 1 │  4–3   │  35–31 │   6   │
│  🥉3 │ Rutuja Bhosale / Purav Raja      │  3 │ 1 │ 2 │  3–4   │  28–34 │   3   │
│   4  │ Ankita Raina / Rohan Bopanna     │  3 │ 0 │ 3 │  1–6   │  24–40 │   0   │
└──────┴──────────────────────────────────┴────┴───┴───┴────────┴────────┴───────┘
```

---

## 6. Group Stage + Knockout View

### 6.1 Multi-Group Card Layout (Team League Mode)
In team league formats (`max_players_per_team > 1`), group cards and standings display the **Team Name** and **Captain Name** rather than individual player names:

```
┌────────────────────────────────────────────────────────┐  ┌────────────────────────────────────────────────────────┐
│ GROUP A                                      [Court 1] │  │ GROUP B                                      [Court 2] │
├────────────────────────────────────────────────────────┤  ├────────────────────────────────────────────────────────┤
│ Q  Pos  Team / Captain              MP  W  L   GD   GW │  │ Q  Pos  Team / Captain              MP  W  L   GD   GW │
│ 🟢   1   Baseline Warriors (R.Bopanna)3  3  0  +14   40│  │ 🟢   1   Net Aces (S. Nagal)         3  3  0  +16   42│
│ 🟢   2   Court Masters (L. Paes)     3  2  1   +4   34│  │ 🟢   2   Spin Wizards (M. Bhupathi)  3  2  1   +3   33│
│ ──   3   Volley Kings (S. Myneni)    3  1  2   -5   28│  │ ──   3   Deuce Dynamos (R.Ramanathan)3  1  2   -6   26│
│ ──   4   Drop Shot Club (P. Raja)    3  0  3  -13   23│  │ ──   4   Ace Hitters (Y. Bhambri)    3  0  3  -13   21│
└────────────────────────────────────────────────────────┘  └────────────────────────────────────────────────────────┘
```
*(In individual singles competitions, the column displays individual player names).*

**Columns:** `MP` matches played, `W`/`L` wins and losses, `GD` games differential, `GW` total games won. Ranking follows the group tiebreak order: wins, head-to-head, games differential, games won, fewest losses.

- **🟢 Qualifier Indicators**: Highlights top $q$ finishers who advance directly into the Knockout Stage.

### 6.2 Team League Mode (3-Rubber Accordion Tie View: 1 Singles + 2 Doubles)
When `max_players_per_team > 1`, match fixtures render as composite ties featuring **3 distinct rubbers (1 Singles and 2 Doubles)** with the $T=7$ summation scoreline:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Fixture #2: Baseline Warriors vs Net Aces                           [Court 1] [12 - 9] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ▼ Rubber 1 (Singles):   Rohan Bopanna (Tier A)        def.  Sumit Nagal (Tier A)        4–3 │
│ ▼ Rubber 2 (Doubles 1): M. Ebden / S. Myneni (B+C)    def.  Y. Bhambri / R. Ramanathan  4–3 │
│ ▼ Rubber 3 (Doubles 2): M. Dhamne / D. Prasad (D+E)   def.  A. Shah / R. Khosla (D+E)   4–3 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Running tie total**: The header shows games won against the target of **11**. Once a team reaches 11, any remaining rubbers are greyed out as dead rubbers.
- **Match tiebreak**: A `3–3` rubber shows `4–3 (TB 7-5)` for the deciding 7-point tiebreak.

### 6.3 Knockout Stage (Playoff Bracket)
Once group matches complete, the top qualifiers are seeded into the binary bracket below the groups. Group winners and runners-up from the same group sit in opposite halves. Any **Lucky Loser** is tagged **LL** with its ranking metrics on hover.

```
  Quarter-Finals (Knockout)                  Semi-Finals                       Final
┌──────────────────────────────┐
│ A1: Iga Swiatek          6 6 │──┐
│ B2: Maria Sakkari        3 2 │  │  ┌──────────────────────────────┐
└──────────────────────────────┘  ├──│ Iga Swiatek              6 6 │──┐
┌──────────────────────────────┐  │  │ Coco Gauff               4 3 │  │
│ C1: Coco Gauff           6 6 │──┘  └──────────────────────────────┘  │  ┌──────────────────────────────┐
│ D2: Jessica Pegula       4 3 │                                       ├──│ Iga Swiatek              6 6 │
└──────────────────────────────┘                                       │  │ Aryna Sabalenka          4 3 │
┌──────────────────────────────┐                                       │  └──────────────────────────────┘
│ B1: Aryna Sabalenka      6 6 │──┐                                    │  🏆 CHAMPION: Iga Swiatek
│ A2: Ons Jabeur           3 4 │  │  ┌──────────────────────────────┐  │
└──────────────────────────────┘  ├──│ Aryna Sabalenka          6 6 │──┘
┌──────────────────────────────┐  │  │ Elena Rybakina           4 4 │
│ D1: Elena Rybakina       6 6 │──┘  └──────────────────────────────┘
│ C2: Daria Kasatkina      2 3 │
└──────────────────────────────┘
```

---

## 7. Interactive Modals & Scorer View

### 7.1 Match Scoring Modal (`openMatchModal`)
Clicking any match card opens the unified Scoring Modal:
- **Set Score Inputs**: Set 1, Set 2, Set 3, with tiebreak point recording.
- **Match Tiebreak**: Optional `[10-7]` entry in place of a final set. It counts as one set and one game for the winner.
- **Scoring Format Switch**: Games mode (tennis sets), Points mode (squash/table tennis), or Team Tie mode ($T=7$ rubbers).
- **Match Status Action**: Single-click toggles between **Pending**, **Live Scoring**, and **Complete Match**.
- **Special Results**: **Walkover (W/O)** and **Retirement** options. The opponent is awarded the win, and in league formats those games and sets are excluded from tiebreak calculations.
- **Audit Reason Field**: Mandatory reason and explanation for score revisions and bracket resets.

---

## 8. Display Conventions

### 8.1 Status Legend
| Status | Style | Marker |
|---|---|:---:|
| Pending | Grey | ○ |
| Live | Blue | ● |
| Completed | Green, winner in bold | ✓ |
| Bye | Muted italic `BYE` | — |
| Walkover | Amber `W/O` | ⚑ |

Color is never the only signal. Every status has a marker.

### 8.2 Names and Scores
- Singles: `(3) A. Shah`. Doubles: `(3) A. Shah / B. Rao`.
- Tennis scores as `6-4 6-3`, match tiebreaks as `[10-7]`, numeric mode as a single number per side.

### 8.3 Verification Footer
Every category page ends with computed checks, shown as ✓/✗:

| Format | Checks |
|---|---|
| Single / Doubles Elim | Matches $= N-1$, byes held by top seeds, seeds 1 and 2 in opposite halves, seeds 1–4 in different quarters |
| Double Elim | Losers matches $= B-2$, fixtures $2N-2$ or $2N-1$, no drop-in rematch (for $B \ge 16$) |
| Round Robin / Doubles RR | Fixtures $= N(N-1)/2$, each player plays $N-1$, ranking starts with wins |
| Group Stage | Group sizes sum to $N$, $B$ is a power of 2, $L = B - Gq$, tie total $= 21$ games |

### 8.4 Responsive Behavior
- Brackets scroll horizontally inside their own container, so the page body never scrolls sideways.
- Standings tables and the cross-matrix collapse to cards under 600px.
- Light and dark themes use the same status markers.
