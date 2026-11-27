# RuangKampus — Modern Academic Operations

## Design intent

The interface supports two related jobs: students finding and booking campus spaces, and staff operating the room and reservation inventory. The visual language is calm, institutional, and information first. Blue carries the RuangKampus identity and primary actions; teal is a restrained supporting accent. Neutral surfaces, clear dividers, and typography establish hierarchy without turning every region into a floating card.

The official RuangKampus logo and its proportions remain unchanged. The supplied transparent wordmark has blue artwork and a dark navy name/tagline; the other supplied wordmark includes a white background. There is no transparent white-on-dark wordmark in the asset set. The wordmark is therefore placed directly on a flat, pale brand panel integrated into the login brand area and desktop sidebar. Its source colors and file are not filtered or edited. The mobile top bar uses the official favicon mark at a small scale. Favicon files and manifest continue to use the supplied official mark. The desktop application keeps its persistent role navigation and the mobile application keeps the existing mobile navigation and route ordering. Existing field labels, status labels, actions, routes, and page content remain as supplied by the application.

## Color tokens

Use semantic variables from `frontend/src/styles/tokens.css`, not page-specific hex values.

| Role | Light | Dark | Use |
|---|---|---|---|
| Brand primary | `#005A9C` | `#77B8E5` | Links, active navigation, information state |
| Primary action | `#005A9C` | `#145C8D` | Main buttons and high-priority actions |
| Supporting teal | `#2F7F78` | `#68B8A8` | Limited supporting emphasis |
| Page background | `#F3F4F1` | `#0D1219` | Main application canvas |
| Navigation | `#FBFCFA` | `#101923` | Sidebar, top bar, mobile navigation |
| Surface | `#FFFFFF` | `#161F2A` | Forms, panels, cards, dialogs |
| Elevated surface | `#FFFFFF` | `#202B38` | Popovers and elevated controls |
| Primary text | `#172B3F` | `#F2F5F8` | Headings and essential content |
| Secondary text | `#536A80` | `#B8C4CF` | Body copy and supporting labels |
| Border | `#DCE2E5` | `#2B3948` | Dividers and control boundaries |
| Success | `#176B4B` | `#75C9A2` | Confirmed and completed state |
| Warning | `#805000` | `#FFD17A` | Pending and attention state |
| Error | `#A51F32` | `#FF929E` | Failure, rejection, destructive state |

Use status color only for its status. Keep a text label or icon with status color; color alone must not carry the meaning. The theme is selected through the existing `data-theme` attribute and the current `rk-theme` persistence mechanism.

## Typography

Use the locally bundled **Plus Jakarta Sans Variable** family for all application text. It is imported from `@fontsource-variable/plus-jakarta-sans` in `frontend/src/main.tsx`, with a platform sans fallback chain defined by `--font-family-sans`. Its 200–800 variable weights allow one family to support interface captions through headings. Use the system monospace stack only for identifiers and time values. Headings use restrained negative tracking and a compact line height; body text uses a 1.55 line height. Keep page headings in the 26–34px range, section headings near 18px, body text at 14px, and labels/metadata at 10–12px. Numeric summaries use tabular figures where supported.

## Layout and spacing

- Keep the desktop sidebar fixed at 260px, with a 226px compact desktop treatment before the mobile breakpoint.
- Use a 1500px maximum page width and responsive 22–42px desktop gutters.
- Follow the 4px base spacing rhythm. Use 8–16px for control groups, 21–26px for page sections, and 32px for the main content inset on wide screens.
- The content canvas is a quiet warm neutral. Use white surfaces and 1px borders for structure; reserve shadows for menus, dialogs, and the mobile navigation.
- Let tables scroll inside their existing wrappers on narrow viewports. Reflow grids and forms while retaining all controls and information.

## Shape, borders, and elevation

Use 7–8px for controls, 9–12px for cards and panels, and 14px for larger contained areas. Avoid pill buttons and large decorative shadows. Standard panels use a clear border with no shadow. The popover shadow is reserved for overlays; mobile navigation uses a modest shadow to separate it from scrolling content.

## Icons

Use the official `@tabler/icons-react` package as the single UI icon family. Import named `Icon…` components directly for tree shaking, and use the outline style with a consistent 2px stroke. Keep inline icons near 16px, common navigation and button icons at 18–20px, and feature icons at 22–24px. Icons stay proportional to their labels. Hide decorative icons from assistive technology when adjacent text already names the action; icon-only controls keep an accessible name. Do not use emoji or substitute brand marks.

## Components and page composition

- **Navigation:** quiet institutional surfaces, a narrow active route marker, consistent icon alignment, and the existing account and theme controls.
- **Buttons and forms:** square-cornered controls, clear primary/secondary hierarchy, visible focus rings, labelled inputs, and unchanged disabled/loading states.
- **Tables:** subtle header surfaces, readable row dividers, tabular alignment where appropriate, and contained horizontal scrolling when necessary.
- **Status and notices:** semantic token pairs with readable labels; statuses use compact rectangular badges.
- **Dashboards:** retain their data and actions. Use typography and spacing to distinguish summary, monitoring, recent activity, and shortcuts rather than adding decorative card treatments.
- **Room and reservation pages:** keep existing details and workflow, with clear section hierarchy and restrained surface separation.
- **RUKKA AI:** preserve the conversation, suggestions, feedback, and result interactions; distinguish user and assistant messages with spacing, alignment, and quiet surface changes.
- **Authentication:** retain the official brand assets and all existing forms. Keep the split brand/form composition on large screens and stack it on smaller screens.

## Responsive behavior

The shared stylesheet includes desktop, tablet, and compact mobile rules. At 920px and below, the desktop sidebar gives way to the existing mobile navigation. The mobile shell reserves a dedicated bottom grid row for navigation while the main content scrolls in its own area, so persistent navigation does not cover form controls or page content. The mobile header uses the official mark-only favicon; the desktop sidebar retains the full wordmark. At 700px, content gutters shrink, multi-column forms reflow, and request/room grids become two columns; at 420px they become one column. Table wrappers preserve all columns through horizontal scrolling. Dialogs remain constrained to the viewport. Mobile navigation accounts for the device safe-area inset.

## Accessibility and interaction

- Keep semantic HTML, existing accessible labels, keyboard behavior, and workflow state untouched.
- Preserve a visible `:focus-visible` ring in both themes.
- Use 40–46px controls for high-frequency touch targets; keep icon buttons at 40px or larger.
- Maintain text contrast by pairing dark primary text with light surfaces and light text with dark surfaces. Validate final rendered pairs with the existing axe browser suite.
- Use 120–180ms state transitions. Honor `prefers-reduced-motion` by suppressing animation and smooth scrolling.
- Keep status meaning readable without color and retain existing loading, error, success, empty, and disabled treatments.

## Implementation boundaries

Tokens live in `frontend/src/styles/tokens.css`; component and responsive rules live in `frontend/src/styles.css`. Typography package CSS is imported by `frontend/src/main.tsx`; UI icons come only from `@tabler/icons-react`. Official image assets remain in `frontend/public/brand/`. Route definitions, API behavior, authentication, reservation rules, form fields and submission logic, notification behavior, chatbot state, and theme persistence are not design-system concerns and must remain unchanged during visual work.
