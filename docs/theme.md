# Daz 3D desktop theme

`src/daz_resolver/theme.py` owns semantic color tokens, the complete Qt stylesheet and the
application palette. `apply_theme()` applies them at application scope; reusable controls in
`ui_widgets.py` inherit them. Dialogs explicitly use the same palette/style so an operating-system
dark palette cannot combine a dark background with the app's dark foreground.

| Role | Token | Use |
|---|---|---|
| Main background | canvas | Pages and scroll viewports |
| Surface | surface | Cards, tables, inputs and dialogs |
| Body text | text | Text on light surfaces |
| Supporting text | muted | Descriptions and secondary labels |
| Sidebar | sidebar / sidebar_text | Dark navigation with light text |
| Primary action | accent / on_accent | Install and continue actions |
| Notice states | success, warning, error and matching text tokens | Explanatory banners |
| Scroll controls | scroll_track, scroll_handle, scroll_hover | Both scrollbar orientations |
| Step states | step_done, step_attention | Completed and attention states |

Use semantic object names (`card`, `title`, `muted`, `primary`, `notice`, `step`), not local color
overrides. All top-level dialogs, popup menus, dropdowns, disabled controls, item views and scrollbars
must be covered by the shared theme. Keep text readable in active/inactive host color modes.
Changes need synthetic screenshots of setup, populated review, attention, details and quick guide.

Lists/tables use pixel scrolling and fixed row heights. Page scrolling uses a fixed wheel distance;
large attention lists are paged at 100 items. Technical details use a bounded no-wrap plain-text
summary. Full JSON export runs off the UI thread; never serialize full file inventories during paint,
layout, scrolling or disclosure-toggle handlers.

The sidebar distinguishes Not done, In progress, Needs attention, Ready to install and Done.
Changing inputs invalidates the review. “Done” for a check-only review means the preview completed,
not that products were installed. Human-facing tool branding is **Daz 3D Product Resolver** and the
repository/package/CLI identifier stays `daz-3d-product-resolver`.
