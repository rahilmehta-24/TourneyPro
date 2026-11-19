# TourneyPro Format Display & UI Guide

This document visualizes and describes how each of the **6 tournament formats** is presented in the TourneyPro web interface (`/tournaments/<slug>/categories/<category_id>`).

---

## Master Format Display Matrix

| Format Key | Primary View Layout | Secondary / Supporting Views | Interactive Features |
|---|---|---|---|
| **`single_elimination`** | **Binary Tree Bracket** (R16 $\rightarrow$ QF $\rightarrow$ SF $\rightarrow$ Final) | Printable Draw PDF, Schedule View | Hover path highlighting, Match Report modal, Seed badges |
| **`doubles_elimination`** | **Binary Tree Bracket** (Pairs) | Order of Play, PDF Draw Sheet | Dual-player badges, Partner profile links |
| **`double_elimination`** | **Dual Split Bracket** (Winners + Losers + Grand Finals) | Losers drop-in indicators, Reset Match | Winners/Losers bracket toggle, Grand Finals Reset |
| **`round_robin`** | **League Table + Cross Matrix Grid** | Fixture Cards list, Standings table | Inline score editing grid, Report modal |
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
│ #3 M. Granollers / H. Zeballos   │────┐                                          │  🏆 CHAMPIONS: Bopanna / Ebden
│    S. Bolelli / A. Vavassori     │    │  ┌──────────────────────────────────┐    │
└──────────────────────────────────┘    ├──│ #2 R. Ram / J. Salisbury     6 6 │────┘
┌──────────────────────────────────┐    │  │    S. Bolelli / A. Vavassori 3 4 │
│ #2 R. Ram / J. Salisbury     6 6 │────┘  └──────────────────────────────────┘
│    K. Krawietz / T. Puetz    4 3 │
└──────────────────────────────────┘
```

### 2.2 Key Display Details
- **Dual Name Anchor**: Renders both partner names separated by a slash (`/`). Clicking either name opens that athlete's verified profile.
- **Badge Indicators**: Seed tags reflect the combined team seed.

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

---

## 4. Round Robin (League) View

The Round Robin category display is divided into a **Live Standings Table**, a **Cross-Matrix Grid**, and the **Upcoming Fixtures List**.

### 4.1 Standings Leaderboard Table
```
┌──────┬────────────────────────┬─────────┬────────┬────────┬────────┬────────┬────────┐
│ Rank │ Competitor             │ Played  │ Won    │ Lost   │ Sets   │ Games  │ Points │
├──────┼────────────────────────┼─────────┼────────┼────────┼────────┼────────┼────────┤
│  🥇1 │ Somdev Devvarman       │    4    │   4    │   0    │  8–1   │  52–24 │   12   │
│  🥈2 │ Ramkumar Ramanathan    │    4    │   3    │   1    │  6–3   │  46–32 │    9   │
│  🥉3 │ Saketh Myneni          │    4    │   2    │   2    │  5–5   │  41–40 │    6   │
│   4  │ Jeevan Nedunchezhiyan  │    4    │   1    │   3    │  3–6   │  30–44 │    3   │
│   5  │ Yuki Bhambri           │    4    │   0    │   4    │  1–8   │  22–51 │    0   │
└──────┴────────────────────────┴─────────┴────────┴────────┴────────┴────────┴────────┘
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

- **Interactive Admin Matrix**: Tournament directors and superadmins can input scores directly into empty grid cells and click **"Save Entries"** to recalculate standings in real time.

---

## 5. Doubles Round Robin View

Combines pair names with the league standings format:

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

### 6.1 Multi-Group Card Layout
```
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
│ GROUP A                          [Court 1]   │  │ GROUP B                          [Court 2]   │
├──────────────────────────────────────────────┤  ├──────────────────────────────────────────────┤
│ Q  Pos  Player            MP  W  L  Diff Pts │  │ Q  Pos  Player            MP  W  L  Diff Pts │
│ 🟢  1   Iga Swiatek        3  3  0   +14  18 │  │ 🟢  1   Aryna Sabalenka    3  3  0   +16  18 │
│ 🟢  2   Ons Jabeur         3  2  1    +4  15 │  │ 🟢  2   Maria Sakkari      3  2  1    +3  14 │
│ ──  3   Barbora Krejcikova 3  1  2    -5  11 │  │ ──  3   Madison Keys       3  1  2    -6  10 │
│ ──  4   Paula Badosa       3  0  3   -13   6 │  │ ──  4   Emma Navarro       3  0  3   -13   7 │
└──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐  ┌──────────────────────────────────────────────┐
│ GROUP C                          [Court 3]   │  │ GROUP D                          [Court 4]   │
├──────────────────────────────────────────────┤  ├──────────────────────────────────────────────┤
│ Q  Pos  Player            MP  W  L  Diff Pts │  │ Q  Pos  Player            MP  W  L  Diff Pts │
│ 🟢  1   Coco Gauff         3  3  0   +12  18 │  │ 🟢  1   Elena Rybakina     3  3  0   +15  18 │
│ 🟢  2   Daria Kasatkina    3  2  1    +2  13 │  │ 🟢  2   Jessica Pegula     3  2  1    +5  15 │
│ ──  3   M. Vondrousova     3  1  2    -3  12 │  │ ──  3   Qinwen Zheng       3  1  2    -4  11 │
│ ──  4   Jelena Ostapenko   3  0  3   -11   7 │  │ ──  4   Danielle Collins   3  0  3   -16   6 │
└──────────────────────────────────────────────┘  └──────────────────────────────────────────────┘
```

- **🟢 Qualifier Indicators**: Highlights top $q$ finishers who advance directly into the Knockout Stage.

### 6.2 Team League Mode (3-Rubber Accordion Tie View)
When `max_players_per_team > 1`, match fixtures render as composite ties featuring **3 distinct rubbers** with the $T=7$ summation scoreline:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Fixture #2: Baseline Warriors vs Net Aces                           [Court 1] [12 - 9] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ▼ Rubber 1 (Singles):   Rohan Bopanna (Tier A)   def.  Sumit Nagal (Tier A)        4–3 │
│ ▼ Rubber 2 (Doubles):   Ebden / Myneni (B+C)     def.  Bhambri / Ramanathan (B+C)  4–3 │
│ ▼ Rubber 3 (Singles):   Manas Dhamne (Tier D)    def.  Aryan Shah (Tier D)         4–3 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Knockout Stage (Playoff Bracket)
Once group matches complete, the top qualifiers are seeded into the binary bracket below the groups:

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
- **Set Score Inputs**: Inputs for Set 1, Set 2, Set 3 with Tiebreak point recording.
- **Scoring Format Switch**: Supports Games mode (tennis sets) or Points mode (squash/table tennis).
- **Match Status Action**: Single-click toggles between **Pending**, **Live Scoring**, and **Complete Match**.
- **Audit Reason Field**: Mandatory reason & explanation inputs for score revisions and bracket resets.
