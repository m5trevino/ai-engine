# LIM Security Protocol Workflow Implementation

I have analyzed the `OPERATOR-01 - Payload Management Workflow` directive and the annotated screenshot. This is a massive shift from an isolated UI to a direct, dynamic filesystem bridge. You are turning the UI into a literal local file explorer and execution loop.

Before I write a single line of code, we need to establish the exact architecture for this because it requires backend (Python) changes and completely overrides the layout we just built.

## 1. Backend Filesystem Bridge (Python FastAPI)
To make this work, the UI needs to read and write directly to your local OS filesystem outside of the React build. I will need to build/update the following endpoints in your `main.py` or a router:
- `GET /v1/prompts`: Reads a specific `prompts/` directory to list available `.txt` or `.md` files.
- `GET /v1/payloads/{dir_path}`: A directory traversal endpoint to surf payload folders.
- `POST /v1/save-response`: Writes the LLM output back to the specific directory as `payload-filename-done.YY-MM-DD-HHMM.md`.

## 2. Layout Transformation (The "Green Boxes")
Your diagram drew **Box 1** entirely over the Left Navigation Menu (Engine Status, Core Modules, etc) and **Box 2** over the "Define Prompts" column. 

> [!WARNING]
> **CRITICAL QUESTION: Are we destroying the Left Navigation Menu?** 
> If I build Box 1 where you drew it, the main menu disappears. Do you want this Payload Workflow to be a completely standalone, full-screen terminal that hides the nav menu? Or did you mean for "Box 1" and "Box 2" to sit *inside* the center area (replacing the 3 columns we just built)?

### Proposed UI Logic (Assuming it replaces the center area):
- **Phase A (Target Acquisition):** 
  - **Left Box:** Lists global prompts from your hard drive. Click eyeball to read in a modal. Click to select.
  - *Dynamic Shift:* Once a prompt is selected, this box morphs into a filesystem explorer. You click through directories, eyeball payloads, and check boxes (or "Select All"). Target Button: `[LOCK PAYLOADS]`.
- **Phase B (Execution - LIM PROTOCOL):**
  - **Box 1 (Processing Queue):** The locked payloads populate here. The UI tracks their status (Yellow = Firing, Green = Success, Red = Failed).
  - **Box 2 (Response Terminal):** As strikes land, the response data from the LLM flashes here, and the Python backend simultaneously writes the `...done.md` file to your server disk. You can click any finished payload to pull up the complete Prompt + Response modal.

## User Action Required
1. **Target Directories:** What are the exact absolute paths on your MX Linux machine where the `prompts` sit, and what is the root path for navigating `payloads`?
2. **Layout Clarification:** Do I overwrite the Left Nav menu to build Box 1, or do I contain Box 1 and 2 inside the main center application window?

Provide confirmation on those two points and I will begin the backend Python restructuring.
