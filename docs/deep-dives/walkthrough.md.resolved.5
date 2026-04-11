# Payload Prompt Routing Walkthrough

The Peacock Engine now supports modular, multi-tier payload instruction routing. This system allows you to dictate a massive **Global Default Instruction** while simultaneously defining distinct **Custom Overrides** for individual assets loaded in the Payload Bay.

## Architecture

We fundamentally shifted how the String Array (`ammoContents`) operates. Instead of smashing raw assets together into a static block, `SequenceOrchestrator` now receives a structured `PayloadAsset` array.

```typescript
export interface PayloadAsset {
  fileName: string;
  content: string;
  customPrompt?: string | null;
}
```

## How It Works

1. **Global Default Prompt**: The top of your Payload Editor now features a sticky text area for the Global Default Prompt. Any un-targeted asset defaults to this instruction during compilation.
2. **Custom Overrides**: When you click on an asset in the "Active Payload" section, the interface expands. A new text area appears natively above the Asset Code Editor. Typing an instruction here isolates that file, forcing the AI to treat it with a unique sub-prompt explicitly.
3. **Sequence Pipeline**: When a strike is launched, `SequenceOrchestrator` maps the final command string exactly as requested:

```text
--- [ASSET: filename] ---
[INSTRUCTION]: {Custom Target Override OR Global Fallback Prompt}

[CONTENT]: {Asset Code Output}
```

### Visual Re-Assembly

The `PayloadStrikerScreen` center pane has been optimized. The active file text areas now sit securely behind kinetic hover barriers with glowing borders to visualize when an override is locked in (the red left border). Empty overrides fall back safely to the Global Instruction text space above it.

The entire UI logic has been committed and built cleanly down the pipeline, ready for deployment in your Sand Hill rig.
