# PEACOCK ENGINE WebUI - Design System
> **Version**: 1.0.0 | **Date**: 2026-04-05 | **Status**: Production Ready

---

## 1. Design Philosophy

**Creative North Star: "The Precision Engine"**

PEACOCK ENGINE's WebUI is built for operators who demand clarity under pressure. This design system merges the **data density of financial terminals** with the **visual sophistication of modern cyberpunk interfaces**.

Unlike generic SaaS dashboards, we embrace:
- **Intentional density** - Information-rich layouts that reward attention
- **Zero-radius geometry** - Sharp edges that feel machined, not molded
- **Tonal hierarchy** - Depth through color shifts, not drop shadows
- **Functional beauty** - Every pixel serves the operator's workflow

The result is a **Digital Cockpit** - a command center for AI orchestration that feels both powerful and precise.

---

## 2. Color System

### Core Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `background` | `#101418` | Application canvas |
| `surface` | `#101418` | Primary work areas |
| `surface-container-low` | `#181c20` | Navigation, sidebars |
| `surface-container` | `#1c2024` | Cards, panels |
| `surface-container-high` | `#262a2f` | Active states, hover |
| `surface-container-highest` | `#31353a` | Elevated elements |
| `primary` | `#aac7ff` | Primary actions, links |
| `primary-container` | `#0066cc` | Buttons, accents |
| `secondary-container` | `#ffdb3c` | Gold highlights, CTAs |
| `tertiary` | `#7ad0ff` | Ice blue for frozen states |
| `error` | `#ffb4ab` | Errors, critical alerts |
| `outline` | `#8b919e` | Subtle borders |
| `outline-variant` | `#414753` | Ghost borders |

### Status Colors

| Status | Color | Usage |
|--------|-------|-------|
| Active | `#00C851` (Green) | Online models, healthy keys |
| Frozen | `#00BFFF` (Ice Blue) | Disabled models, cooldown |
| Warning | `#ffdb3c` (Gold) | Alerts, quotas |
| Error | `#ffb4ab` (Red) | Failures, billing issues |

### Surface Logic

**The "No Border" Rule:** Separation is achieved through **chromatic shifts**, not 1px borders. Use surface container tiers to create depth:
- Place `surface-container` on `surface` for subtle elevation
- Place `surface-container-high` on `surface-container` for active focus
- Use `outline-variant` at 10% opacity only when absolutely necessary

---

## 3. Typography

### Font Stack

| Role | Font | Weight Range |
|------|------|--------------|
| Headlines | Space Grotesk | 400-500 (light, elegant) |
| Body | Inter | 400-500 (readable, neutral) |
| Labels | Space Grotesk | 500 (medium weight) |
| Mono | JetBrains Mono | 400-500 (data, logs) |

### Type Scale

| Element | Size | Weight | Tracking | Transform |
|---------|------|--------|----------|-----------|
| Page Title | 30px | 500 | -0.02em | none |
| Section Header | 18px | 500 | -0.01em | none |
| Card Title | 16px | 500 | 0 | none |
| Body | 14px | 400 | 0 | none |
| Label | 12px | 500 | 0.05em | UPPERCASE |
| Mono Data | 14px | 400 | 0 | none |
| Mono Small | 10-11px | 400 | 0.02em | UPPERCASE |
| Caption | 10px | 400 | 0.02em | UPPERCASE |

### Typography Principles

1. **Headlines use medium weight** - Not bold. Lighter weights feel more refined.
2. **Labels are always uppercase** - Creates clear hierarchy for metadata.
3. **Monospace for all data** - RPM, TPM, pricing, timestamps, logs.
4. **Tracking is tight** - -0.02em for headlines creates compact, intentional feel.

---

## 4. Layout Structure

### Three-Panel Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  TopNav (16px height)                                       │
├──────────┬──────────────────────────────┬───────────────────┤
│          │                              │                   │
│ SideNav  │      Main Content            │  Details Panel    │
│ (256px)  │      (flexible)              │  (384px)          │
│          │                              │                   │
├──────────┴──────────────────────────────┴───────────────────┤
│  Status Bar (32px height)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Panel Specifications

