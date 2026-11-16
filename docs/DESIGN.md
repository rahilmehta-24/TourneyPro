# The Baseline Society Design System — Heritage Club Theme

## 1. Design Philosophy
The Baseline Society feels like a well-kept private tennis club translated into software: calm, warm, precise. The interface is quiet so tournament data (draws, scores, schedules) is the star. Brand color is used with restraint, and motion is soft and purposeful.

- **Single light theme.** No theme switcher. `color-scheme: light` everywhere (desktop, mobile, print, PDF). Declare `<meta name="color-scheme" content="light">` and `:root { color-scheme: light; }` so mobile browsers' forced dark modes do not recolor the app.
- **Natural surfaces.** Warm ivory and stone neutrals, like linen and court-side stone, instead of stark white. Cards are pure white so they lift gently off the canvas.
- **Brand in moderation.** Court Green is for structure and primary actions. Champion Gold is a highlight, never a background for body text. Clay is a rare warm accent.
- **Depth through soft shadow, not heavy borders.** Shadows are tinted green-grey, never pure black.
- **Motion with meaning.** Animation confirms actions, shows progress, and guides the eye. Nothing bounces for its own sake.
- **Logo unchanged.** The serif "B" monogram in a double gold ring on Court Green stays the brand mark.

---

## 2. Color Tokens (`app/web/static/css/style.css` `:root`)

### 2.1 Surfaces & Text
| Token | Value | Usage |
|---|---|---|
| `--bg-primary` | `#FAF8F3` | Page canvas (Ivory) |
| `--bg-secondary` | `#F2EEE4` | Nested panels, table stripes (Linen) |
| `--bg-tertiary` | `#E7E1D2` | Hover fills, pill wells, subtle headers (Stone) |
| `--bg-card` | `#FFFFFF` | Cards, modals, fixtures, inputs |
| `--bg-overlay` | `rgba(11, 36, 28, 0.45)` | Modal backdrop |
| `--text-primary` | `#14221C` | Headings and body (15.5:1 on Ivory) |
| `--text-secondary` | `#3B4F44` | Descriptions, labels (8.3:1) |
| `--text-muted` | `#5E7066` | Captions, timestamps, placeholders (5.0:1 on Ivory, 4.6:1 on Linen) |
| `--border-subtle` | `#DDD6C5` | Dividers and card edges (decorative only) |
| `--border-strong` | `#8C8570` | Input and control borders (3.7:1 on white) |

### 2.2 Brand
| Token | Value | Usage |
|---|---|---|
| `--accent-primary` | `#0F3D2E` | Navbar, primary buttons, round headers, table headers (Court Green) |
| `--accent-primary-hover` | `#0B3024` | Hover |
| `--accent-primary-active` | `#082419` | Pressed |
| `--accent-primary-tint` | `#E3EDE7` | Selected rows, soft badges, focus wash |
| `--accent-primary-text` | `#0F3D2E` | Links and small labels on light surfaces (11.5:1) |
| `--accent-secondary` | `#C9A55C` | Baseline rule, hero CTA fill, active bracket path, large display accents (Champion Gold) |
| `--accent-secondary-hover` | `#B8934A` | Hover |
| `--accent-secondary-tint` | `#F4EBD4` | Gold-tinted highlights and badges |
| `--accent-secondary-text` | `#7A5F1E` | Small gold-toned text on light surfaces (5.7:1) |
| `--accent-tertiary` | `#B5593A` | Live-match badge fill, warm alerts (Clay) |
| `--accent-tertiary-hover` | `#9A482C` | Hover |
| `--accent-tertiary-tint` | `#F6E4DC` | Clay-tinted backgrounds |
| `--accent-tertiary-text` | `#9A482C` | Small clay-toned text on light surfaces (5.9:1) |

### 2.3 Semantic Status
Each status has a fill, a tint background, and a text color. Always pair with an icon or label; never rely on color alone, and never reuse Court Green as the success color.

| Status | Fill | Tint | Text on tint |
|---|---|---|---|
| Success (win, confirmed) | `#2F7D5A` | `#E1F0E8` | `#1F6A47` (5.6:1) |
| Warning (pending, delayed) | `#B7791F` | `#F8EBCF` | `#8A5A0B` (5.0:1) |
| Danger (retired, error) | `#B42318` | `#FBE4E0` | `#B42318` (5.4:1) |
| Info (scheduled, notice) | `#2B6C8C` | `#DFEDF4` | `#1F5F7E` (5.9:1) |

