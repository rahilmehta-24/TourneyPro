# TourneyPro — System & UX/UI Design Specification (DESIGN.md)

**Document Status:** Approved  
**Source of Truth:** Inherits all requirements and domain rules from [`PRD.md`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/PRD.md)  
**Design Version:** 2.0  
**Target Platform:** Web (Desktop, Tablet, Mobile Responsive)  
**Last Updated:** October 2026  

---

## 1. Design Philosophy & Principles

TourneyPro's interface is engineered to eliminate operational friction during high-stress tournament environments. The design adheres to four foundational pillars:

1. **Information Density with Zero Clutter:** Tournament organizers need high data density (courts, matches, scores, seeds) without cognitive overload. Layouts use clear visual grouping, card containers, and micro-spacing.
2. **Dynamic Live Feel:** The interface feels alive and responsive. Bracket paths connect dynamically via SVG vectors; score reporting immediately highlights winning participants; status badges reflect live court occupancy.
3. **Sleek Aesthetic with Dark-Mode First Engineering:** A modern sports-tech palette featuring deep charcoal backgrounds, neon tennis-ball accents (`#10b981`, `#047857`, emerald and neon accents), glassmorphism cards, and refined typography.
4. **Zero-Framework Lightweight Speed:** Built entirely with Vanilla CSS3 and minimal vanilla JavaScript. No heavy frontend framework runtimes (React/Vue/Angular), yielding instant page renders, sub-second transitions, and zero client-side bundling lag.

---

## 2. Design System Tokens & Foundations

The design system is defined centrally in [`app/web/static/css/style.css`](file:///Users/rahilmehta24/VS_Code/Projects/TourneyPro/app/web/static/css/style.css) using CSS Custom Properties (Variables):

### 2.1 Color Palette

```css
:root {
  /* Primary & Brand Accents */
  --color-primary: #10b981;          /* Vibrant Emerald / Tennis Green */
  --color-primary-hover: #059669;
  --color-primary-light: rgba(16, 185, 129, 0.12);
  --color-accent: #6366f1;           /* Indigo Accent */
  --color-accent-hover: #4f46e5;
  
  /* Neutral / Dark Theme Backgrounds */
  --bg-app: #0f172a;                 /* Slate 900 */
  --bg-surface: #1e293b;             /* Slate 800 */
  --bg-surface-elevated: #334155;    /* Slate 700 */
  --bg-surface-glass: rgba(30, 41, 59, 0.75);
  
  /* Text & Typography */
  --text-primary: #f8fafc;           /* Slate 50 */
  --text-secondary: #94a3b8;         /* Slate 400 */
  --text-muted: #64748b;             /* Slate 500 */
  
  /* Status Colors */
  --status-pending: #f59e0b;         /* Amber 500 */
  --status-in-progress: #3b82f6;     /* Blue 500 */
  --status-completed: #10b981;       /* Emerald 500 */
  --status-danger: #ef4444;          /* Red 500 */
  --status-walkover: #8b5cf6;        /* Purple 500 */

  /* Borders & Dividers */
  --border-subtle: rgba(148, 163, 184, 0.15);
  --border-focus: #10b981;
}
```

### 2.2 Typography
* **Primary Font Stack:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`
* **Monospace / Score Stack:** `"JetBrains Mono", "SF Mono", Consolas, "Liberation Mono", monospace` (used for score displays, tiebreaks, and court times)
* **Scale:**
  * `Display 1` (Hero Titles): 2.5rem (40px), Bold (700)
  * `Heading 1` (Tournament / Category Headers): 1.875rem (30px), Semi-Bold (600)
  * `Heading 2` (Card Titles / Round Labels): 1.25rem (20px), Semi-Bold (600)
  * `Body Regular`: 1rem (16px), Regular (400)
  * `Body Small / Metadata`: 0.875rem (14px), Regular (400)
  * `Badge / Micro`: 0.75rem (12px), Medium (500), Uppercase tracking +0.05em

### 2.3 Glassmorphism & Elevation
* **Card Elevation:** `box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2);`
* **Modal Elevation:** `box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4);`
* **Glass Backdrop:** `backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);`

---

## 3. Information Architecture & Navigation

```
Global Header / Nav
├── Brand Logo & Tournament Selector
├── Main Navigation: Tournaments | Academies | Leaderboards | Players
└── User Actions: Search | Dark/Light Toggle | User Profile / Sign In
```

### 3.1 Tournament Navigation Hub (`/t/<slug>`)
When viewing an active tournament, a persistent contextual secondary sub-nav provides immediate access across:
1. **Overview / Draws:** Visual bracket trees and group standings.
2. **Order of Play:** Daily court matrix and hourly match schedule.
3. **Participants:** Registered players, seeding list, check-in statuses.
4. **Live Scores:** Real-time scoreboard with 5-second polling updates.
5. **Manage (Admin Only):** Setup wizard, category creation, team drafts, match reporting.
6. **Export:** PDF Draw, Order of Play, and Roster downloads.

---

## 4. Key Component Specifications

### 4.1 Unified Organizer Wizard
The organizer workflow is consolidated into a 4-step progressive disclosure wizard:
* **Step 1: Setup:** Tournament name, game type, multi-day calendar (start/end dates), daily operating hours (`court_operating_start` / `court_operating_end`), court count, and court naming.
* **Step 2: Categories:** Modular cards to add categories (Men's Singles, Mixed Doubles, Team League). Each card exposes format selection, set/game rules, and entry fees.
* **Step 3: Registration & Seeding:** Participant roster grid with seed assignment inputs, drag-and-drop or manual seed override, check-in switches, and payment status indicators.
* **Step 4: Execution & Brackets:** Action bar featuring "Generate Brackets", "Reset Bracket" (safeguarded by confirmation modals), and "Launch Tournament".

### 4.2 Interactive Geometric Bracket Visualizer
* **Layout Structure:** Multi-column layout where each column represents a Tournament Round (Round of 32, Sweet 16, Quarter-Finals, Semi-Finals, Final).
* **Match Node Card:**
  * Displays participant seeds, names (or pair names), and score boxes.
  * Winner card slot highlighted in `--color-primary` with bold typography.
  * Loser card slot subtly dimmed (`opacity: 0.65`).
  * Direct click opens the Admin Score Reporting Modal (for authorized organizers) or opponent comparison popup (for public viewers).
* **Dynamic SVG Connectors:**
  * An overlaid `<svg>` canvas calculates the exact $(x, y)$ client coordinates of match outgoing connector pins and next-round incoming connector pins.
  * Draws smooth cubic Bézier or orthogonal step curves linking winners to subsequent rounds.
  * Automatically recalculates on browser window resize.

### 4.3 Group Stage Team League Interface
* **Team Draft Wizard:**
  * **Mode A (Chit Draw):** Interactive modal allowing organizers to pick players from a live unassigned pool for each team. The UI cross-validates and disables already-picked players to prevent accidental duplicates.
  * **Mode B (Auto Tier Draft):** Auto-distributes 1 player from each Tier (A, B, C, D, E) per team with a single click, showing instant balance verification.
* **3-Rubber Fixture Card:**
  * Parent card represents the Team Tie (Team Alpha vs Team Beta, e.g., Target: 11 of 21 games).
  * Collapsible sub-cards display the 3 individual Rubbers:
    * Rubber 1: Tier A Singles
    * Rubber 2: Doubles (Tier B + Tier C)
    * Rubber 3: Tier D Singles
  * Real-time sum indicator showing games won (e.g. `12 - 9`, Winner: Team Alpha).

### 4.4 Order of Play (Court Matrix & Timeline)
* **Day Selector Tabs:** Horizontal pill tabs representing Tournament Day 1, Day 2, Day 3 with match count badges.
* **Court Columns:** Responsive horizontal grid with columns for Court 1, Court 2, etc.
* **Match Blocks:**
  * Display scheduled start time or "Not Before [Time]" flag.
  * Display Category pill badge (e.g. `Men's Open Singles`).
  * Progression Lock Indicator: A lock icon appears on downstream fixtures if feeder matches are still pending, preventing premature court dispatching.

