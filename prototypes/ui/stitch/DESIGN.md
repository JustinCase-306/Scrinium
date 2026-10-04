---
name: Clear Desktop Organization
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0eded'
  surface-container-high: '#eae7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1b1b1c'
  on-surface-variant: '#424654'
  inverse-surface: '#303030'
  inverse-on-surface: '#f3f0ef'
  outline: '#737785'
  outline-variant: '#c3c6d6'
  surface-tint: '#0856cf'
  primary: '#0041a2'
  on-primary: '#ffffff'
  primary-container: '#0b57d0'
  on-primary-container: '#ced9ff'
  inverse-primary: '#b2c5ff'
  secondary: '#076d2e'
  on-secondary: '#ffffff'
  secondary-container: '#9cf7a7'
  on-secondary-container: '#147434'
  tertiary: '#364863'
  on-tertiary: '#ffffff'
  tertiary-container: '#4e607c'
  on-tertiary-container: '#c8dbfc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b2c5ff'
  on-primary-fixed: '#001847'
  on-primary-fixed-variant: '#0040a1'
  secondary-fixed: '#9cf7a7'
  secondary-fixed-dim: '#81da8d'
  on-secondary-fixed: '#002109'
  on-secondary-fixed-variant: '#005320'
  tertiary-fixed: '#d4e3ff'
  tertiary-fixed-dim: '#b5c7e8'
  on-tertiary-fixed: '#071c35'
  on-tertiary-fixed-variant: '#364862'
  background: '#fcf9f8'
  on-background: '#1b1b1c'
  surface-variant: '#e5e2e1'
typography:
  display-lg:
    fontFamily: Roboto Flex
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: 0px
  headline-lg:
    fontFamily: Roboto Flex
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: 0px
  headline-md:
    fontFamily: Roboto Flex
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: 0px
  title-lg:
    fontFamily: Roboto Flex
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: 0px
  title-md:
    fontFamily: Roboto Flex
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 30px
    letterSpacing: 0.15px
  body-lg:
    fontFamily: Roboto Flex
    fontSize: 20px
    fontWeight: '400'
    lineHeight: 30px
    letterSpacing: 0.15px
  body-md:
    fontFamily: Roboto Flex
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
    letterSpacing: 0.25px
  body-sm:
    fontFamily: Roboto Flex
    fontSize: 17px
    fontWeight: '500'
    lineHeight: 26px
    letterSpacing: 0.25px
  label-lg:
    fontFamily: Roboto Flex
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: 0.1px
  label-md:
    fontFamily: Roboto Flex
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0.1px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  margin: 2rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1.25rem
  space-lg: 2rem
  space-xl: 3rem
---

## Brand & Style

This design system is tailored for an elderly demographic (80+ years old), focusing on order, safety, and cognitive ease in personal file management. The aesthetic builds upon Material Design 3 principles adapted for absolute clarity, calm reassurance, and senior accessibility. Visual hierarchy is direct and unambiguous: no hidden gestures, no low-contrast secondary text, no ephemeral states, and no ambiguous iconography. 

The aesthetic is Modern Tactile Corporate—blending clean digital surfaces with physical desktop metaphors (cards, folders, visible tabs) that offer high visual affordance. Interactive controls possess substantial surface areas and obvious boundary definitions. The emotional tone evokes calm reliability, stability, and patience, eliminating digital anxiety through prominent confirmation states, large legible targets, and steady visual anchors.

## Colors

Color is applied intentionally to delineate functionality, indicate focus, and provide immediate cognitive confirmation. Contrast ratios strictly exceed WCAG AAA standards (7:1 for normal text, 4.5:1 for large graphical elements and buttons).

- **Primary (`#0B57D0`):** Reassuring cobalt blue. Used for primary navigation states, active folder selections, and key action buttons. Surfaces paired with pure white (`#FFFFFF`) text for maximum contrast.
- **Secondary / Success (`#137333`):** High-contrast deep forest green. Reserved for success alerts, completed file transfers, verified backup statuses, and destructive recovery points. Never paired with red in isolation to prevent color-blindness confusion.
- **Tertiary (`#4A5C78`):** Deep slate blue-gray. Used for secondary metadata chips, active filters, and structural boundary fills.
- **Neutral Core (`#1F1F1F` on `#F8F9FA` / `#FFFFFF`):** High-legibility dark charcoal for primary copy on an ultra-light gray surface to eliminate blinding stark white glare while preserving 14:1 contrast.
- **Borders & Dividers:** Defined using `#74777F` (outline) and `#C4C7C5` (outline-variant) to ensure distinct physical component edges that remain visible under lower visual acuity.

## Typography

The type scale is calibrated specifically for aging eyes, ensuring all body text starts at a minimum of 17px (scaling naturally to 18-20px for primary reading) and buttons utilize 20px+ weights.

