# Plan - Hardening Peacock Engine Token Counter & Workspace

## Goal
Resolve runtime bugs, IDE configuration issues, and TypeScript errors in the Peacock Engine to ensure a smooth "Hardened" production state.

## User Review Required
> [!IMPORTANT]
> I am adding `peacock-engine` to your root `pyproject.toml` workspace members. This will help your IDE resolve imports correctly.
> I am also updating `ui/src/App.tsx` components (`ApiKeyCard`, `ModelRow`) to use standard React typing, resolving `key` prop mismatch errors.
> I am adding a missing `error` method to `HighSignalLogger` to prevent runtime crashes during token counting failures.

## Proposed Changes

### [Component] Peacock Engine Backend Core

#### [MODIFY] [logger.py](file:///home/flintx/peacock-engine/app/utils/logger.py)
- Add `HighSignalLogger.error()` static method to prevent crashes in `PeacockTokenCounter`.

#### [MODIFY] [pyproject.toml](file:///home/flintx/pyproject.toml)
- Add `"peacock-engine"` to `tool.uv.workspace.members` for proper package resolution.

### [Component] Peacock Engine WebUI

#### [MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)
- Refactor `ApiKeyCard` and `ModelRow` to use `React.FC` or explicit interfaces to clear TypeScript "key" prop errors.

## Verification Plan

### Automated Tests
- Run `python3 -m app.utils.token_counter` to verify `PeacockTokenCounter` works and logs errors correctly.
- Run `npm run tsc` or check Vite build in UI to confirm TypeScript errors in `App.tsx` are resolved.

### Manual Verification
- Verify that @[current_problems] in `App.tsx` and the backend `token_counter.py` lint warnings are cleared.
- Ensure the engine starts and the Mission Control UI displays key telemetry without errors.
