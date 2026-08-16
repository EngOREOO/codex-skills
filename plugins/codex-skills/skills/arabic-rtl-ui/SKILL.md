---
name: arabic-rtl-ui
description: Enforce RTL-first behavior when building, editing, reviewing, or fixing Arabic and Arabic-English user interfaces. Use whenever visible UI content is Arabic or mixes Arabic and English, or when the user asks for RTL, bidi, localization, Arabization, or Arabic layout support.
---

# Arabic RTL UI

Apply these rules to every interface task whose visible content contains Arabic, even when English is also present. Do not wait for the user to repeat the RTL requirement.

## Direction policy

- If the interface contains Arabic, set the page or application shell to RTL.
- When replying in a chat host, use plain Arabic-first Markdown and do not emit raw HTML as a direction workaround unless the host is known to render it. A skill can guide generated content, but it cannot change the host application's message-container CSS.
- Arabic-only content is RTL.
- Mixed Arabic-English content is also RTL at the page and component-layout level.
- Use LTR only for isolated content that must preserve left-to-right reading: email addresses, URLs, code, file paths, version strings, serial numbers, and explicitly English-only text fields.
- Prefer `dir="auto"` for unpredictable user-generated text inside an RTL shell.
- Set the document language correctly: use `lang="ar"` for Arabic-first pages and a suitable regional tag such as `ar-SA` when the product specifies one.

## Implementation rules

1. Put direction at the highest stable root instead of patching each child:

```html
<html lang="ar" dir="rtl">
```

2. Use CSS logical properties so components adapt safely:

```css
.card {
  margin-inline-start: 1rem;
  padding-inline: 1rem;
  border-inline-start: 3px solid currentColor;
  text-align: start;
}
```

Prefer `inline-start`, `inline-end`, `block-start`, `block-end`, and `text-align: start/end`. Avoid new directional declarations such as `margin-left`, `padding-right`, `left`, or `right` unless the element is intentionally physical rather than linguistic.

3. Mirror directional UI meaning, including navigation arrows, chevrons, breadcrumbs, drawers, steppers, and previous/next controls. Do not mirror universal symbols, media controls, clocks, logos, checkmarks, or brand artwork.

4. Keep numbers readable in context. Do not reverse phone numbers, dates, prices, IDs, or verification codes. Wrap unstable mixed-direction values when necessary:

```html
<bdi dir="ltr">support@example.com</bdi>
```

5. Align form labels, validation, tables, menus, modals, notifications, pagination, and empty states with the RTL flow. Keep technical inputs LTR while their labels and surrounding layout remain RTL.

6. Use an Arabic-capable font stack and verify that Arabic glyphs, diacritics, line height, and font weight render correctly. Never rely on letter spacing for Arabic text.

7. For frameworks, use their native root-direction mechanism when available, but keep the same policy:
   - React/Next/Vue/Svelte: set `dir` and `lang` on the document or app shell.
   - Tailwind: prefer logical utilities or the project's established RTL plugin; avoid duplicate RTL-only markup.
   - Flutter: set an Arabic locale and ensure `Directionality(textDirection: TextDirection.rtl)` at the app shell when localization does not provide it automatically. Use `EdgeInsetsDirectional` and `AlignmentDirectional`.
   - Native mobile: use leading/trailing constraints rather than left/right constraints.

## Review checklist

Before finishing, verify:

- The highest stable root is RTL and declares an Arabic language.
- In chat hosts, verify whether message-container RTL is supported by the application itself; do not claim the skill can reposition host UI that it does not control.
- Mixed Arabic-English pages remain RTL overall.
- English/code/URL islands render LTR without changing surrounding layout.
- Spacing and positioning use logical properties.
- Directional icons are mirrored and non-directional icons are not.
- Keyboard focus order and screen-reader reading order follow the DOM, not visual CSS tricks.
- Horizontal overflow does not appear at common mobile widths.
- Contrast meets WCAG AA and focus indicators remain visible.
- Existing project conventions and localization architecture are preserved.

When reviewing existing code, report concrete RTL defects with file and line references. When asked to implement or fix the UI, make the changes and verify them rather than only describing them.
