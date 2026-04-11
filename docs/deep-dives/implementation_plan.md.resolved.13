# Strategic Dashboard Overhaul: 'Sand Hill' UI Upgrade

This plan transforms the Dashboard into a high-performance workspace similar to Google AI Studio, prioritizing technical controls, strategic objectives (Goals), and extremely sharp typography for maximum readability.

## User Review Required

> [!IMPORTANT]
> **Typography Pivot**: I am upgrading the font system to **Geist/Inter** with high-contrast weights. This will make the text "pop" and feel like a premium engineering rig.
> **Layout Shift**: Sidebars will be collapsible on the right. This maintains the "clean desk" feel while providing instant access to advanced strike parameters.

## Proposed Changes

### [Masterpiece Typography & Theme]

#### [MODIFY] [index.css](file:///home/flintx/peacock-engine/ui/src/index.css)
- **High-Contrast Fonts**: Import and configure `Outfit` for headlines and `Roboto Mono` for technical labels.
- **Enhanced Utilities**: Add CSS variables for "Neon Glow" effects and sharper border treatments.

### [UI Architecture & State]

#### [MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)
- **Generation State**: Add `temperature`, `topP`, `maxTokens`, and `systemInstructions` to the main `Dashboard` state.
- **Collapsibility**: Implement `isRightSidebarOpen` state with `AnimatePresence` for smooth transitions.
- **Right Sidebar (Dashboard Only)**:
    - **[NEW] Section 1: Run Settings**: Sliders for Temp, Top P, Max Tokens.
    - **[NEW] Section 2: System Protocol**: A persistent "System Instructions" text area.
    - **[NEW] Section 3: Feature Objectives (Goals)**: A modular list of "Engine Features" that acts as your tactical goals list.

### [Neural Link Integration]

#### [MODIFY] [api.ts](file:///home/flintx/peacock-engine/ui/src/lib/api.ts)
- **Dynamic Config**: Update `PeacockWS` to transmit the live `temp`, `topP`, etc. from the sidebar in every `config` sync message.

## Open Questions

- **Feature Goals**: Since you mentioned the sidebar features *are* the goals, I’ll pre-load it with items like "WebSocket Streaming", "Multi-Gateway Support", and "Precision Token Counting". Are there any other specific "Goals" you want visible in that list right now?

## Verification Plan

### Automated Tests
- Check sidebar animation performance.
- Verify WebSocket `config` messages carry the new parameters.

### Manual Verification
- Toggle the right sidebar and verify the chat area resizes smoothly.
- Adjust Temperature and verify it affects the AI response "vibe".
- Inspect typography for that "bright and readable" pop.
