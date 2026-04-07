# PEACOCK ENGINE - Design Changes Checklist
> Apply these fixes to all 5 OG screens for consistent "Masterpiece" look

---

## 🔧 LAYOUT FIXES

### TopNav Background
```diff
- bg-[#101418] OR bg-[#181c20] (mixed)
+ bg-[#181c20] (standardized)
+ border-b border-[#414753]/10
```

### SideNav Width
```diff
- w-[260px] OR w-64 (256px-280px mixed)
+ w-64 (exact 256px)
```

### Status Bar Height
```diff
- h-8 OR fixed bottom-0
+ h-8 (exact 32px)
+ bg-[#0a0f13] (surface-container-lowest)
```

---

## ✏️ TYPOGRAPHY FIXES

### Headline Font Weight
```diff
- font-bold (700)
- font-extrabold (800) 
- font-black (900)
+ font-medium (500) for ALL headlines
```

### Headline Tracking
```diff
- tracking-normal
- tracking-wide
+ tracking-tight (-0.02em)
```

### Label Text
```diff
- font-bold uppercase
+ font-medium uppercase
+ tracking-wider (0.05em)
```

### Mono Data
```diff
- font-mono text-xs (10px)
+ font-mono text-xs (11px)
+ tracking-wide (0.02em)
```

---

## 🎨 COLOR FIXES

### Border Colors (ALL borders)
```diff
- border-white/5
- border-white/10
- border-gray-500
+ border-[#414753]/10 (outline-variant)
```

### Card Backgrounds
```diff
- bg-surface-container-low
+ bg-[#181c20] (surface-container-low)
+ hover:bg-[#262a2f] (surface-container-high)
```

### Primary Text
```diff
- text-blue-400
- text-[#4d94ff]
+ text-[#aac7ff] (primary)
```

### Gold/Secondary
```diff
- text-yellow-400
- bg-yellow-500
+ text-[#ffdb3c] (secondary-container)
+ bg-[#ffdb3c]
```

---

## 📦 SPACING FIXES

### Card Padding
```diff
- p-4 (16px)
- p-6 (24px)
+ p-5 (20px) STANDARD
```

### Section Padding
```diff
- p-6
+ p-8 (32px)
```

### Grid Gaps
```diff
- gap-4 (16px)
+ gap-6 (24px)
```

---

## 🎯 COMPONENT FIXES

### Status Dots
```diff
- w-2 h-2 (8px)
+ w-1.5 h-1.5 (6px)

- Rounded variations
+ rounded-full (consistent)
```

### Badges
```diff
- px-2 py-0.5
+ px-2.5 py-1

- text-[10px]
+ text-[10px] font-semibold

+ Add gap-1.5 for dot spacing
```

### Buttons
```diff
# Primary Button
- bg-primary
+ bg-gradient-to-br from-[#aac7ff] to-[#0066cc]

# Gold Button
+ filter: drop-shadow(0 0 8px rgba(255, 219, 60, 0.27))
+ hover: drop-shadow(0 0 12px rgba(255, 219, 60, 0.4))

# All Buttons
+ active:scale-95
```

### Table Headers
```diff
- bg-surface-container-low
+ bg-[#1c2024] (surface-container)

- font-bold
+ font-medium
```

---

## 🧩 SCREEN-SPECIFIC FIXES

### API Key Management
- [ ] Status dots: 6px not 8px
- [ ] "ADD NEW KEY" button → gold style
- [ ] Telemetry panel → glass-panel class
- [ ] Key cards: standard 20px padding

### Chat Interface
- [ ] Model dropdown: add z-50
- [ ] Input area: kinetic-focus border
- [ ] Message bubbles: consistent border-width
- [ ] Right panel: sticky positioning

### Custom Tool Creation
- [ ] Modal: glass-panel backdrop blur
- [ ] Form inputs: border-b only (no full border)
- [ ] Deploy button: gold-glow effect
- [ ] Card grid: gap-6 not gap-4

### Model Registry
- [ ] Table header: surface-container bg
- [ ] Default badge: #ffdb3c (not wrong yellow)
- [ ] Status badges: consistent px-2.5 py-1
- [ ] Left accent bar: 2px width

### Tool Configuration ✅
- [ ] Already clean - use as reference
- [ ] Just verify toggle switches match brand

---

## 📋 COPY-PASTE CSS UTILITIES

Add to `<style>` in each file:

```css
/* Glow Effects */
.gold-glow {
    filter: drop-shadow(0 0 8px rgba(255, 219, 60, 0.27));
}
.gold-glow-hover:hover {
    filter: drop-shadow(0 0 12px rgba(255, 219, 60, 0.4));
}

/* Glass Panel */
.glass-panel {
    backdrop-filter: blur(12px);
    background: rgba(38, 42, 47, 0.6);
    border: 1px solid rgba(139, 145, 158, 0.15);
}

/* Kinetic Focus */
.kinetic-focus:focus-within {
    border-left: 2px solid #aac7ff;
    background-color: #181c20;
}

/* Status Dots */
.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
}
.status-dot.active {
    background: #00C851;
    box-shadow: 0 0 6px rgba(0, 200, 81, 0.6);
}
```

---

## ✅ FINAL CHECKLIST

For each of the 5 screens, verify:

- [ ] TopNav bg = #181c20
- [ ] Headlines use font-medium (500)
- [ ] SideNav width = 256px
- [ ] Status bar height = 32px
- [ ] Card padding = 20px
- [ ] All borders = outline-variant/10
- [ ] Buttons have active:scale-95
- [ ] Status dots = 6px
- [ ] Font tracking = tight for headlines
- [ ] Gold elements have glow effect

---

**Tool Config screen is your reference** - copy its font weights, spacing, and color usage exactly.