### 2.4 Gradients & Elevation
```css
--gradient-court: linear-gradient(135deg, #0F3D2E 0%, #17533F 100%);
--shadow-xs: 0 1px 2px rgba(15, 61, 46, 0.06);
--shadow-sm: 0 2px 6px rgba(15, 61, 46, 0.08);
--shadow-md: 0 8px 20px rgba(15, 61, 46, 0.10);
--shadow-lg: 0 20px 44px rgba(15, 61, 46, 0.16);
```

### 2.5 Contrast Pairing Rules
Ratios use the WCAG 2.x formula.
1. **Ivory on Court Green** (`#FAF8F3` on `#0F3D2E`, 11.5:1) for navbars, headers, and primary buttons.
2. **Gold on Court Green** (`#C9A55C` on `#0F3D2E`, 5.2:1) for accents, icons, and the baseline rule on dark surfaces.
3. **Ink on Champion Gold** (`#14221C` on `#C9A55C`, 7.1:1) for gold buttons and badges.
4. **White on Clay** (`#FFFFFF` on `#B5593A`, 4.7:1). Never dark ink on Clay.
5. **Raw gold and clay are fills only.** For small text on light surfaces use the `-text` tokens.
6. **Placeholders and captions** use `--text-muted` and must stay above 4.5:1 on their surface.

---

## 3. Typography
| Role | Font | Weight | Size / Line height |
|---|---|---|---|
| Display / wordmark | Cormorant Garamond | 600 | 40–56 / 1.1 |
| Page title (h1) | Cormorant Garamond | 600 | 32 / 1.15 |
| Section title (h2) | Cormorant Garamond | 600 | 24 / 1.2 |
| Body | Inter | 400 | 15 / 1.55 |
| UI label, button | Inter | 500–600 | 14 / 1.3 |
| Caption, metadata | Inter | 400–500 | 12–13 / 1.4 |
| Scores and draw numbers | Inter (tabular numerals) | 600 | 16–28 / 1.1 |

Font delivery: self-host Cormorant Garamond and Inter as WOFF2 (`font-display: swap`, preload the two used weights) instead of loading Google Fonts. Self-hosting removes a third-party request, keeps the Content-Security-Policy strict, and avoids privacy issues. PDF exports cannot use web fonts, so register the same fonts as local TTF files for `xhtml2pdf`/ReportLab.

Rules: use `font-variant-numeric: tabular-nums` for all scores, times, and standings so digits never jitter during live updates. Serif is for display only; all interactive UI is Inter. Maximum body line length is 70 characters.

---

## 4. Spacing, Radius & Layout
- **Spacing scale (4pt):** `4, 8, 12, 16, 20, 24, 32, 40, 56, 80`.
- **Radius:** `--radius-sm: 6px` (inputs, chips), `--radius-md: 10px` (buttons, small cards), `--radius-lg: 14px` (cards, modals), `--radius-xl: 20px` (hero panels), `--radius-pill: 999px` (badges, pills).
- **Touch targets:** minimum 44 × 44 px for every interactive element on mobile.
- **Grid:** 12 columns on desktop (max content width 1200px), 4 on mobile, 24px gutters on desktop and 16px on mobile.
- **Density:** generous padding (cards 20–24px) so draws and tables breathe; tables use 12px vertical cell padding.

---

## 5. Motion System
Motion is soft and quick. Elements decelerate into place and accelerate out. Use the tokens below; never hard-code durations.

```css
:root {
  /* Durations */
  --dur-instant: 90ms;    /* press feedback, checkbox */
  --dur-fast: 160ms;      /* hover, focus, color changes */
  --dur-base: 260ms;      /* menus, tabs, cards, toasts */
  --dur-slow: 420ms;      /* modals, page entrances */
  --dur-draw: 700ms;      /* bracket line drawing */

  /* Easings */
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);      /* default for most movement */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);        /* entrances: fast start, soft landing */
  --ease-in: cubic-bezier(0.4, 0, 1, 1);            /* exits */
  --ease-spring: cubic-bezier(0.34, 1.4, 0.64, 1);  /* tiny overshoot, used sparingly */
}
```

