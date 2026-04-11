# Design System Strategy: The Kinetic Terminal

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Kinetic Terminal."** 

Unlike standard dashboards that mimic consumer web apps, this system is designed to feel like a high-performance mission control interface. It moves beyond the "template" look by embracing a high-contrast, technical aesthetic that prioritizes data density and editorial precision. By utilizing sharp `0px` radii and a monochrome-heavy foundation punctuated by vibrant "hazard" yellow and "systemic" blue, we create a workspace that feels authoritative, intentional, and engineered rather than merely "designed."

The layout breaks traditional rigidity through **Intentional Asymmetry**: using wide gutters for logs while keeping command inputs tight and centered. This creates a visual rhythm that guides the operator's eye from high-level telemetry to granular code execution.

---

## 2. Colors: Tonal Depth & The "No-Line" Rule
The color palette is built on deep, obsidian tones. The goal is to create depth through light, not through borders.

### Surface Hierarchy
*   **Background (`#0a0a0c`):** The absolute floor. Used for the primary canvas.
*   **Surface-Container-Low (`#131315`):** Used for sidebar backgrounds and secondary navigation panels.
*   **Surface-Container-High (`#1f1f22`):** Used for active terminal windows and code blocks.
*   **Primary (`#f5d547`):** Use sparingly for critical actions (e.g., `INITIALIZE SEQUENCE`) and active state indicators.
*   **Secondary (`#2563eb`):** Reserved for technical data streams, links, and "safe" system confirmations.

### The "No-Line" Rule
Prohibit the use of 1px solid borders for sectioning. Boundaries must be defined by shifts in background tokens. For example, a `surface-container-high` code block should sit directly on a `surface` background. The change in luminance is the boundary.

### The Glass & Gradient Rule
To provide a premium feel, floating overlays (like command palettes) must use **Glassmorphism**:
*   **Color:** `surface_variant` at 60% opacity.
*   **Effect:** `backdrop-blur: 20px`.
*   **Signature Texture:** Use a subtle linear gradient on primary CTAs (`primary` to `primary_container`) to simulate a backlit physical button.

---

## 3. Typography: Technical Authority
We use a dual-font strategy to balance readability with a "hacker" aesthetic.

*   **Display & Headline (Space Grotesk):** Provides a clean, modern editorial feel for titles and high-level stats.
*   **Monospace Engine (JetBrains Mono Semi Bold):** Used for all "living" data. This includes the chat history sidebar, logs, code blocks, and input fields.
*   **Hierarchy as Brand:** Use `label-sm` in all-caps with `letter-spacing: 0.1em` for metadata (e.g., "RECENT INTERVALS"). This conveys a sense of rigorous categorization.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are forbidden. We achieve lift through the **Layering Principle**.

*   **The Layering Principle:** Place a `surface-container-lowest` (`#000000`) element inside a `surface-container-low` container to create a "recessed" well for logs. Place a `surface-container-highest` element on the `background` to create a "raised" console.
*   **Ambient Shadows:** For floating modals, use a shadow with a 40px blur, 0% spread, and a color of `secondary` at 4% opacity. This creates a subtle blue "glow" rather than a grey shadow, simulating the light bleed of a high-end monitor.
*   **Ghost Borders:** If accessibility requires a stroke, use `outline-variant` at 15% opacity. It should be felt, not seen.

---

## 5. Components: Engineered Primitives

### Buttons
*   **Primary:** Sharp `0px` corners. Background: `primary`. Text: `on_primary`. On hover, apply a `primary_dim` outer glow.
*   **Secondary (Action):** Background: `secondary_container`. Text: `on_secondary_container`. 
*   **Tertiary (Ghost):** No background. `outline-variant` ghost border (15% opacity). Text: `on_surface_variant`.

### Input Fields
*   **Technical Command Input:** `surface-container-highest` background, `0px` radius. Use `JetBrains Mono` for the caret and typed text. The focus state should not be a border change, but a subtle `primary` glow on the bottom edge (2px).

### Terminal Logs
*   **Style:** No dividers. Use `body-sm` typography. 
*   **Status Indicators:** Use `tertiary` (green) for success, `error` (red) for failures, and `secondary` (blue) for system pings.

### Sidebar Lists
*   **State:** The active "chat" or "thread" should be indicated by a `primary` vertical 2px line on the far left and a subtle `surface-bright` background shift. No rounded highlights.

---

## 6. Do's and Don'ts

### Do
*   **DO** use strict `0px` rounding for all containers. 
*   **DO** use uppercase `label-sm` for all non-interactive headers to maintain the "Technical Manual" feel.
*   **DO** leverage `surface-container` tiers to group related data.
*   **DO** use the `secondary` blue to highlight "safe" data (e.g., file names, IDs).

### Don't
*   **DON'T** use 100% opaque borders to separate panels; let the color shifts do the work.
*   **DON'T** use standard sans-serif fonts for data or logs—always use `JetBrains Mono`.
*   **DON'T** use soft, "bubbly" UI patterns. If a component feels "friendly," it is wrong for this system.
*   **DON'T** use pure grey shadows. Always tint shadows with the `secondary` or `on_surface` color for organic depth.