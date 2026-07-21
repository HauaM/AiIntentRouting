# AiIntentRouting Project Instructions

These instructions apply to this repository and override generic frontend
defaults when they are more specific.

## Admin Console Viewport Scope

The AiIntentRouting Admin Console is a desktop web operations console optimized
for FHD usage. Do not design, implement, or verify mobile-specific UX unless the
user explicitly asks for it.

Still preserve layout robustness when a desktop browser window is narrowed:

- prevent clipping, unreadable text, broken toolbars, and modal/drawer overflow;
- use table overflow, ellipsis, wrapping, and viewport constraints where needed;
- treat narrow desktop windows as a web layout resilience requirement, not as a
  mobile product requirement.

Do not add mobile-only navigation, card-list replacements for tables,
touch-first interaction patterns, or phone-viewport acceptance criteria by
default.