### 5.1 Interaction Patterns
| Element | Behavior | Timing |
|---|---|---|
| Buttons | Hover: background shift. Press: `scale(0.98)`. | `--dur-fast` / `--dur-instant`, `--ease-standard` |
| Cards and fixtures | Hover: `translateY(-2px)` and `--shadow-md`. | `--dur-base`, `--ease-out` |
| Links and nav items | Underline grows from left (`scaleX` 0 to 1). | `--dur-fast`, `--ease-standard` |
| Tabs | Active indicator slides to the new tab. | `--dur-base`, `--ease-standard` |
| Inputs | Border color transition and focus ring fade in. | `--dur-fast` |
| Dropdowns and menus | Fade in with `translateY(-6px)` to 0. | `--dur-base`, `--ease-out` |
| Modals | Backdrop fades in with 6px blur; panel fades and scales from 0.96 to 1. Exit is 30% faster. | `--dur-slow`, `--ease-out` |
| Toasts | Slide in from the bottom edge and fade; auto-dismiss fades out. | `--dur-base` |
| Page and section entrance | Fade up 12px; lists stagger by 40ms per item (max 8 items). | `--dur-slow`, `--ease-out` |
| Tournament bracket | Connector paths draw in via `stroke-dashoffset`, round by round; the winning path glows in Gold. | `--dur-draw`, `--ease-standard` |
| Live score change | The changed digit slides up (8px) and fades in; the row briefly tints Gold then settles. | `--dur-base` |
| Live badge | Soft pulsing ring on the Clay dot. | 1.8s loop, `ease-in-out` |
| Skeleton loading | Linen to Stone shimmer sweep. | 1.4s loop, linear |
| Global loader | A tennis ball bounces once per second on a gold baseline with a soft shadow that scales in sync. | 1s loop, `--ease-standard` |

### 5.2 Key Keyframes
```css
@keyframes fade-up   { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
@keyframes modal-in  { from { opacity: 0; transform: scale(0.96) translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes draw      { to { stroke-dashoffset: 0; } }
@keyframes live-ring { 0% { box-shadow: 0 0 0 0 rgba(181, 89, 58, 0.45); } 100% { box-shadow: 0 0 0 10px rgba(181, 89, 58, 0); } }
@keyframes shimmer   { from { background-position: -200% 0; } to { background-position: 200% 0; } }
@keyframes score-tick{ from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes ball-hop  { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-28px); } }

.bracket-connector-path { stroke-dasharray: var(--path-len); stroke-dashoffset: var(--path-len);
  animation: draw var(--dur-draw) var(--ease-standard) forwards; animation-delay: calc(var(--round) * 160ms); }
.skeleton { background: linear-gradient(90deg, #F2EEE4 25%, #E7E1D2 50%, #F2EEE4 75%); background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite; }
```

