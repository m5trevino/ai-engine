# Asset Distribution Mode - Implementation Plan

You’re talking about an **Asset Split / Distribution Mode**. 

Right now, the Striker runs in **Monolithic Mode**: It grabs all your active payloads, stitches them into one massive Frankenstein block (using the specific prompts we just built), and fires that *exact same massive block* through every slot in your sequence.

You want a new toggle to run **Distributed Mode**: Where each payload asset (Prompt + Code) is treated as its own *isolated strike*.

### The Operation Logic
I will build a new toggle in the Tactical Command sidebar (underneath BATCH / ULTRA) called **PAYLOAD ROUTING: [ MONOLITHIC | DISTRIBUTED ]**.
- **MONOLITHIC**: (Default) The behavior we just built. Everything goes out together.
- **DISTRIBUTED**: The Orchestrator breaks the payload apart. It fires one API strike for Asset #1, a totally separate API strike for Asset #2, etc.

## User Review Required

> [!WARNING]  
> If we run in **DISTRIBUTED** mode, how do you want the assets to map to the 10-Slot Sequence Manifest?
> 
> **Option A (Manifest Drives)**: 
> If you have 3 assets loaded in your bay, and 10 active slots in your manifest, do we route Asset #1 to Slot 1, Asset #2 to Slot 2, Asset #3 to Slot 3, and then loop back around (Asset #1 to Slot 4, etc.) until all 10 slots fire?
> 
> **Option B (Asset Count Drives)**: 
> If you have 3 assets loaded, the sequence will completely ignore slots 4 to 10. It will just execute exactly 3 strikes (one for each asset) using the model/temp settings from Slot 1, and then shut down.

Tell me which option fits the architecture in your head, and I'll lay the brickwork.
