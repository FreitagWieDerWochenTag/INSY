# DESIGN.md – INSY design system

The design system for the INSY school projects: interactive pages that explain and run real code
(a neural network, a C library, a microcontroller sketch). It looks like Apple's product pages: calm,
lots of white space, big bold headlines, soft cards. The colors are inspired by Lufthansa's current look:
**navy and white as the base, yellow only where something is active**.

Visual reference with live component previews: the **INSY Design System** in Claude Design
(<https://claude.ai/artifact/KNZuCVMKkjNtotXPJXWULN>, private until shared). Reference implementation:
`NN/web/assets/style.css`. This file and the design system hold the same rules; change both together.

## Principles

1. **Navy and white carry the page.** Light mode: white cards (`surface`) on a light grey ground (`bg-2`),
   navy headings (`ink`). Dark mode: deep navy ground, slightly lighter navy cards, white headings.
2. **Yellow means "on".** `accent` is only used for things that are active right now: a lit display segment,
   a neuron's activation, a GPIO that is HIGH, a toggled bit, the current tab, the last step of a pipeline.
   If nothing is active, there is no yellow on the screen. Yellow is never used for text on white
   (use `accent-ink`).
3. **Cards, not borders.** Groups are cards with `radius-lg` and `shadow-card`, no outlines. Hairlines (`line`)
   only separate rows inside a card.
4. **System fonts.** San Francisco on Apple devices, Helvetica Neue / Segoe UI / Arial elsewhere. No web fonts:
   pages load fast and look native. Numbers use the mono face with tabular figures.
5. **Show the real thing.** Every number on a page comes from the real implementation. Hardware (displays, the
   serial monitor, a PCB) is drawn realistically in `hardware` navy, in both themes.

## Color

| Role | Tokens |
|---|---|
| Ground & surfaces | `bg`, `bg-2`, `surface`, `nav-bg` |
| Text | `ink` (headings), `text` (body), `muted` (secondary), `on-primary`, `on-accent`, `accent-ink` |
| Actions | `primary` (filled button, selected control) |
| Active | `accent`, `led` |
| Data | `s1` → `s2` → `s3` in this order, never cycled; positive weight = `s1`, negative = `s2` |
| Status | `good`, `bad`, always with a word ("ready", "error") |

All text pairs meet 4.5:1 in both themes (ink on surface 17.1:1, muted 5.6:1 / 6.9:1, navy on yellow 9.1:1).
The data colors pass the dataviz validator (lightness band, CVD separation, contrast) against both surfaces.

## Type

One family in three roles: `display` for titles (700, tight tracking −0.03em), `sans` for text, `mono` for data.
Scale: title-1 52 px, title-3 21 px, headline 17 px, lede 18 px, body 16 px, control/caption 13 px, data 13 px,
label 11 px. Running text max ~68 characters wide.

## Layout & shape

Max width 1180 px, side gutter at least 16 px. Cards: padding `space-4` (22 px), gaps 20–24 px.
Radii: `radius-sm` keys and inputs, `radius-md` switches and displays, `radius-lg` cards, `radius-pill`
tabs, buttons and segmented controls. Navigation: sticky, frosted (`nav-bg` + 20 px backdrop blur), 52 px tall.

## Motion

Short and physical: 150–250 ms color/opacity transitions, a 0.96 press scale on keys and buttons, a pulsing status dot
while something loads, flowing dashes on wires that carry current. Everything stops with `prefers-reduced-motion`.

## Writing

English, plain and specific. Status lines say what ran and how long it took ("computed by C as WebAssembly ·
main() 2.00 ms"). Errors say what failed and offer a way out (a Reload button).

## Components

Nav bar (frosted, current tab = yellow pill) · segmented control (selected = navy) · button (pill; primary = navy) ·
card (surface, radius-lg, shadow, no border) · bit switch (toggled = yellow track) · keypad (current = navy, untrained =
outlined) · 7-segment display (hardware navy, lit = led yellow) · data table (mono, tabular, hairlines) · loss chart
(s1/s2/s3, direct labels + legend + crosshair) · status line (yellow pulsing while loading, green ready, red error + Reload).
Previews and usage notes for each: see the Claude Design link above; the classes live in `NN/web/assets/style.css`.

## Using it in a new project

1. Create `<Project>/web/assets/style.css` starting with the token block below (light values on `:root`, dark values
   under `prefers-color-scheme: dark` and `[data-theme="dark"]`), then copy the component rules you need from
   `NN/web/assets/style.css`.
2. No web fonts. Use `var(--font)`, `var(--font-display)`, `var(--font-mono)`.
3. Every color comes from a token; no literal colors in components (hardware drawings such as a PCB are the exception).
4. Charts: series in the order `--s1`, `--s2`, `--s3`; run the dataviz palette validator if you add colors.
5. Add the project to the landing page `index.html` and to `.github/workflows/pages.yml`.

## Tokens (copy-paste)

```css
:root {
  color-scheme: light;
  --bg: #ffffff;            /* page */
  --bg-2: #f5f6f8;          /* grouped background, wells */
  --surface: #ffffff;       /* cards */
  --ink: #05164d;           /* navy: headings, primary text */
  --text: #1b2240;          /* body text */
  --muted: #5f6787;         /* secondary text */
  --line: rgba(5, 22, 77, 0.10);
  --primary: #05164d;       /* buttons, selected controls */
  --on-primary: #ffffff;
  --accent: #ffad00;        /* yellow: only for active / on states */
  --on-accent: #05164d;
  --accent-ink: #9a6400;    /* yellow-family text that stays readable on white */
  --s1: #1d4ed8;            /* chart / positive weight */
  --s2: #d97706;            /* chart / negative weight */
  --s3: #0d9488;            /* chart / third series */
  --good: #12805c; --bad: #c4321d;
  --hardware: #05164d;      /* display housing, serial monitor */
  --hardware-ink: #dfe4f2;
  --led: #ffad00;           /* lit segment */
  --shadow: 0 1px 2px rgba(5, 22, 77, 0.06), 0 8px 24px rgba(5, 22, 77, 0.07);
  --nav-bg: rgba(255, 255, 255, 0.72);
  --radius: 18px;
  --radius-sm: 10px;
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", "Segoe UI", Arial, sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", "Segoe UI", Arial, sans-serif;
  --font-mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --bg: #030b2a; --bg-2: #081538; --surface: #0b1a45; --ink: #ffffff; --text: #dfe4f2; --muted: #9aa5c8;
    --line: rgba(255, 255, 255, 0.10); --primary: #ffffff; --on-primary: #05164d; --accent-ink: #ffc24d;
    --s1: #5b8af0; --s2: #c98400; --s3: #14a89a; --good: #3ccf98; --bad: #ff7a66;
    --hardware: #020821; --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 10px 30px rgba(0, 0, 0, 0.35);
    --nav-bg: rgba(3, 11, 42, 0.72);
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #030b2a; --bg-2: #081538; --surface: #0b1a45; --ink: #ffffff; --text: #dfe4f2; --muted: #9aa5c8;
  --line: rgba(255, 255, 255, 0.10); --primary: #ffffff; --on-primary: #05164d; --accent-ink: #ffc24d;
  --s1: #5b8af0; --s2: #c98400; --s3: #14a89a; --good: #3ccf98; --bad: #ff7a66;
  --hardware: #020821; --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 10px 30px rgba(0, 0, 0, 0.35);
  --nav-bg: rgba(3, 11, 42, 0.72);
}
```