### 5.3 Performance & Accessibility
- Animate only `transform` and `opacity` (plus `box-shadow` and color on small elements). Never animate `width`, `height`, `top`, or `left`.
- Add `will-change` only during an active animation.
- **Respect reduced motion.** Under `prefers-reduced-motion: reduce`, remove movement and keep simple fades:
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }
  .bracket-connector-path { stroke-dashoffset: 0; }
}
```
- Looping animations (live pulse, shimmer, loader) must stop when reduced motion is on or when the tab is hidden.

---

## 6. Component Patterns
### 6.1 Navigation & Hero
- `.navbar`: `--gradient-court` with a `3px solid var(--accent-secondary)` baseline, 64px tall, sticky, with `--shadow-sm` after scrolling.
- `.hero`: Court Green framing, Cormorant Garamond display headline, one Gold primary CTA and one ghost secondary button.
- Mobile: bottom tab bar and compact top bar; see section 7.

### 6.2 Buttons
- **Primary** (`.btn-primary`): Court Green fill, Ivory text, `--radius-md`, 44px height, 20px horizontal padding.
- **Gold** (`.btn-gold`): Champion Gold fill, Ink text. Use at most one per screen, for the single most important action.
- **Secondary:** white fill, `--border-strong`, Ink text. **Ghost:** transparent, Court Green text, Green-tint hover.
- **Destructive:** Danger fill with white text, always behind a confirmation.
- **Mobile:** buttons grow to 48–52px, go full width in forms and sheets, and use press states instead of hover. Full rules in section 7.4.
- **Disabled:** 45% opacity, no hover, `cursor: not-allowed`. **Loading:** label replaced by a small spinner; width is preserved so the layout does not shift.

### 6.3 Forms
- Inputs are white, 44px tall, `--border-strong` border, `--radius-sm`. Labels sit above in 13px Inter 500.
- **Focus ring (all interactive elements):** `box-shadow: 0 0 0 2px var(--bg-primary), 0 0 0 4px var(--accent-primary);` with no outline removal without this replacement.
- Errors: Danger border, Danger-text message with an icon below the field; the field shakes 4px once (`--dur-base`) unless reduced motion is on.

### 6.4 Brackets, Draws & Match Cards
- `.tennis-match`: white card, `--radius-lg`, `--border-subtle`, `--shadow-xs`; the winner row is bold with a Green-tint background and a leading check icon.
- `.round-title`: Court Green banner with Ivory text, uppercase 12px tracking `0.08em`.
- `.standings-table`: Court Green header, Linen alternate rows, sticky header, right-aligned tabular numerals, hover row in Stone.
- `.round-robin-grid`: 1px `--border-subtle` grid, current match cell highlighted with Gold tint.
- `.bracket-connector-path`: 2px Stone by default; `.path-highlighted` is Gold with a soft glow and draws in with the motion tokens above.
- **Live match:** Clay pill with a pulsing dot and the word "LIVE"; the card gains a 3px Gold left border.

### 6.5 Modals, Drawers & Loader
- `.glass-modal`, `#matchModal`, `#tierPickerModal`, `#captainsLineupModal`: white panel, `--radius-lg`, `--shadow-lg`, 24px padding, `--bg-overlay` with 6px backdrop blur. Focus is trapped, Esc closes, and focus returns to the trigger.
- Mobile: modals become bottom sheets that slide up from the edge with a drag handle.
- `#global-loader` (`.loader-overlay`): frosted Ivory backdrop with the ball-hop animation (section 5.1).

### 6.6 Badges, Chips & Toasts
- Badges are pills with tint background, status text color, and an icon. Team Draft tiers A–E use distinct hues from section 2.3 plus a letter, never color alone.
- Toasts are white with a 4px status-colored left edge, `--shadow-md`, anchored bottom-center on mobile and bottom-right on desktop, auto-dismissing after 5s with a visible hover-pause.

### 6.7 Empty & Error States
Centered illustration-light layout: Cormorant Garamond heading, one line of Inter secondary text, and a single Primary action. Example copy: "No matches scheduled yet. Create the draw to get started."

### 6.8 Security-Related UI Patterns
- **PIN and password fields:** `type="password"` (or masked digits) with a show/hide toggle, `inputmode="numeric"` and `autocomplete="one-time-code"` for PINs, never place PINs, tokens, or transaction IDs in URLs.
- **Errors:** generic wording for authentication failures ("Invalid credentials", "PIN invalid or expired"); a clear lockout message with the remaining wait time after repeated failures; never reveal whether an account exists.
- **Destructive actions** (reset draw, remove staff, revoke PIN): confirmation sheet, Danger button, and for resets require typing the category name plus a reason.
- **Draft draws:** show an Info banner to staff ("Draft: only organizers can see this draw") and the public notice to everyone else; never render draft data to unauthorized users and hide it with CSS.
- **Role-aware UI:** hide controls the user cannot use, but always enforce permissions on the server.
- **Session expiry:** show a non-blocking "Session expired, sign in again" toast and preserve unsent score input.
- **Forms:** every form includes the CSRF token; never use `|safe` on user text.

---

## 7. Mobile Experience
Design mobile-first: phones are the primary device for scoring, checking draws, and receiving live updates at the court. Desktop layouts are enhancements, not the baseline.

### 7.1 Breakpoints & Resolution Matrix
The shipped CSS is **desktop-first**: mobile styles live in `@media (max-width: ...)` blocks (768 px and 640 px) so the desktop layout at 1025 px and above is never altered. New components follow the same convention. Design thinking stays mobile-first (phones are the primary device at the court), but the code keeps `max-width` queries to avoid desktop regressions.
```css
:root { --bp-phone: 640px; --bp-tablet: 1023px; --bp-desktop: 1024px; --bp-wide: 1600px; }
@media (max-width: 640px)  { /* phones: bottom sheets, bottom bar, 16px inputs */ }
@media (max-width: 768px)  { /* inputs 16px, compact nav */ }
@media (min-width: 641px) and (max-width: 1023px) { /* tablet portrait */ }
@media (min-width: 1600px) { /* wide screens and venue display */ }
@media (max-height: 500px) and (orientation: landscape) { /* landscape phones */ }
```

