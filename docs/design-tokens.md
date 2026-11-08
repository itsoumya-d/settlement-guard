# Paymark design tokens

Extracted from the live Paymark/Worldline property and its stylesheet on 2026-11-04.

## Typography

| Role | Family | Size | Weight | Line height | Tracking | Colour |
| --- | --- | --- | --- | --- | --- | --- |
| Body | Roboto, sans-serif | 18px | 400 | 27px | normal | `#000000` |
| H1 | Roboto, sans-serif | 60px | 600 | 64.8px | normal | `#ffffff` on hero, `#1e1e1e` on light |
| H2 | Roboto, sans-serif | 44px | 600 | 49.28px | normal | `#000000` |
| Eyebrow | Roboto, sans-serif | 14px | 600 | 19.6px | 1.68px | `#e6746b` |
| Button | Roboto, sans-serif | 16px | 600 | normal | 0.5px | `#ffffff` |
| Focus ring | — | — | — | — | — | `#36c6f9` |

The site also ships Proxima Nova, DM Sans, Simply Circular, Degular and Neue Haas Grotesk webfonts. The computed body and heading styles resolve to **Roboto**, so the reference UI and CV use Roboto as the primary family.

## Colour

| Token | Value | Use |
| --- | --- | --- |
| `--sg-red` | `#d9291c` | Primary action, alert accent |
| `--sg-salmon` | `#e6746b` | Eyebrow and secondary accent |
| `--sg-ink` | `#1e1e1e` | Headings and body on light surfaces |
| `--sg-muted` | `#575469` | Secondary copy |
| `--sg-surface` | `#f9f9f9` | Cards and table headers |
| `--sg-line` | `#e9e9e9` | Borders |
| `--sg-focus` | `#36c6f9` | Focus ring |
| `--sg-radius` | `5px` | Buttons, cards, inputs |

The wider Paymark palette also includes `#5a3c9f` (purple), `#46beaa` (teal), `#e67300` (orange), `#1067d5` (blue) and `#292540` (dark purple). They are retained as supporting accents in the stylesheet source but not used for the primary operations surface.

## Where the tokens are applied

- `src/main/resources/static/styles.css` — dashboard body, headings, buttons, cards, table, focus ring and responsive breakpoints.
- `docs/design-tokens.md` — this reference.
- The companion PDF CV uses the same Roboto family, `#d9291c` accent, `#e6746b` eyebrow, `#1e1e1e` ink and 5px radius.

## Layout geometry

- Content max width: `1120px`.
- Section spacing: `48px` top, `72px` bottom.
- Card gap: `16px`.
- Card padding: `24px`.
- Button padding: `11px 24px`.
- Table cell padding: `14px 18px`.
- Mobile breakpoints: `900px` (2-column cards) and `560px` (single column).
