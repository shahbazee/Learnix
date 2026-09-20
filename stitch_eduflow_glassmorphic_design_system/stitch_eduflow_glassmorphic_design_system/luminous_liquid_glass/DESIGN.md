---
name: Luminous Liquid Glass
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#4a4455'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#7b7487'
  outline-variant: '#ccc3d8'
  surface-tint: '#732ee4'
  primary: '#630ed4'
  on-primary: '#ffffff'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#d2bbff'
  secondary: '#00687a'
  on-secondary: '#ffffff'
  secondary-container: '#57dffe'
  on-secondary-container: '#006172'
  tertiary: '#9b005c'
  on-tertiary: '#ffffff'
  tertiary-container: '#bf2076'
  on-tertiary-container: '#ffdde7'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#acedff'
  secondary-fixed-dim: '#4cd7f6'
  on-secondary-fixed: '#001f26'
  on-secondary-fixed-variant: '#004e5c'
  tertiary-fixed: '#ffd9e4'
  tertiary-fixed-dim: '#ffb0cd'
  on-tertiary-fixed: '#3e0022'
  on-tertiary-fixed-variant: '#8c0053'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 64px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.015em
  title-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 26px
    letterSpacing: -0.01em
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0em
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  gutter-lg: 2rem
  margin: 2rem
  margin-mobile: 1rem
  margin-desktop: 3rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies ethereal, hyper-clean liquid glassmorphism optimized exclusively for light mode. The visual language merges fluid optics, prismatic light refraction, and high-energy saturated accents against luminous, crystalline surfaces. It projects high technology, premium craft, optimism, and uncompromised precision.

The aesthetic avoids heavy or murky dark glass; instead, it relies on multi-layer translucent frost, razor-sharp specular borders, and soft chromatic caustics that make UI surfaces appear suspended in pure ambient daylight. Interaction states are reactive and fluid, utilizing soft iridescent glows, spring transitions, and subtle inner-lens refractions.

## Colors

The palette is engineered around high-chroma spectrum accents interacting with bright neutral glass backdrops.

- **Primary (Electric Violet - `#7C3AED`):** Drives key calls to action, active navigation tabs, and primary focus states.
- **Secondary (Vivid Cyan - `#06B6D4`):** Accents operational metrics, informational pills, and secondary focus indicators.
- **Tertiary (Hot Magenta - `#EC4899`):** Reserved for highlights, critical notifications, dynamic badges, and energetic gradient transitions.
- **Supportive Accents:** Radiant Amber (`#F59E0B`) for warnings/real-time indicators; Crisp Royal Indigo (`#4F46E5`) for deep focal emphasis.
- **Canvas & Neutrals:**
  - Canvas Base: `#F8FAFC` to `#F1F5F9`, accented with ambient underlying mesh gradients (`#E0E7FF` / `#FCE7F3` / `#CFFAFE`).
  - Glass Panes: Solid base translucent white varying from `rgba(255, 255, 255, 0.72)` to `rgba(255, 255, 255, 0.92)`.
  - Obsidian Text: `#0F172A` (Headings/Primary text), `#334155` (Secondary text), `#64748B` (Muted/Tertiary labels).

## Typography

Plus Jakarta Sans provides geometric clarity with crisp modern proportions. The type system prioritizes high-contrast legibility over frosted surfaces:

- **Display & Headline Levels:** Feature tight tracking (`-0.03em` to `-0.015em`) and heavy weights (700/800) to cut through background diffusion. Gradient fills (Electric Violet to Hot Magenta or Cyan) can be applied to `display-hero` and `headline-lg` on major dashboard headers.
- **Body Text:** Uses balanced line heights (`1.5` to `1.625`) in deep obsidian `#0F172A` and slate `#334155` to ensure AAA contrast across semi-transparent glass layers.
- **Labels & Badges:** Use medium to bold weights with uppercase tracking (`+0.02em` to `+0.04em`) for small-scale identification.

## Layout & Spacing

The layout is built on a responsive 12-column fluid grid on desktop, scaling to 8 columns on tablet and 4 columns on mobile. Generous negative space is essential to let the luminous glass surfaces breathe and prevent optical clutter.

- **Desktop (>= 1200px):** 12 columns, `margin-desktop` (3rem), `gutter` (1.5rem) to `gutter-lg` (2rem). Content maxes out at a standard 1440px viewport cap.
- **Tablet (768px - 1199px):** 8 columns, `margin` (2rem), `gutter` (1.5rem). Multi-column glass panels fold into cohesive stacked cards.
- **Mobile (<= 767px):** 4 columns, `margin-mobile` (1rem), `gutter-sm` (1rem). Floating sheets and navigation bars dock to bottom safe-areas with heavy backdrop blur.

## Elevation & Depth

