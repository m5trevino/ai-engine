# PEACOCK ENGINE - Component Library

Standardized HTML components for all WebUI screens.

## Files

| File | Purpose |
|------|---------|
| `shared-styles.css` | Global CSS utilities, buttons, cards, form elements |
| `TopNav.html` | Header navigation component |
| `SideNav.html` | Sidebar navigation component |
| `StatusBar.html` | Footer status bar component |
| `MasterLayout.html` | Complete layout template showing all components together |

## Usage

Include the shared styles in your HTML head:

```html
<link rel="stylesheet" href="components/shared-styles.css">
```

Then copy/paste the component HTML into your page structure.

## Standard Layout Structure

```html
<body class="bg-[#101418] text-[#e0e3e8] h-screen overflow-hidden flex flex-col">
    <!-- TopNav (64px height) -->
    <header>...</header>
    
    <!-- Main Content Area -->
    <main class="flex flex-1 pt-16 overflow-hidden">
        <!-- SideNav (256px width) -->
        <aside>...</aside>
        
        <!-- Content (flexible) -->
        <section class="flex-1 overflow-y-auto">
            <!-- Your screen-specific content -->
        </section>
        
        <!-- Optional: Details Panel (384px width) -->
        <aside class="w-96">...</aside>
    </main>
    
    <!-- StatusBar (32px height) -->
    <footer>...</footer>
</body>
```

## Design Tokens

### Colors
- Background: `#101418`
- Surface: `#101418`
- Surface Container Low: `#181c20`
- Surface Container: `#1c2024`
- Surface Container High: `#262a2f`
- Primary: `#aac7ff`
- Primary Container: `#0066cc`
- Secondary/Gold: `#ffdb3c`

### Typography
- Headlines: Space Grotesk, weight 500, tracking -0.02em
- Body: Inter, weight 400
- Mono: JetBrains Mono, weight 400
- Labels: Space Grotesk, uppercase, tracking 0.05em

### Spacing
- Section padding: 32px (p-8)
- Card padding: 20px (p-5)
- Component gaps: 16px (gap-4)
- Small gaps: 8px (gap-2)

### Border Radius
- Default: 0px (sharp corners)
- Full: 9999px (pills/dots only)

## Button Classes

```html
<!-- Primary -->
<button class="btn-primary">Deploy</button>

<!-- Secondary -->
<button class="btn-secondary">Cancel</button>

<!-- Gold/Action -->
<button class="btn-gold">Test Model</button>

<!-- Ghost -->
<button class="btn-ghost">Config</button>
```

## Badge Classes

```html
<span class="badge active">Active</span>
<span class="badge frozen">Frozen</span>
<span class="badge warning">Warning</span>
<span class="badge error">Error</span>
<span class="badge default">Default</span>
```

## Status Dots

```html
<div class="status-dot active"></div>
<div class="status-dot frozen"></div>
<div class="status-dot warning"></div>
<div class="status-dot error"></div>
```

## Card Classes

```html
<!-- Standard Card -->
<div class="card">...</div>

<!-- Active Card (with left border) -->
<div class="card active">...</div>

<!-- Gold Accent Card -->
<div class="card-gold">...</div>
```
