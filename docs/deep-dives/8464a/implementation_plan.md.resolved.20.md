# Campaign Mode UI: Horizontal Column Redesign

I see the drawing. You are visualizing a massive **multi-column command center** for Campaign Mode, rather than the vertical stacking I just pushed. This is a much colder, more industrial "Sand Hill" layout because it shows you all the routing at a single glance.

Here is how I will reconstruct the entire `PayloadStrikerScreen` to match your diagram when switched to **Campaign Mode**:

### The New Architecture Layout

The Center area (which usually holds the vertical Ammo Pile and Editor) will be split vertically into **3 distinct columns**:

1. **Column 1: Prompt Master (pick prompt)**
   - A vertical list of your "Strike Groups" (Prompts). 
   - You can click one to make it the "Active" group. 
   - Button at the bottom to `[+ ADD NEW PROMPT]`.

2. **Column 2: The Vault (list of payloads)**
   - This holds the Ammo Pile (all your inactive files). 
   - When you have a Prompt selected in Column 1, clicking a file here moves it directly into Column 3.

3. **Column 3: Active Loadout (payloads for current selected prompt)**
   - This shows the ammo explicitly attached to the prompt you highlighted in Column 1. 
   - You can click an 'X' to detach it and send it back to Column 2.

### The Right Side
The logic moves cleanly to the right exactly as you drew it:
- **Run Settings**: Temperature, Top-P, Strike Mode (Batch/Ultra) stacked neatly.
- **Sequence Striker**: The dynamic pipeline manifest grid and the heavy `LAUNCH` trigger.

## User Review Required
> [!WARNING]  
> If I execute this layout, the **Logs / Telemetry** panel (which currently sits at the bottom) needs somewhere to live. I can either:
> - **A)** Squeeze it horizontally below the 3 columns in the center.
> - **B)** Move the telemetry to an overlay/drawer that slides up when the strike executes.
> 
> My recommendation is **A** (keep it mounted permanently below the 3 columns so you have constant visual confirmation). 

Confirm if this matches your drawing's vision completely, and I will rip out the existing Campaign UI and lay this glass down.
