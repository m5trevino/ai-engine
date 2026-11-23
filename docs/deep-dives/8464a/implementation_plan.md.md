# LIM Security Protocol Workspace Integration (Correction)

My fault. You aren't replacing the whole engine shell, you're mapping this massive workflow *strictly* inside the `Payload Striker` workspace across the 4 layout columns. The Left Navigation Menu stays absolutely untouched and anchored.

Here is the precise visual and logical breakdown of what goes into those 4 columns based exactly on your green and cyan annotations.

## Workstation Layout: 4 Columns (Left to Right)

### Column 1 (Box 1): The Director
This acts as the engine's primary file-system interface and execution tracker.
- **State A (Prompt Phase):** Loads the `prompts/` list. Click eyeball to view in modal. Click file to select.
- **State B (Payload Phase):** Once prompt is selected, this immediately flips to display your `payloads/` local file explorer. You click files to select them (they shoot over to Box 2). Contains the `[SELECT ALL PAYLOADS]` and `[CONFIRM TRANSFER]` triggers.
- **State C (LIM Protocol Execution):** Once you hit "Confirm", the selected payloads from Box 2 shift *back* into Box 1. Box 1 now tracks their processing limits dynamically (Yellow = Firing, Green = Success, Red = Fail).

### Column 2 (Box 2): The Staging & Response Bay
- **State A (Staging):** As you select payloads in Box 1, they stack up here. 
- **State B (LIM Execution):** The moment you pull the trigger, the payloads move to Box 1, and Box 2 instantly transforms into the **LLM Response Terminal**. It will print the parsed payload responses returning from the LIM protocol. Finished items can be clicked to open the Full Context Modal (Original Prompt + LLM Response).

### Column 3: Telemetry & Logic
- **Top Block:** Master Strike Settings (Batch/Ultra toggles, Temperature, Thread granularity).
- **Bottom Block:** The Rev-Limiter Live Dashboard mapping Requests/Min and TPS metrics to prevent rate-limit crashes.

### Column 4 (Sidebar): Stats & Execution
- **Metrics Panel:** Total Payloads completed. Total left in queue. Average response latency.
- **Trigger:** Master Arm and `LAUNCH SEQUENCE`.

## Python Backend Bridge
Because this operates directly with the OS inside the app, the UI needs to connect to FastAPI backends to physically crawl your system. I need to build:
- `GET /v1/lim/prompts`
- `GET /v1/lim/payloads/{path}`
- `POST /v1/lim/save` (Writes `payload-filename-done.YY-MM-DD-HHMM.md` exactly to disk).

## User Action Required (Coordinate Hand-Off)
> [!WARNING]  
> Before I lock this in, I need the absolute local file paths perfectly mapped to safely give the FastAPI shell root access.
> 
> **Where do these file structures exist locally on your MX Linux machine?**
> 1. Absolute path to the `prompts` directory:
> 2. Absolute path to the `payloads` parent directory:

Provide those coordinates and we'll rip out the standard layout for this workspace and build out the LIM Architecture.
