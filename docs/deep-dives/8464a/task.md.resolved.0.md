# Task: Hardening Peacock Engine

- [ ] **Backend Hardening**
    - [ ] Add `HighSignalLogger.error` method in `app/utils/logger.py`
    - [ ] Add `peacock-engine` to workspace members in `pyproject.toml`
- [ ] **Frontend Type Safety**
    - [ ] Refactor `ApiKeyCard` to use `React.FC` or proper props interface in `ui/src/App.tsx`
    - [ ] Refactor `ModelRow` to use `React.FC` or proper props interface in `ui/src/App.tsx`
- [ ] **Verification**
    - [ ] Verify `PeacockTokenCounter` doesn't crash on errors
    - [ ] Verify `App.tsx` TypeScript errors are cleared
    - [ ] Audit `peacock-engine` git status
