# LIM Security Protocol: Full-Screen Dashboard Override

Your cyan diagram answers my question perfectly. We are blowing away the global navigation menu during this mode to turn the engine into a dedicated full-screen battle station for the **LIM Security Protocol**. 

I understand exactly how the layout maps out now.

## The 4-Zone UI Architecture

The app will transition through two distinct stages (Staging visually converts into Execution):

### STAGE 1: Target Staging (Pre-Strike)
- **Zone 1 (Far Left):** The Directory Explorer. Loads `prompts/`. Clicking an eyeball opens a modal to read it. Selecting a prompt locks it in and flips this zone to surf `payloads/` directories.
- **Zone 2 (Inner Left):** Empty or showing instructions, waiting for you to `[SELECT ALL]` payloads in Zone 1. Once selected, they queue up here.
- **Zone 3 (Center Block):** 
  - **Top:** Strike Settings (Ultra/Batch, Granular routing logic, Temperature, Threads).
  - **Bottom:** The Rev-Limiter/Governor dashboard (Tracking Tokens/Sec, Requests/Min gauges).
- **Zone 4 (Right Sidebar):** The execution manifest. Shows total payload count, average response time, Master Arm, and `LAUNCH SEQUENCE`.

### STAGE 2: LIM Execution (Post-Launch)
- **Zone 1 (Far Left):** Morphs into the **Processing Queue**. Shows the selected payloads lighting up (Yellow = Firing, Green = Done, Red = Failed).
- **Zone 2 (Inner Left):** Morphs into the **Response Terminal**. As the LLM returns data, the responses print here, and the output is silently mapped to disk via `payload-filename-done.YY-MM-DD-HHMM.md`.

## The Python Backend Bridge
Because this runs live against your filesystem, I need to build FastAPI hooks in Python.
1. `/lim/prompts`: Reads your local Prompts directory.
2. `/lim/payloads/{path}`: A directory crawler to surf your payload files.
3. `/lim/save`: Takes the LLM payload response and writes the `...done.md` output cleanly onto the disk next to the target.

## User Action Required (The Final Variable)

> [!CAUTION]  
> Before I execute the Python backend edits, you  must provide the absolute routing paths for your MX Linux rig!
> 
> **Where are these directories physically located on your machine?**
> - What is the absolute path to the `prompts` directory? (e.g., `/home/flintx/Documents/prompts`)
> - What is the root path to the `payloads` directory?

Drop those two file paths in the chat, and I will immediately tear down the UI to construct this 4-Zone LIM architecture and wire the Python APIs.
