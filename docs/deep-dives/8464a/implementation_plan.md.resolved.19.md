# Campaign Mode (Mode B) - Blueprint

Your new request describes a deeply hierarchical striking system—what I'm designating as **Campaign Mode**. 

This is fundamentally different from the 10-Slot Monolithic architecture we already built. Instead of a flat list of assets, you want a **Grouped Array** architecture.

### Conceptual Architecture
In Campaign Mode, the center payload editor shifts into a "Loadout Builder":
- **Strike Group Alpha**: 
  - *Primary Instruction*: "Extract system vulnerabilities."
  - *Attached Ammo*: [Asset 1, Asset 2, Asset 3...]
- **Strike Group Beta**:
  - *Primary Instruction*: "Rewrite in Go."
  - *Attached Ammo*: [Asset 4, Asset 5...]

When you pull the trigger, the Engine fires **consecutively** (5 total strikes in the example above). Asset 1 gets struck. Then Asset 2. Then Asset 3. Then Asset 4. Then Asset 5. The engine handles the looping automatically, independent of any visual 10-slot UI limits.

## The UI Plan

To house this without destroying your existing Monolithic 10-slot rig, we need a Master Toggle at the top of the screen:
**[ MONOLITHIC STRIKER | CAMPAIGN STRIKER ]**

### If you toggle to Campaign Striker:
1. **The Right Sidebar Changes**: The static 10-box grid disappears. It is replaced by a dynamic queue list that just says "Total Pending Strikes: X", tracking exactly how many payloads you have loaded across all your groups.
2. **The Center Pane Changes**: "Active Payload" becomes "Strike Groups". You can click `[+ ADD GROUP]`. Each group gives you one big text box for the Prompt, and a drop-zone where you can assign multiple ammo targets to that specific prompt. 

## User Review Required
> [!WARNING]  
> This requires building a **completely separate routing state** within the `PayloadStrikerScreen` and the `SequenceOrchestrator`. 
> 
> The UI for dragging/selecting ammo into separate "Groups" requires a decent structural overhaul compared to our flat "Loaded Ammo" array. 
> 
> Do you approve this **Strike Group** conceptual layout and the addition of a master switch to flip between Monolithic (Mode A) and Campaign (Mode B)?
