---
name: Mint Financial
colors:
  surface: '#f9f9ff'
  surface-dim: '#d7dae3'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3fd'
  surface-container: '#ebeef7'
  surface-container-high: '#e5e8f2'
  surface-container-highest: '#dfe2ec'
  on-surface: '#181c23'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#2d3138'
  inverse-on-surface: '#eef0fa'
  outline: '#6b7b72'
  outline-variant: '#bacac1'
  surface-tint: '#006c4f'
  primary: '#006c4f'
  on-primary: '#ffffff'
  primary-container: '#00d09c'
  on-primary-container: '#00533c'
  inverse-primary: '#2fe0aa'
  secondary: '#006c4f'
  on-secondary: '#ffffff'
  secondary-container: '#6ef7c6'
  on-secondary-container: '#007153'
  tertiary: '#b02c31'
  on-tertiary: '#ffffff'
  tertiary-container: '#ff9d98'
  on-tertiary-container: '#91131e'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#59fdc5'
  primary-fixed-dim: '#2fe0aa'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#71fac8'
  secondary-fixed-dim: '#50ddad'
  on-secondary-fixed: '#002116'
  on-secondary-fixed-variant: '#00513b'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3af'
  on-tertiary-fixed: '#410005'
  on-tertiary-fixed-variant: '#8e101c'
  background: '#f9f9ff'
  on-background: '#181c23'
  surface-variant: '#dfe2ec'
typography:
  display-portfolio:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.03em
  display-portfolio-mobile:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0.01em
  numeric-ticker:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.01em
  label-md:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-mobile: 0.75rem
  margin: 1.5rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

This design system establishes an approachable, friction-free wealth-building environment tailored for mobile-first retail investors. It balances consumer clarity with institutional rigor, removing visual noise to make personal finance feel transparent and optimistic rather than daunting.

The visual style is **Modern Fintech Minimalism**:
- Pristine white surfaces contrasted by rich, legible charcoal text.
- Focused semantic color hits: energetic emerald mint for growth, neutral slate for context, and crisp crimson for negative deltas.
- Tactile, content-first cards with deep micro-borders and soft ambient diffusion rather than heavy physical drops.
- Generous touch targets and crisp data visualizations that instill immediate operational confidence.

## Colors

The palette relies on deliberate, purposeful hierarchy to prioritize critical financial indicators:

- **Primary Brand / Positive (`#00D09C`)**: The core interactive color and positive performance indicator. Used for primary call-to-actions, upward asset trends, portfolio gains, and verified trust tags.
- **Primary Pressed / Shade (`#00B386`)**: Deepened mint state utilized for button presses, interactive highlights, and active chart fills.
- **Negative / Alert (`#EB5757`)**: Explicit downward indicators, loss states, critical warnings, and sell actions. Must maintain 4.5:1 contrast against surface backgrounds.
- **Neutral Foreground (`#1E2229`)**: Core typography color for balances, company names, and high-priority figures. A deeper absolute charcoal (`#121212`) is reserved for primary metric numerals.
- **Secondary Neutral (`#7C7E8C`)**: Muted slate for secondary labels, timestamps, metadata, and placeholder text.
- **Surfaces**: Pure canvas background (`#FFFFFF`), paired with secondary component fills (`#F8F9FA` and `#F4F6F8`) and micro-stroke dividers (`#E5E7EB`).

## Typography

Typography centers around **Inter** for exceptional screen legibility across dense data interfaces.

Key implementation rules:
- **Tabular Figures**: Every quantitative data element, stock ticker, portfolio valuation, and performance delta must render with `font-feature-settings: "tnum" 1, "cv05" 1` to prevent horizontal shifting during live market updates.
- **Hierarchy Stacking**: Numeric metrics prioritize weight over size. A 16px medium/semibold amount stands out clearly against a 12px regular label without dominating screen real estate.
- **Letter Spacing**: Negative tracking is applied exclusively to headings over 20px to preserve tight, modern editorial density.

## Layout & Spacing