| Tier | Width | Required layout |
|---|---|---|
| Small phone | 320 to 359 px | Single column, 14 px gutters, no horizontal page scroll |
| Phone | 360 to 480 px (includes 440 px-wide phones) | Single column, bottom sheets, bottom tab bar |
| Large phone / small tablet | 481 to 640 px | Phone layout; two-column chips and stats allowed |
| Tablet portrait | 641 to 1023 px | Centered modals (not sheets), 2-column card grids, horizontally scrollable tables, optional bracket round tabs, tap targets stay 44 px |
| Desktop | 1024 to 1599 px | Full layout, hover states, 12-column grid (unchanged) |
| Wide / venue display | 1600 px and above | See section 10 |
| Landscape phone | height 500 px or less | Top bar 48 px, no fixed bars taller than 56 px, sheets `max-height: 100dvh`, content never hidden behind bars |
| Print / PDF | `@media print` | Section 8 |

Test at 320 × 568, 360 × 640, 390 × 844, 430 × 932, 440 × 956, 768 × 1024, 1024 × 768, 1440 × 900, 1920 × 1080, landscape phone, 200 % zoom, and large system text.

### 7.2 Layout, Spacing & Safe Areas
- **Viewport:** `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`. Never disable user zoom.
- **Gutters:** 16px (14px under 360px wide). Single-column layout; two columns only for compact stats and chips.
- **Cards:** 16–18px padding, 12px gap between cards, 24px between sections.
- **Safe areas:** pad fixed bars with `env(safe-area-inset-bottom)` and page edges with the left and right insets so nothing hides behind notches or the home indicator.
- **Heights:** use `100svh` or `100dvh`, not `100vh`, so the mobile browser toolbar does not clip content. Declare `height: 100vh;` first as a fallback for older browsers, then the `dvh` value.
- **Text:** body 15–16px, headings scale down (h1 28px, h2 22px), inputs always 16px or larger to prevent iOS zoom-on-focus. Never use hover-only information; tap reveals it instead.
- **Scrolling:** one vertical scroll per screen. Horizontal scrolling only inside deliberate containers (brackets, chip rows, wide tables) with scroll-snap and a fade at the edge.

### 7.3 Thumb Zone & Reach
- Place the most frequent actions in the bottom third of the screen: score entry, "Start match", "Save", primary navigation.
- Put destructive actions (cancel match, remove player) away from the primary action, never directly adjacent, and always behind a confirmation sheet.
- Top corners hold only low-frequency items (back, overflow menu, notifications).

### 7.4 Buttons on Mobile
Touch targets follow platform guidance: at least 44 × 44 px, with 48 × 48 px preferred. Adjacent targets are separated by at least 8px.

| Type | Height | Width | Use |
|---|---|---|---|
| **Primary** (`.btn-primary`) | 52px | Full width in forms, sheets, and action bars | The single main action on screen |
| **Gold** (`.btn-gold`) | 52px | Full width | The one hero action ("Create tournament"), max one per screen |
| **Secondary** | 48px | Full width or 50/50 with primary | Alternate actions |
| **Ghost / text** | 48px | Auto, min 64px wide | Low-emphasis actions such as Skip, Cancel |
| **Compact** | 40px visual, 44px tap area | Auto | Inline actions inside table rows and cards; extend hit area with padding or a pseudo-element |
| **Icon button** | 44 × 44 px (icon 24px) | Square | Toolbars and headers; always has an `aria-label` |
| **Chip / segmented** | 44px | Auto | Filters and view toggles |
| **Score stepper (+ / −)** | 56 × 56 px | Square | One-handed live scoring |

**Shape and type:** radius `12px` on mobile (`--radius-md` rises from 10px), Inter 16px at weight 600, horizontal padding 20px, label never wraps (shorten the label instead).

**Pairing:** when two buttons sit together, the primary action goes on the bottom (nearest the thumb) when stacked, or on the right when side by side. Never place two filled buttons next to each other; the second is Secondary or Ghost.

