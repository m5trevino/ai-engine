# UI Type Integrity & Hardening Plan

The UI codebase (`ui/src/App.tsx`) is currently in a state of "Type Entropy" due to missing React type definitions and implicit any declarations in high-interaction components. This plan will force-align the development environment with production standards.

## User Review Required

> [!IMPORTANT]
> **Workspace Sync**: I will be executing `npm install` within the `ui/` directory to anchor the missing `@types`. This is required for the IDE to stop red-lining core React primitives.

## Proposed Changes

### [Infrastructure Alignment]

#### [MODIFY] [package.json](file:///home/flintx/peacock-engine/ui/package.json)
- Inject `@types/react` and `@types/react-dom` into `devDependencies`.
- Ensure version parity with React 19.

### [Component Hardening]

#### [MODIFY] [App.tsx](file:///home/flintx/peacock-engine/ui/src/App.tsx)
- Re-inject `ApiKeyCardProps` and `ModelRowProps` interfaces (backported from hardening-sync).
- Explicitly type event handlers (e.g., `React.ChangeEvent`, `React.FormEvent`).
- Seal the `msg` and `chunk` parameters in API callbacks with robust interfaces.

## Open Questions

- None. The error manifest provides a complete hit-list.

## Verification Plan

### Automated Tests
- Run `npm run lint` (`tsc --noEmit`) in the `ui/` directory to verify zero-error state.

### Manual Verification
- Verify the "Current Problems" list in the IDE is cleared.