The layout utilizes a mobile-first fluid column structure engineered for handheld interaction:
- **Mobile Grid**: 4 fluid columns with `12px` (`0.75rem`) gutters and `16px` (`1rem`) screen margins. All critical interaction zones conform to a minimum 48px tap container height.
- **Tablet & Web Expansion**: 8 to 12 columns with `16px` gutters and `24px` margins, capping investment dashboard containers at `1120px` to maintain focused scan paths.
- **Rhythm**: Spacing adheres strictly to an 8pt base grid with a 4pt sub-grid for internal component alignment (e.g., badges, pill chips, and inline price deltas).

## Elevation & Depth

Visual hierarchy uses clean flat boundaries reinforced by subtle ambient diffusion:

- **Level 0 (Flat / Canvas)**: Pure `#FFFFFF` or background canvas `#F8F9FA` with 0px blur and no outline. Used for baseline layouts.
- **Level 1 (Card Rest)**: Surface `#FFFFFF` layered over `#F8F9FA` background with a subtle border of `1px solid #E5E7EB` and ambient shadow: `0px 2px 8px -2px rgba(30, 34, 41, 0.04)`.
- **Level 2 (Interactive Floating / Active State)**: Lifted cards and action bars: `0px 6px 16px -4px rgba(30, 34, 41, 0.08)`, stroke drops to `1px solid rgba(0, 0, 0, 0.06)`.
- **Level 3 (Overlays & Sheets)**: Bottom sheets, portfolio modals, and sticky order ribbons: `0px -4px 24px 0px rgba(18, 18, 18, 0.12)`, no border required.

## Shapes

The geometric vocabulary balances modern ergonomics with high UI density:
- **Base Components (`rounded-md` / 8px)**: Inputs, segmented tabs, and compact metric badges.
- **Containers & Cards (`rounded-lg` to `rounded-xl` / 16px to 24px)**: Primary stock cards, wealth summary banners, and bottom navigation sheets.
- **Action Triggers (`rounded-full`)**: Primary action buttons, category pill selectors, and quick-filter chips utilize fully rounded ends to indicate interactive tap affordability.

## Components

### Buttons
- **Primary CTA**: Full background `#00D09C`, text `#FFFFFF` (Semibold), height 48px, fully rounded or 12px radius. Active state transitions to `#00B386`.
- **Secondary / Ghost**: Background `#F4F6F8`, text `#1E2229`, zero border; hover/active introduces `#E5E7EB`.
- **Destructive / Sell**: Soft tinted background `rgba(235, 87, 87, 0.12)` with `#EB5757` bold text for secondary sell flows, solid `#EB5757` with white text for definitive confirmations.

### Cards & Asset Tiles
- **Holding Card**: Pure `#FFFFFF` surface, `1px solid #E5E7EB` border, 16px border-radius, 16px internal padding. Left section: Company logo avatar (40x40px, rounded-lg) + Ticker + Exchange name. Right section: Current price + 24h percentage delta (in `#00D09C` or `#EB5757`).
- **Portfolio Summary Card**: Ambient gradient underlay (`#00D09C` at 6% opacity to transparent white) wrapped in a crisp 1px stroke.

### Filter & Category Chips
- **Inactive**: Solid `#FFFFFF` fill with `1px solid #E5E7EB`, text `#7C7E8C`, padding `6px 14px`, pill-shaped.
- **Active**: Background `#E6FAF5` (5% tint), border `1px solid #00D09C`, text `#00B386` (Font weight 600).

### Inputs & Financial Keypads
- **Amount Inputs**: Large tabular font (28px semibold) anchored with fixed currency glyph. Outline remains unobtrusive `#E5E7EB` at rest and smoothly scales to a 2px focused ring of `#00D09C`.
- **Search Bar**: Background `#F4F6F8`, icon color `#7C7E8C`, pill-shaped or 12px radius, no border.

### Badges & Micro-Pills
- **Gain Badge**: Background `rgba(0, 208, 156, 0.12)`, text `#00B386`, bold font weight, padding `2px 8px`, border radius `4px`. Preceded by an upward chevron.
- **Loss Badge**: Background `rgba(235, 87, 87, 0.12)`, text `#EB5757`, bold font weight, padding `2px 8px`, border radius `4px`. Preceded by a downward chevron.

### Navigation
- **Bottom Navigation Bar**: Fixed dock with `#FFFFFF` background, 1px top stroke `#E5E7EB`. Active item colored in `#00D09C` with subtle 4px dot indicator; inactive items rendered in `#7C7E8C`.