# Design System Strategy: Tactical Industrialism

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Kinetic Brutalist Interface."**

We are moving away from traditional "glassmorphism" or flat SaaS aesthetics and moving toward **high-fidelity hardware simulation**. The goal is to make the user feel like they are interacting with a physical, military-grade console—heavy, metallic, and mission-critical.

## 2. Visual Principles

### 2.1 Physicality & Weight
- **Recessed Data Wells:** Information isn't just "on" a page; it is sunk into the substrate. This is achieved using deep internal shadows and dark backgrounds.
- **Chrome Panels:** Main UI containers use metallic gradients and subtle top-lighting (1px highlight) to simulate CNC-machined aluminum or high-grade steel.
- **3D Pop-Out:** Interactive elements (buttons, toggles) physically protrude from the surface using hard, offset shadows.

### 2.2 Kinetic Feedback
- **Hardware Interaction:** Buttons should have a physical "click" feel. This is simulated by removing shadows and adding a slight vertical translation (translate-y) on the active state.
- **Bioluminescent Overlays:** While the base is dark metal, data visualization uses glowing neon (Cyber Cyan, Cyber Magenta) to simulate high-contrast heads-up displays.

## 3. Core Color Palette
- **Primary Substrate:** Chrome Dark (`#0a0a0c`)
- **Accent Light:** Cyber Cyan (`#00f3ff`)
- **Warning/Critical:** Cyber Magenta (`#ff0055`)
- **Tactical Utility:** Hazard Gold (`#ffd700`)

## 4. Typography
- **Headlines:** Oswald. It provides a condensed, industrial strength that mirrors signage found in high-pressure environments.
- **Data & Body:** Share Tech Mono. This maintains a clear, legible terminal/CLI aesthetic for all mission-critical data output.

## 5. UI Components
- **The Bezel:** A signature 1px translucent white border on top and left edges to simulate light hitting the corner of a metal plate.
- **The Well:** A signature inner shadow treatment for all lists and terminal feeds to create depth.
- **The Switch:** Large, chunky toggles that look like they require force to flip.