# Payload Striker Dedicated Screen

To protect the integrity of the existing `DASHBOARD` (Chat Interface), we will isolate all Sequence Striker functionalities into a brand-new, dedicated section of the rig. 

## Architectural Separation

### [MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)
1. **New Top-Level Tab**: We will add `STRIKER` to the top navigation bar (alongside DASHBOARD, ANALYTICS, etc.).
2. **Dedicated Component (`PayloadStrikerScreen`)**: We will extract the Ammo Pile, Loaded Payload, Sequence Manifest (10 slots), Run Settings, and Telemetry out of the Chat Dashboard and into this new screen.

## Proposed Layout Schematic
Based on your box diagrams, the `PayloadStrikerScreen` will use a complex grid layout.

- **Left Rail**: Consistent main navigation (Operator-01, Core Modules).
- **Middle Column (Payload Engineering)**:
    - **Top Pane**: Ammo Pile (Context Vault).
    - **Center Pane**: The Prompt Editor / Payload Builder (what's actually getting sent).
    - **Bottom Pane Split**: 
        - Left: Live Strike Output / CLI Responses.
        - Right: Run Settings (Temp, Top P).
- **Right Column (Tactical Command)**:
    - Strike Mode (Batch/Ultra).
    - Thread Sliders.
    - The 10-Slot Sequence Manifest.
    - `LAUNCH STRATEGIC SEQUENCE` Button.
    - Real-time Pilot Gauges (TPS / RPM).

## Open Questions

> [!CAUTION]
> **Data Migration**
> Before I proceed, I will remove the Context Vault and Sequence Striker sidebars from the `DASHBOARD` entirely so that it reverts back to just your pristine Chat Interface. Is that exactly what you want, or should some small version remain on the Chat Dashboard?

Once you approve this blueprint, I will build out the `PayloadStrikerScreen` as a separate, massive grid component.