Depth is conveyed through luminous glass tiers, light refraction, and tinted chromatic caustics rather than muddy opaque drops:

1. **Canvas Surface (Level 0):** Crisp pearl foundation (`#F8FAFC`) with soft, dispersed radial underlays of indigo, pink, and cyan.
2. **Glass Base / Flat Cards (Level 1):** 
   - Background: `rgba(255, 255, 255, 0.75)`
   - Backdrop Filter: `blur(16px) saturate(180%)`
   - Border: `1px solid rgba(255, 255, 255, 0.85)`
   - Shadow: `0 8px 32px -4px rgba(99, 102, 241, 0.08), 0 2px 8px -2px rgba(15, 23, 42, 0.04)`
3. **Elevated Glass / Active Cards & Dropdowns (Level 2):** 
   - Background: `rgba(255, 255, 255, 0.85)`
   - Backdrop Filter: `blur(24px) saturate(200%)`
   - Border: Top edge `1px solid rgba(255, 255, 255, 1.0)`, bottom edge `1px solid rgba(255, 255, 255, 0.6)`
   - Shadow: `0 16px 40px -8px rgba(124, 58, 237, 0.14), 0 4px 12px -2px rgba(6, 182, 212, 0.08)`
4. **Modal / Top Sheet Overlay (Level 3):** 
   - Background: `rgba(255, 255, 255, 0.92)`
   - Backdrop Filter: `blur(32px) saturate(210%)`
   - Border: `1px solid rgba(255, 255, 255, 0.95)`
   - Shadow: `0 24px 64px -12px rgba(124, 58, 237, 0.2), 0 8px 24px -4px rgba(236, 72, 153, 0.12)`

## Shapes

The shape hierarchy is completely rounded, smooth, and aerodynamic (`roundedness: 3`). Fully radiused capsules (pills) serve as the primary signature primitive across buttons, tags, search bars, and indicators.

- **Containers & Glass Panels:** Large, organic corner radii (`2rem` / 32px for cards, `2.5rem` / 40px for floating modals).
- **Controls & Micro-elements:** Complete continuous pill roundness (`9999px`) on all buttons, badges, inputs, and toggles.
- **Glass Edge Reflections:** Outlines utilize directional gradient strokes that mimic a physical light source hitting the top-left curve (higher opacity white transitioning to semi-transparent violet/cyan).

## Components

### Buttons
- **Primary Liquid Button:** Continuous pill shape. Vibrant linear gradient background (`linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%)`), text `#FFFFFF`, crisp inset highlight (`inset 0 1px 1px rgba(255, 255, 255, 0.4)`), and a colored shadow (`0 8px 20px -4px rgba(124, 58, 237, 0.4)`). Hover triggers subtle scale (`1.02`) and elevated blur.
- **Secondary Glass Button:** Translucent white fill (`rgba(255, 255, 255, 0.7)`), 1px stroke (`rgba(255, 255, 255, 0.9)`), text `#0F172A`, backdrop blur (12px). Hover adds ambient violet tint (`rgba(124, 58, 237, 0.06)`).

### Chips & Badges
- Pill-shaped status badges. Semi-transparent colored fills (`rgba(6, 182, 212, 0.12)` for Cyan, `rgba(236, 72, 153, 0.12)` for Magenta) with a 1px colored rim (`rgba(6, 182, 212, 0.25)`). Text matches the high-contrast variant of the base accent color. Contains an optional glowing 6px internal status orb.

### Input Fields
- Capsule-shaped text fields with frosted glass fill (`rgba(255, 255, 255, 0.65)`), backdrop blur (16px), and a soft border (`1px solid rgba(255, 255, 255, 0.8)`). 
- Active/Focus: Glow ring (`0 0 0 3px rgba(124, 58, 237, 0.18)`), background shifts to `rgba(255, 255, 255, 0.95)`, border shifts to `#7C3AED`.

### Selection Controls (Checkboxes & Radios)
- **Checkboxes:** Rounded squares (radius 8px) with frosty base; checked state delivers an electric violet-to-cyan gradient with an etched white checkmark.
- **Radios:** Outer glass circle with a concentric vibrant violet floating pip on selection.

### Progress Bars
- High-saturation track in translucent white-tinted glass (`rgba(255, 255, 255, 0.5)` with inset shadow). The indicator is a pill-shaped continuous gradient from Vivid Cyan (`#06B6D4`) to Electric Violet (`#7C3AED`) to Hot Magenta (`#EC4899`), finished with a luminous leading edge shine.

### Multi-layer Cards
- Structured with layered glass panes: base card holds lower blur and high transparency, while nested internal metric blocks leverage higher opacity (`rgba(255, 255, 255, 0.85)`), higher blur, and distinct 1px specular white borders to establish clear depth segmentation.