**States:**
- No hover on touch. Wrap hover styles in `@media (hover: hover)`.
- **Press:** `transform: scale(0.98)` plus the `--accent-primary-active` fill over `--dur-instant` (90ms) for immediate feedback.
- **Focus:** keep the shared focus ring for keyboard and switch-control users (`:focus-visible`).
- **Loading:** show a 18px spinner replacing the label, keep the width fixed, set `aria-busy="true"`, and ignore further taps.
- **Disabled:** 45% opacity, not focusable; explain why in helper text nearby, since there is no hover tooltip.
- **Success confirmation:** the label briefly swaps to a check icon (800ms) before returning, for actions with no visible result.

**Browser behavior:**
```css
button, .btn { -webkit-tap-highlight-color: transparent; touch-action: manipulation; user-select: none; }
.btn { min-height: 44px; padding: 0 20px; border-radius: 10px; font: 600 14px/1 Inter, sans-serif; }        /* desktop */
@media (max-width: 640px) { .btn { min-height: 48px; border-radius: 12px; font-size: 16px; } }          /* phones */
.btn-block { width: 100%; }
.btn:active { transform: scale(0.98); transition-duration: var(--dur-instant); }
@media (hover: hover) { .btn-primary:hover { background: var(--accent-primary-hover); } }
.icon-btn { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 12px; }
.btn-compact { min-height: 40px; position: relative; }
.btn-compact::after { content: ""; position: absolute; inset: -2px 0; } /* extends tap area to 44px */
```

### 7.5 Sticky Action Bar
For forms and detail screens, keep the primary action visible in a bottom bar rather than at the end of a long page.
```css
.action-bar {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
  display: flex; gap: 12px; padding: 12px 16px calc(12px + env(safe-area-inset-bottom));
  background: rgba(250, 248, 243, 0.94); backdrop-filter: blur(8px);
  border-top: 1px solid var(--border-subtle); box-shadow: 0 -8px 20px rgba(15, 61, 46, 0.08);
}
.page-with-action-bar { padding-bottom: calc(84px + env(safe-area-inset-bottom)); }
```
- One primary (flex 2) and at most one secondary (flex 1). A single primary spans the full width.
- The bar hides while the on-screen keyboard is open if it would cover the field; the field scrolls into view above the keyboard.
- When a bottom tab bar is also present, the action bar sits directly above it, and the page padding adds both heights.

### 7.6 Floating Action Button (FAB)
- 56px circle in Champion Gold with an Ink icon, `--shadow-md`, placed 16px from the right and 16px above the tab bar (plus the safe-area inset).
- Use it for the single creation action on a list screen ("New tournament", "Add match").
- **Extended FAB** (icon + label, 48px high) at the top of a list or on first view, collapsing to icon-only after scrolling.
- Hides on scroll down (`translateY(120%)`, `--dur-base`, `--ease-in`) and returns on scroll up. Never overlaps the action bar; it is hidden on screens that have one.

### 7.7 Navigation & Surfaces
- **Bottom tab bar:** 56px plus safe-area inset, maximum 5 destinations (Home, Draws, Schedule, Live, Profile). Icon 24px with a 12px label always visible. The active tab has a Gold 3px top indicator and a Court Green icon and label.
- **Top bar:** 56px, back button at left, title centered or left, one or two icon buttons at right. It condenses (shadow appears) once the page scrolls.
- **Bottom sheets replace modals** on phones: slide up from the bottom, 16px top radius, drag handle (36 × 4px), snap points at about 50% and 90% of `100svh`, swipe down or tap the backdrop to dismiss, content scrolls inside the sheet. Sheet actions use the full-width stacked buttons from section 7.4.
- **Menus** open as sheets, not small floating popovers.
- **Toasts** appear above the tab bar and action bar, never behind them, and are not used for critical errors.

### 7.8 Draws, Brackets & Tables on Mobile
- **Brackets:** show one round at a time with sticky round tabs (Round of 16, QF, SF, Final) and swipe between rounds using scroll-snap. A "Full bracket" button opens a pan-and-pinch-zoom view.
- **Match cards:** full width, 16px padding, tap anywhere to open the match sheet. Winner is bold with a check icon.
- **Standings and wide tables:** keep the first column (player) sticky, scroll the rest horizontally, 48px minimum row height, and right-aligned tabular numerals. Alternatively, collapse each row into a stacked card for tables with more than 5 columns.
- **Fixtures list:** group by day with sticky date headers; live matches float to the top with the Clay LIVE pill.
- **Live scoring:** the score screen uses large 56px stepper buttons and a prominent "Undo" button, with haptic feedback where available (`navigator.vibrate(10)`).