| Panel | Width | Background | Purpose |
|-------|-------|------------|---------|
| TopNav | 100% | surface-container-low | Global nav, user actions |
| SideNav | 256px | surface-container-low | Section navigation |
| Main Content | flexible | surface | Primary data display |
| Details Panel | 384px | surface-container-low | Contextual actions |
| Status Bar | 100% | surface-container-lowest | System status |

### Spacing System

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight gaps, icon padding |
| `space-2` | 8px | Inline spacing |
| `space-3` | 12px | Button padding |
| `space-4` | 16px | Card padding, section gaps |
| `space-6` | 24px | Major section separation |
| `space-8` | 32px | Page-level padding |

---

## 5. Components

### Buttons

**Primary Button**
- Background: Gradient from `primary` to `primary-container`
- Text: `on-primary`
- Padding: 12px 24px
- Font: 12px, font-semibold, uppercase, tracking-wider
- Border-radius: 0px
- Hover: brightness(110%), active: scale(0.95)

**Secondary Button**
- Background: `surface-container-highest`
- Border: 1px `outline-variant`
- Text: `on-surface`
- Hover: background shifts to `primary`, text to `on-primary`

**Gold/Action Button**
- Background: `secondary-container`
- Text: `on-secondary-container`
- Use for: Test, Deploy, Critical actions
- Add `gold-glow` filter on hover

### Cards

**Model Card (Table Row)**
- Background: transparent (inherits container)
- Hover: `surface-container-high`
- Left accent: 4px vertical bar in status color
- Padding: 20px 24px
- No border-bottom - use divide-y at 10% opacity

**Key Card**
- Background: `surface-container`
- Border-left: 2px accent on hover
- Padding: 20px
- Status badge: pill shape with dot indicator

### Status Badges

**Active Badge**
```
BG: status-active/10
Border: status-active/20
Text: status-active
Dot: status-active (no pulse)
Font: 10px mono uppercase semibold
```

**Frozen Badge**
```
BG: status-frozen/10
Border: status-frozen/20
Text: status-frozen
No dot
Font: 10px mono uppercase semibold
```

### Data Table

- Header: `surface-container` background
- Header text: 12px uppercase, slate-500, medium weight
- Row hover: `surface-container-high`
- Cell padding: 20px 24px
- No vertical borders
- Horizontal dividers: `outline-variant/10`

### Form Elements

**Text Input**
- Background: transparent
- Border-bottom: 1px `outline-variant/30`
- Focus: border shifts to `primary`
- Font: Monospace for API keys, Inter for text

**Toggle Switch**
- Track: `surface-container-highest`
- Thumb: status color
- Active track: status color at 20% opacity

---

## 6. Screen-Specific Patterns

### Model Registry Screen

**Layout:**
- Main: Data table with model rows
- Right Panel: Selected model details + actions

**Key Elements:**
- Model name + provider badge
- Status indicator (Active/Frozen/Deprecated)
- Context window size (mono)
- Rate limits RPM/TPM (mono)
- Pricing in/out per 1k tokens (mono)
- Actions: Test (gold), Freeze, Set Default

**API Integration:**
```
GET /v1/webui/models/registry - List all models
POST /v1/webui/models/{id}/test - Test model
POST /v1/webui/models/{id}/freeze - Freeze model
POST /v1/webui/models/{id}/unfreeze - Unfreeze model
POST /v1/webui/models/{id}/default - Set default
```

### Key Management Screen

**Layout:**
- Main: Grid of key cards by gateway
- Top metrics: Total keys, healthy count, cost estimate

**Key Elements:**
- Gateway icon + name
- Masked key (first 8 + last 4)
- Usage percentage bar
- Status: Active/Standby/Error
- Quick actions: Test, Toggle, Delete

**API Integration:**
```
GET /v1/webui/keys/ - List all keys
GET /v1/webui/keys/telemetry - Key metrics
POST /v1/webui/keys/{gw}/{label}/test - Test key
POST /v1/webui/keys/{gw}/{label}/toggle - Enable/disable
DELETE /v1/webui/keys/{gw}/{label} - Remove key
```

