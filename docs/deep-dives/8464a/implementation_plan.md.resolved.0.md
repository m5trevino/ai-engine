# Plan - Hardening Peacock Engine Token Counter & Workspace

## Goal
Resolve runtime bugs and IDE configuration issues in the Peacock Engine to ensure a smooth "Hardened" production state.

## User Review Required
> [!IMPORTANT]
> I am adding `peacock-engine` to your root `pyproject.toml` workspace members. This will help your IDE resolve imports correctly but may affect your `uv` or `rye` environment if you're not using it globally.
> I am also adding a missing `error` method to `HighSignalLogger` to prevent runtime crashes during token counting failures.

## Proposed Changes

### [Component] Peacock Engine Core Utilities

#### [MODIFY] [logger.py](file:///home/flintx/peacock-engine/app/utils/logger.py)
- Add `HighSignalLogger.error()` static method.
- This method will log system-level errors to `failed_strikes.log` with a unique tag and timestamp, preventing crashes when `PeacockTokenCounter` fails.

#### [MODIFY] [pyproject.toml](file:///home/flintx/pyproject.toml)
- Add `"peacock-engine"` to `tool.uv.workspace.members`.
- This tells the IDE and build tools that `peacock-engine` is a first-class project in the workspace, resolving the `app` package pathing issues.

## Verification Plan

### Automated Tests
- Run `python3 -m app.utils.token_counter` (if it has a test block) or a small test script to verify `PeacockTokenCounter` works and doesn't crash on errors.
- Check `failed_strikes.log` for correctly formatted error entries.

### Manual Verification
- Verify that the IDE lint errors @[token_counter.py:current_problems] disappear after the workspace update.
- Run `git status` in `peacock-engine` to confirm all changes are ready for a final push.
