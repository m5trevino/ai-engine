# Pilot's Dashboard: Tactical Payload & Sequence Striker

This plan transforms the Peacock Engine into a high-stakes engineering rig. We are implementing a dual-pane **Context Vault** for ammo management and a **10-Slot Sequence Striker** with "Ultra" and "Regular" threading modes.

## User Review Required

> [!IMPORTANT]
> **Ultra Mode vs Batch Mode**: 
> - **Ultra Mode**: A continuous worker pool. If you have 6 threads, it keeps 6 strikes "in flight" at all times, grabbing the next slot from the manifest as soon as one finishes.
> - **Regular Mode**: Wait for all threads in the current batch to finish before firing the next batch.
> 
> **Threading Warning**: Multi-threading can lead to rapid rate-limit depletion. I will add a "Master Arm" toggle to ensure you are ready for the heat.

## Proposed Changes

### [Engine Core Expansion]

#### [NEW] [SequenceOrchestrator.ts](file:///home/flintx/peacock-engine/ui/src/lib/SequenceOrchestrator.ts)
- Implement the batching and worker pool logic for the 10nd-slot manifest.
- Support for `delay` between slots and `repeat` on manifest completion.
- Automated key rotation logic after the 10th strike.

### [UI: Pilot's Dashboard]

#### [MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)
- **Context Vault (Ammo)**:
    - Split into "Ammo Pile" (from `/ammo`) and "Loaded Payload".
    - Buttons to transfer files and a "Prompt Editor" Slide-out.
- **Sequence Striker Module**:
    - 10-Slot list with individual Model/Key/Delay selectors.
    - "Master Fuse" execution button.
- **Gauges & Gauges**:
    - Real-time TPS (Tokens Per Second) and RPM (Requests Per Minute) gauges.
    - Progress bars for each slot in the sequence.

### [Backend Integration]

#### [MODIFY] [fs.py](file:///home/flintx/peacock-engine/app/routes/fs.py)
- Ensure `/v1/fs/ammo` and `/v1/fs/prompts` are robust and support read/write for the Prompt Editor.

## Open Questions

- **Hellcat Governor**: Should "Ultra Mode" respect the backend RPM governor, or should it bypass it for maximum speed (risking 429 errors)?
- **Key Rotation**: For the "rotate after 10" feature, should I just pick the next healthy key in the pool, or do you want to define a specific rotation order?
- **Gauges**: Would you like the gauges to have audible alerts (optional) when token burn hits a certain threshold?

## Verification Plan

### Automated Tests
- Simulate a 10-strike sequence in both "Ultra" and "Regular" modes.
- Verify key rotation occurs after index 10.

### Manual Verification
- Test file movement between "Pile" and "Loaded."
- Verify the "Master Arm" safety works as intended.
- Inspect the kinetics of the gauges during a high-speed strike.
