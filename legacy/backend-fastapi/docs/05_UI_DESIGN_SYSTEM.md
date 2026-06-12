# UI Design System - Minimalist Blue and White

Use this as the required visual baseline for all current and future UI work in this repository.

## 1. Brand Direction

Every interface should feel:
- Modern
- Minimal
- Intelligent
- Premium
- Slightly futuristic
- Clean and trustworthy

Design principles:
- Prioritize whitespace and clear hierarchy.
- Keep surfaces clean with light shadows and subtle borders.
- Use smooth, restrained motion.
- Avoid visual clutter.

## 2. Core Palette

### Primary
- Primary blue: #2563EB
- Deep blue (hover/active): #1D4ED8
- White (main background): #FFFFFF
- Light gray (secondary background): #F5F7FA
- Dark text: #111827
- Gray text: #6B7280

### Accent (use sparingly)
- Success: #10B981
- Warning: #F59E0B
- Error: #EF4444

## 3. Typography

Preferred font stack:
- Inter
- SF Pro Display (fallback option)
- Manrope (fallback option)
- Montserrat (fallback option)

Type scale:
- Hero title: 48px / 700
- Page title: 36px / 600
- Section title: 28px / 600
- Card title: 20px / 500
- Body text: 16px / 400
- Small text: 14px / 400

## 4. Spacing System

Use only the spacing tokens below:
- XS: 4px
- SM: 8px
- MD: 16px
- LG: 24px
- XL: 32px
- XXL: 48px

No random spacing values in production UI.

## 5. Components

### Buttons
Primary button:
- Background: #2563EB
- Text: white
- Radius: 10px
- Padding: 12px 24px
- Hover: #1D4ED8 with slight lift

Secondary button:
- Background: white
- Border: 1px solid #2563EB
- Text: #2563EB

### Cards
- Radius: 16px
- Border: subtle neutral border
- Shadow: 0 4px 20px rgba(0,0,0,0.05)
- Keep generous inner spacing

### Top Navigation
- Thin floating bar
- Background: rgba(255,255,255,0.8)
- Backdrop blur: 10px
- Logo on left, nav center/right, profile far right

## 6. Motion Rules

Allowed:
- Fade in
- Soft hover transitions
- Slide-up card entrances
- Mild glow on active controls

Avoid:
- Flashy motion
- Bouncy animations
- Excessive transition chaining

## 7. Icon Style

Use only simple outlined icon sets with thin strokes:
- Lucide (default)
- Heroicons
- Phosphor

Icon sizes must follow [ui/ICON_SCALE.md](ui/ICON_SCALE.md).

## 8. Layout Pattern

Default dashboard layout:
1. Top navbar
2. Left sidebar
3. Main content (cards, charts, tables, analytics)

## 9. Background Treatment

Use mostly white backgrounds with soft blue-tinted gradients, for example:

```css
background: linear-gradient(to bottom right, #FFFFFF, #F5F9FF);
```

## 10. Futuristic Touch (Optional)

Optional details are allowed only if subtle:
- Soft blue glow
- Mild glassmorphism
- Animated gradient borders
- Neon-blue highlights (low intensity)

Professional first, futuristic second.

## 11. Tech Stack Guidance

Web:
- React
- Tailwind CSS
- Framer Motion

Flutter:
- Material 3
- Custom ThemeData
- Google Fonts package

## 12. Required Compliance Checklist

Before merging any UI change, verify:
1. Palette matches this document.
2. Typography and spacing tokens are respected.
3. Components use minimal borders/effects.
4. Motion is subtle and purposeful.
5. No cluttered or overly decorative layouts.
6. Dashboard pages follow navbar + sidebar + content structure.

## 13. Golden Rule

Minimalism done properly looks expensive.
Favor fewer colors, fewer borders, fewer effects, more spacing, and stronger hierarchy.
