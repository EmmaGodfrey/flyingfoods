# Icon Scale Rules

This file is the single shared icon sizing rule sheet for all UI in this repository.

## Required Scale

- Topbar icons: 18px
- Navigation icons: 16px
- Meta/action icons: 14px

## Stroke

- Use outlined icons with stroke width around 1.8 where configurable.

## Library

- Default library: Lucide.

## HTML Usage

Use semantic classes:

- `.icon-topbar`
- `.icon-nav`
- `.icon-meta`

Use CSS variables where possible:

```css
--icon-topbar: 18px;
--icon-nav: 16px;
--icon-meta: 14px;
```

## React Usage

Use centralized constants:

```ts
const ICON = {
  topbar: 18,
  nav: 16,
  meta: 14,
} as const;
```

Never use arbitrary one-off icon sizes in production UI unless explicitly required.
