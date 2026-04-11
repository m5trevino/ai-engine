# Tactical Visibility Upgrade

The Pilot's Dashboard (Payload Striker) is currently hard to locate. We need to engrave the access points into the UI shell for high-stakes orchestration.

## Proposed Changes

### [Component: App Header]
- **[MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)**: 
    - Add a `Target` icon button to the utility bar (next to Bell/Settings).
    - Wire it to toggle `isRightSidebarOpen`.
    - Apply `gold-glow` kinetic when active.

### [Component: Sidebar Nav]
- **[MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)**: 
    - Wire the `INITIALIZE SEQUENCE` button to set `setIsRightSidebarOpen(true)`.

### [Component: Dashboard Sidebar]
- **[MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)**: 
    - Ensure the right sidebar container has `overflow-y-auto` and `no-scrollbar` to allow access to all tactical modules (Context Vault, Striker, Gauges).

## Verification Plan

### Manual Verification
- Verify the **Target** icon appears in the top right.
- Verify clicking it toggles the tactical dashboard.
- Verify reaching the bottom-left **Initialize Sequence** button also opens the dashboard.
- Verify full scrollability of the tactical modules.
