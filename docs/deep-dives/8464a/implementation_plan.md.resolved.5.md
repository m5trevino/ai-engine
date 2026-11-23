# Token Counter Emergency Repair & Unification

The `app/utils/token_counter.py` module was corrupted during a branch merge, resulting in a `SyntaxError` (unterminated triple-quoted string) and dual-implementation bloat. This plan will restore a single, high-performance "Source of Truth" for token counting.

## User Review Required

> [!CAUTION]
> **Production Crash**: This error is currently preventing the Peacock Engine from booting on the VPS. I am force-fixing the file and pushing to `main` immediately once approved.

## Proposed Changes

### [Backend Utility Repair]

#### [MODIFY] [token_counter.py](file:///home/flintx/peacock-engine/app/utils/token_counter.py)
- **Purge Merge Markers**: Remove all `<<<<<<<`, `=======`, and `>>>>>>>` tokens.
- **Architectural Unification**: 
    - Retain the `PeacockTokenCounter` coordinator class for registry-aware counting.
    - Consolidate the `GeminiTokenCounter` and `GroqTokenCounter` implementations into a clean class hierarchy.
    - Restore the `count_tokens` convenience function expected by the `striker` module.
- **Syntactic Sealing**: Ensure all docstrings and block comments are properly terminated.

## Open Questions

- None. This is a critical stability fix.

## Verification Plan

### Automated Tests
- Run `python3 app/utils/token_counter.py` locally to verify the internal test suite passes.
- Run `python3 -m app.main` (dry run) to ensure the import chain is healthy.

### Manual Verification
- Deploy to VPS and verify the engine boots without `SyntaxError`.