### 4.5 Score Reporting Modal
* Dynamic form adapting to category rules:
  * If **Total Games:** Two numeric inputs with real-time differential calculation.
  * If **Tennis Sets:** Multiple set rows with game inputs and tiebreak superscript fields (e.g., Set 1: `7`-`6`, Tiebreak: `5`).
  * If **Group Stage Rubber ($T=7$):** Validation rule requiring $G_1 + G_2 = 7$ (or 4–3 with tiebreak), with automated walkover remainder allocation.

---

## 5. Responsive Behavior & Breakpoints

| Breakpoint | Target Devices | Layout Adaptations |
| :--- | :--- | :--- |
| **Mobile (< 768px)** | Smartphones | Single-column stack. Brackets switch to horizontal swipe/scroll container with sticky round headers. Order of Play switches from multi-column grid to vertical chronological list with court filter chips. |
| **Tablet (768px – 1024px)** | iPads / Tablets | 2-column dashboard layout. Brackets viewable in pinch-to-zoom SVG viewport. |
| **Desktop (> 1024px)** | Laptops & Monitors | Full multi-column bracket tree with SVG vector connectors, side-by-side court matrix, and multi-pane organizer wizard. |

---

## 6. Accessibility & Usability (a11y)
* High contrast ratio (> 4.5:1) across all text elements against dark slate backgrounds.
* All interactive match cards, tabs, and buttons feature explicit ARIA attributes (`role="tab"`, `aria-selected`, `aria-expanded`).
* Visible focus indicators (`outline: 2px solid var(--color-primary); outline-offset: 2px;`) for keyboard navigation.
