# The Baseline Society Design System — Refined Club UI

## 1. Design Philosophy
The Baseline Society feels like a well-kept private tennis club translated into software: calm, warm, precise. The interface is quiet so tournament data (draws, scores, schedules) is the star. Brand color is used with restraint, and motion is soft and purposeful.

- **Single light theme.** No theme switcher. `color-scheme: light` everywhere (desktop, mobile, print, PDF).
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
- Mobile: bottom tab bar (5 items max), 56px tall, active item marked by a Gold top indicator.

### 6.2 Buttons
- **Primary** (`.btn-primary`): Court Green fill, Ivory text, `--radius-md`, 44px height, 20px horizontal padding.
- **Gold** (`.btn-gold`): Champion Gold fill, Ink text. Use at most one per screen, for the single most important action.
- **Secondary:** white fill, `--border-strong`, Ink text. **Ghost:** transparent, Court Green text, Green-tint hover.
- **Destructive:** Danger fill with white text, always behind a confirmation.
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

---

## 7. Print & PDF Exports (`print_layout.html`, `export/*.html`)
Clean `#FFFFFF` paper with `#14221C` typography, `#0F3D2E` section, round, and court banners, `#C9A55C` baseline dividers, `#F2EEE4` and `#E7E1D2` row shading, and the stacked logo (light version) in the header. No shadows, no animation, and no gradients in print. Floating print preview controls use `#0F3D2E` with `#FAF8F3` text.

---

## 8. Logo & Brand Marks
- **Monogram:** serif "B" inside a double Champion Gold ring, resting on a gold baseline with a small ball dot. On Court Green use Gold ring and Ivory letter; on light surfaces use Gold ring and Court Green letter.
- **Wordmark:** "THE" small and tracked in Gold (or Antique Gold on light), "Baseline Society" in Cormorant Garamond 600.
- **Minimum sizes:** full logo 120px wide; monogram 40px. Below 40px use the letter only.
- **Clear space:** at least the height of the "B" on all sides.
- **Tagline:** "Every draw, every court, every champion."