- **Typeface:** `Roboto Flex` is selected for its mechanical stability, clear glyph separation, open counters, and high legibility at large scale.
- **Hierarchy Rules:** 
  - Never use light font weights (300 or below); regular (400), medium (500), and bold (600/700) are used exclusively.
  - Headings are kept tight and structured, never exceeding 36px on desktop to maintain spatial cohesion without causing line-wrapping issues in German compound words (e.g., *Dokumentenverwaltung*, *Ordnerstruktur*).
  - Body copy maintains a generous 1.5x line height minimum to prevent line-tracking skipping during reading.

## Layout & Spacing

The layout is built upon an anchored, fixed-pane desktop structure instead of unpredictable fluid responsive shifts. It features a persistent primary navigation rail on the left (minimum 280px wide), an expansive document staging center, and a dedicated action/preview panel on the right.

- **Rhythm:** An 8px base grid, stepped up with generous defaults to prevent accidental clicks or mis-taps. Minimum clickable surface gaps are maintained at `space-md` (20px).
- **Target Boundaries:** All interactive elements maintain a hard minimum target height and width of 56px.
- **Section Margins:** Canvas margins (`margin: 2rem`) ensure that interactive controls are never jammed against system taskbars or window borders.

## Elevation & Depth

Visual hierarchy combines physical outline containment with low-blur, high-contrast Material 3 tonal elevation:

- **Level 0 (Base Canvas):** Background color `#F8F9FA`. Completely flat with no shadow.
- **Level 1 (Card & Content Panes):** Surface color `#FFFFFF` with a crisp 1.5px structural border (`#C4C7C5`) and an ambient drop shadow: `0px 2px 6px rgba(0, 0, 0, 0.08)`.
- **Level 2 (Active Drag States & Menus):** Surface `#FFFFFF`, border 2px solid `#74777F`, shadow `0px 6px 16px rgba(0, 0, 0, 0.14)`.
- **Focus Rings:** Any focused interactive element generates an unequivocal dual-ring focus state: a 2px white gap followed by a 3.5px solid `#0B57D0` outline. Shadows are never used in isolation to signal interactive state changes.

## Shapes

Components utilize calm, soft rounded corners ranging between 14px and 16px (`roundedness: 2`). 

- **Containers & Cards:** 16px corner radius (`rounded-lg`), creating an approachable card look that visually groups content without sharp, clinical points.
- **Buttons, Inputs & Interactive Controls:** Uniform 14px–16px radius. Fully circular/pill shapes are avoided for operational buttons to preserve clear boundary edges and maintain generous horizontal padding for longer descriptive German labels.
- **Inner Selection Badges:** 8px–10px radius, maintaining consistent nested proportions inside 16px parent cards.

## Components

### Buttons
- **Primary Buttons:** Minimum height 56px (ideal 60px). Background `#0B57D0`, foreground `#FFFFFF`, border-radius 16px. Typography `label-lg` (20px, bold). Padding: 16px 28px. Accompanied by a 24px icon on the left with a minimum 12px gap from text.
- **Secondary Buttons:** Same dimensions, background `#FFFFFF`, border 2px solid `#0B57D0`, foreground `#0B57D0`.
- **Destructive Actions:** Require a secondary explicit modal confirmation step. Styled with 2px solid `#BA1A1A` and explicit textual labels (e.g., *Endgültig löschen*).

### Text Inputs & Search
- **Height & Frame:** Minimum height 60px. White background with a 2px static outline (`#74777F`).
- **Typography:** Input text and placeholders set at `body-lg` (20px). Placeholder text uses high-contrast slate (`#444746`), never faint gray.
- **Labels:** Always floating or pinned permanently above the input field at `label-md` (18px, bold). Labels never disappear upon typing.

### Checkboxes & Radio Buttons
- **Sizing:** Hitbox 56px x 56px with a visual indicator of 28px x 28px.
- **Border:** 2.5px solid `#1F1F1F`. Active checked state fills with `#0B57D0` displaying a bold white checkmark.
- **Labeling:** Text is positioned to the right with `body-lg` (20px) and is fully clickable as part of the toggle hit area.

### File & Folder Cards
- **Structure:** Bounded cards with a 1.5px border (`#C4C7C5`), 16px border-radius, and 20px internal padding.
- **File Icons:** Scaled to 40px x 40px with unmistakable color coding (e.g., Blue for documents, Green for receipts/scans).
- **Secondary Details:** File size and modification dates use `body-sm` (17px, bold), avoiding low-contrast captions.

### Chips & Filters
- **Height:** 48px minimum height with 12px corner radius.
- **Visuals:** Static state features 1.5px solid `#74777F` with `#FFFFFF` background. Selected state uses `#0B57D0` background with white text and a leading checkmark icon.

### Modal Dialogs
- Centered overlay with a 40% opacity black backdrop. Modal width fixed to 640px minimum.
- Includes a prominent header (`headline-lg`), simple single-step instructions, and side-by-side large 56px action buttons labeled explicitly with full verbs (e.g., *Datei speichern*, *Abbrechen*).