### Chat Interface Screen

**Layout:**
- Main: Message thread with input
- Left: Conversation list

**Key Elements:**
- Message bubbles with role indicators
- File attachments with preview
- Streaming indicator (pulsing dot)
- Model selector dropdown
- Token count + cost estimate

**API Integration:**
```
GET /v1/webui/chat/conversations - List conversations
POST /v1/webui/chat/conversations - Create conversation
POST /v1/webui/chat/stream - Send message (SSE)
POST /v1/webui/chat/upload - Upload file
```

---

## 7. Animation & Micro-interactions

### Hover States
- Buttons: brightness(110%) + subtle scale
- Cards: background shift + left border accent
- Table rows: background to `surface-container-high`
- Duration: 150ms ease-out

### Loading States
- Pulsing dot: `animate-pulse` on status indicators
- Skeleton: Shimmer effect on `surface-container-high`
- Streaming: Pulsing cursor in message input

### Transitions
- Panel slide: 200ms ease-in-out
- Modal fade: backdrop blur + opacity
- Toast slide: 300ms cubic-bezier

---

## 8. Responsive Behavior

### Breakpoints

| Breakpoint | Width | Behavior |
|------------|-------|----------|
| Desktop | 1440px+ | Full three-panel layout |
| Laptop | 1024px | Collapsible details panel |
| Tablet | 768px | Hide side nav, show hamburger |
| Mobile | <768px | Single column, stacked panels |

### Mobile Adaptations
- SideNav becomes slide-out drawer
- Details Panel becomes bottom sheet
- Data table becomes card list
- Status bar becomes collapsible

---

## 9. Do's and Don'ts

### Do:
- Use 0px border-radius consistently
- Embrace data density - operators want information
- Use monospace for all numerical data
- Apply the gold color (`secondary-container`) sparingly for high-value actions
- Use chromatic separation instead of borders
- Keep headlines at font-weight 500 (medium), not bold

### Don't:
- Use rounded corners - it breaks the machined aesthetic
- Use 100% opaque borders - they feel cluttered
- Use generic "bootstrap blue" - stick to `primary` (#aac7ff)
- Use dividers between list items - use spacing instead
- Use font-weight 700+ for headlines - lighter is more refined
- Forget the status bar - it's essential for operator awareness

---

## 10. Implementation Notes

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#101418',
        surface: {
          DEFAULT: '#101418',
          dim: '#101418',
          bright: '#353a3e',
          container: {
            lowest: '#0a0f13',
            low: '#181c20',
            DEFAULT: '#1c2024',
            high: '#262a2f',
            highest: '#31353a',
          }
        },
        primary: {
          DEFAULT: '#aac7ff',
          container: '#0066cc',
          fixed: '#d7e3ff',
        },
        secondary: {
          container: '#ffdb3c',
          fixed: '#ffe16d',
        },
        status: {
          active: '#00C851',
          frozen: '#00BFFF',
          warning: '#ffdb3c',
        }
      },
      fontFamily: {
        headline: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '0px',
        lg: '0px',
        xl: '0px',
      }
    }
  }
}
```

### CSS Custom Properties

```css
:root {
  --gold-glow: drop-shadow(0 0 8px rgba(255, 219, 60, 0.27));
  --cyber-glow: drop-shadow(0 0 8px rgba(170, 199, 255, 0.2));
  --ghost-border: 1px solid rgba(65, 71, 83, 0.1);
}
```

---

## 11. Director's Final Note

This design system serves a single purpose: **empower the operator**. Every decision - from the 0px corners to the monospace data fields - reinforces that PEACOCK ENGINE is a precision tool, not a casual app.

When in doubt:
1. Add more data, not less
2. Use lighter font weights, not heavier
3. Prefer color shifts over borders
4. Default to sharp, not soft

We are not building a website. We are building the cockpit for AI orchestration.

---

**END OF DESIGN SYSTEM**
