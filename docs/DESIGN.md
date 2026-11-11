# The Baseline Society Design System — Heritage Tennis Club Theme

## 1. Visual Philosophy & Surface Polarity
The Baseline Society uses a **single light-mode Heritage Club color system** inspired by classic grass-court and clay-court tennis clubs. There is **no dark/light theme switcher**; every view renders consistently with crisp daylight legibility (`color-scheme: light`) across desktop, mobile, print previews, and PDF exports.

- **Club Surface Canvas**: Ivory Court (`#FDFBF6`) for the primary page canvas and elevated cards, layered over warm Cream (`#F4EFE3`) and Sand (`#E8E0CC`) secondary containers.
- **Court Line & Header Architecture**: Court Green (`#0F3D2E`) anchors navigation bars, hero banners, bracket round headers, table headers, and primary actions.
- **Prestige Accents**: Champion Gold (`#C9A55C`) highlights active court baselines, hero CTAs, live fixture highlights, bracket path traces, and section header borders.
- **Clay Accent**: Clay (`#B5593A`) is a tertiary accent for live-match badges, alerts that need warmth, and secondary highlights.
- **Typography Ink**: Deep Green Ink (`#0B2B20`) provides high-contrast readability against Ivory Court and Cream surfaces.

---

## 2. Core Palette Tokens (`app/web/static/css/style.css` `:root`)

| Token | Value | Role & Usage |
|---|---|---|
| `--bg-primary` | `#FDFBF6` | Ivory Court main canvas background |
| `--bg-secondary` | `#F4EFE3` | Cream secondary panels, nested boxes, alternating table stripes |
| `--bg-tertiary` | `#E8E0CC` | Sand hover states, subtle header fills, pill wells |
| `--bg-card` | `#FDFBF6` | Elevated card, modal, and fixture surfaces |
| `--text-primary` | `#0B2B20` | Deep Green Ink primary copy and headings |
| `--text-secondary` | `#2F4A3E` | Muted green body descriptions, metadata labels |
| `--text-muted` | `#55695E` | Subtle captions, placeholders, timestamps |
| `--accent-primary` | `#0F3D2E` | Court Green navbar, hero gradient, primary buttons, borders |
| `--accent-primary-hover` | `#0A2D21` | Hover/active state for Court Green buttons and interactive controls |
| `--accent-primary-text` | `#0F3D2E` | Link and small label text on Ivory Court (already AA-safe) |
| `--accent-secondary` | `#C9A55C` | Champion Gold baselines, hero CTAs, active connector glow, divider stripes |
| `--accent-secondary-hover` | `#B8934A` | Hover state for `.btn-gold` and Gold interactive actions |
| `--accent-secondary-text` | `#7A5F1E` | AA-safe Antique Gold small text on light backgrounds |
| `--accent-tertiary` | `#B5593A` | Clay live badges, warm alerts, secondary highlights |
| `--accent-tertiary-hover` | `#9A482C` | Hover state for Clay interactive actions |
| `--accent-tertiary-text` | `#9A482C` | AA-safe Clay small text on light backgrounds |
| `--gradient-court` | `linear-gradient(135deg, #0F3D2E 0%, #1A5A43 100%)` | Navbar and hero court gradient |

### Accessibility & Contrast Pairing Rules
Ratios below were calculated with the WCAG 2.x contrast formula.

1. **Ivory on Court Green**: Use `#FDFBF6` text on `#0F3D2E` headers, navbars, round banners, and primary buttons (11.8:1).
2. **Gold on Court Green**: Use `#C9A55C` for accents, icons, and text on `#0F3D2E` surfaces (5.2:1).
3. **Small Brand Text on Light Canvas**: Use `--accent-secondary-text` (`#7A5F1E`, 5.8:1 on Ivory) or `--accent-tertiary-text` (`#9A482C`, 6.1:1 on Ivory) instead of raw `#C9A55C`/`#B5593A` when styling small body links, table labels, or metadata tags on `#FDFBF6`/`#F4EFE3`. Raw Champion Gold is for fills, borders, and large display text only.
4. **Text on Gold Surfaces**: Pair `#C9A55C` fills with `#0B2B20` Deep Green Ink (6.5:1), for example on gold call-to-action buttons and draft tier badges.
5. **Text on Clay Surfaces**: Pair `#B5593A` fills with `#FFFFFF` text (4.7:1). Do not use dark ink on Clay (3.2:1 fails AA).
6. **Semantic Status & Tier Distinctions**: Preserve distinct emerald green, amber, purple, cyan/azure, and crimson hues tuned for light-surface contrast across match results, live indicators, and 5-tier Team Draft roles (A–E). Because Court Green is now the brand color, success states should use a brighter emerald (not Court Green) and always pair color with an icon or label so they are not confused with brand chrome.

---

## 3. Component & Layout Patterns
- **Navigation & Hero**: `.navbar` renders `--gradient-court` with a `3px solid var(--accent-secondary)` Gold baseline; `.hero` pairs Court Green framing with a Champion Gold primary CTA button.
- **Modals & Loader**: `.glass-modal`, `#matchModal`, `#tierPickerModal`, `#captainsLineupModal`, and `#global-loader` (`.loader-overlay`) use bright Ivory Court / frosted Cream backdrops with Deep Green Ink text and Green/Gold court accents.
- **Brackets & Match Cards**: `.tennis-match`, `.round-title`, `.standings-table`, `.round-robin-grid`, and `.bracket-connector-path.path-highlighted` render crisp Court Green boundaries, subtle Cream surface fills, and Champion Gold active match highlighting. Live matches add a Clay badge.
- **Print & PDF Exports (`print_layout.html`, `export/*.html`)**: Clean `#ffffff` paper with `#0B2B20` typography, `#0F3D2E` section/round/court banners, `#C9A55C` baseline dividers, `#F4EFE3`/`#E8E0CC` row shading, and `#0F3D2E`/`#FDFBF6` floating print preview controls.

---

## 4. Typography & Brand Marks
- **Display / Headlines**: Cormorant Garamond (500–600), used for the wordmark, page titles, and round banners.
- **Interface / Data**: Inter (400–600), used for scores, draws, schedules, forms, and tables.
- **Monogram**: A serif "B" inside a double Champion Gold ring, sitting on a court baseline; use Gold and Ivory on Court Green, or Court Green on Ivory for light backgrounds.
- **Tagline**: "Every draw, every court, every champion."