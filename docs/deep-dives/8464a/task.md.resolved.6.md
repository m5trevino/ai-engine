# Task: Resolve UI Infrastructure & Type Entropy

- [x] **Infrastructure Fixes**
    - [x] Install `@types/react` and `@types/react-dom` in `ui/`
    - [x] Run `npm install` for workspace sync
- [x] **App.tsx Type Patching**
    - [x] Inject `ApiKeyCardProps` and `ModelRowProps` interfaces
    - [x] Type event handlers (Change, Form events)
    - [x] Type API response/chunk parameters
- [x] **Verification**
    - [x] Run `npm run lint` (`tsc --noEmit`) to verify zero-error state
