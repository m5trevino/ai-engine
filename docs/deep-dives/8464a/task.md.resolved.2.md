# Task: Hardening Peacock Engine

- [x] **Backend Hardening**
    - [x] Add `HighSignalLogger.error` method in `app/utils/logger.py`
    - [x] Add `peacock-engine` to workspace members in `pyproject.toml`
- [x] **Frontend Type Safety**
    - [x] Refactor `ApiKeyCard` to use `React.FC` or proper props interface in `ui/src/App.tsx`
    - [x] Refactor `ModelRow` to use `React.FC` or proper props interface in `ui/src/App.tsx`
- [x] **Verification**
    - [x] Verify `PeacockTokenCounter` doesn't crash on errors
    - [x] Verify `App.tsx` TypeScript errors are cleared
    - [x] Audit `peacock-engine` git status
