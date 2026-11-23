# Payload Prompt Routing Plan

You want the ability to assign a **Global Default Prompt** that applies to all loaded payload assets, while retaining the ability to set a **Custom Specific Prompt** for individual assets if needed.

## Proposed Implementation

### 1. State Refactoring (`App.tsx`)
Currently, `loadedAmmo` is just a list of filenames. We will upgrade this to an object structure:
```javascript
type LoadedPayload = {
    fileName: string;
    customPrompt: string | null; // Null means it falls back to Global Default
};
```
We will also add a new state `globalPayloadPrompt` to hold the master instruction.

### 2. Payload Editor Evolution (`PayloadStrikerScreen`)
When you select an active payload in the center pane, the editor will split or offer tabs:
- **Global Settings**: A sticky textarea at the top of the Center Pane for the **Global Default Prompt**.
- **Asset Grooming**: Below it, when a specific active payload is clicked, you will see two fields:
  1. **Custom Prompt override** for that specific file (leave blank to use the Global Default).
  2. The actual **Ammo Content** (editable via `savePrompt` as it is now).

### 3. Orchestrator Payload Generation (`SequenceOrchestrator.ts`)
The `SequenceOrchestrator` will be updated to accept these structured payload objects. When building the final transmission for a strike slot, the Orchestrator will compile it like this:

```text
[SYSTEM SETTINGS]

--- [ASSET: file1.txt] ---
[INSTRUCTION]: {Custom Prompt OR Global Default Prompt}
[CONTENT]: 
{...file content...}

--- [ASSET: file2.txt] ---
[INSTRUCTION]: {Custom Prompt OR Global Default Prompt}
[CONTENT]: 
{...file content...}
```

## User Review Required

> [!IMPORTANT]  
> Are we keeping the main **System Prompt** (from `genSettings.system`) separate from this new **Global Payload Prompt**? 
> *Example: "You are a master coder" (System) vs "Refactor this code to use promises" (Global Payload).*
> Or do you want the Global Default Prompt to replace the System prompt entirely for the Striker? 

If this architecture aligns with your vision, give me the green light and I'll execute the structural upgrades.