### 7.9 Forms on Mobile
- Inputs 48px tall, 16px text, labels above, helper text below, one field per row.
- Use `inputmode`, `type`, and `autocomplete` attributes (`numeric`, `email`, `tel`) so the right keyboard appears; use native date and time pickers.
- Validate on blur and on submit, scroll to the first error, and show the message below the field with an icon.
- Avoid stacking sheets on sheets; use a full-screen step for multi-step flows such as tournament setup, with a progress indicator at the top and Back / Next in the action bar.

### 7.10 Motion & Performance on Mobile
- Shorten durations by about 20% on phones (`--dur-base: 210ms`, `--dur-slow: 340ms`) and drop `--ease-spring` overshoot.
- Animate only `transform` and `opacity`. No parallax, no scroll-jacking, and no more than two looping animations visible at once.
- Use `backdrop-filter` only for the top bar, action bar, and sheet backdrop, and keep blur at 8px or less.
- Ambient background light is limited to the soft aurora and the baseline shimmer on hero and login screens. Use smaller, less blurred shapes, and never run it behind brackets, tables, or score screens.
- Pull-to-refresh uses a small tennis ball that rotates with the pull distance.
- Pause looping animations when the tab is hidden, and honor `prefers-reduced-motion` (section 5.3).
- **Budgets:** Largest Contentful Paint under 2.5s on a mid-range phone over 4G (desktop SSR target: 1.2s, per the PRD), Cumulative Layout Shift under 0.1, Interaction to Next Paint under 200ms, 60fps scrolling. Lazy-load below-the-fold images, preload the two fonts in use with `font-display: swap`, and reserve space for images and skeletons to avoid layout shift.

### 7.11 Mobile QA Checklist
- Every tappable element is at least 44 × 44 px and has 8px spacing from neighbors.
- Primary action is reachable with one thumb and not covered by the keyboard or the browser toolbar.
- No horizontal page scroll at 320px wide; text stays readable at 200% zoom.
- Safe areas respected in portrait and landscape.
- Inputs do not trigger zoom on focus.
- Status is never conveyed by color alone.
- Layout survives 200 % zoom, large system text, and text-spacing overrides; WCAG 2.2 AA target size is exceeded (44 px).
- Tablet portrait (641 to 1023 px) and landscape-phone layouts have been checked.
- Works with reduced motion on, with VoiceOver and TalkBack labels on icon buttons, and with a slow network (skeletons appear within 100ms).

---

## 8. Print & PDF Exports (`print_layout.html`, `export/*.html`)
Clean `#FFFFFF` paper with `#14221C` typography, `#0F3D2E` section, round, and court banners, `#C9A55C` baseline dividers, `#F2EEE4` and `#E7E1D2` row shading, and the stacked logo (light version) in the header. No shadows, no animation, and no gradients in print. Floating print preview controls use `#0F3D2E` with `#FAF8F3` text.

---

## 9. Logo & Brand Marks
- **Monogram:** serif "B" inside a double Champion Gold ring, resting on a gold baseline with a small ball dot. On Court Green use Gold ring and Ivory letter; on light surfaces use Gold ring and Court Green letter.
- **Wordmark:** "THE" small and tracked in Gold (or Antique Gold on light), "Baseline Society" in Cormorant Garamond 600.
- **Minimum sizes:** full logo 120px wide; monogram 40px. Below 40px use the letter only.
- **Clear space:** at least the height of the "B" on all sides.
- **Tagline:** "Every draw, every court, every champion."

---

## 10. Large Display / Venue TV Mode (1600 px and above)
For projectors and clubhouse monitors (PLAN WP 2.3):
- Root font size 20 to 24 px (`clamp(20px, 1.2vw, 24px)`), scores 64 px or larger, readable from 20 meters.
- Maximum contrast: Ivory text on Court Green, Gold for live highlights; no hover or tap-only interactions.
- Carousel rotates Live Matches, Order of Play (Now Playing / Up Next), and Leaderboard every 12 to 20 seconds; pause on keyboard focus, and respect reduced motion by switching to cross-fades.
- Safe margins of 5 % to avoid overscan clipping; layouts verified at 1920 × 1080 and 3840 × 2160.
- Read-only: no personal data, published draws only, protected by a revocable display token in the URL.
- Keep the screen awake (Wake Lock API where supported) and recover automatically after network loss.
