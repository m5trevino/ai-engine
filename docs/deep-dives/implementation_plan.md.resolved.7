# Static Asset Path Alignment

The WebUI is still 404ing because the Vite build is outputting to `app/static`, but the backend is looking in `ui/dist`. Also, the Vite `base` configuration is currently set to `/static/`, which forces asset requests into sub-paths. This plan will unify the pipeline for a root-level launch.

## User Review Required

> [!IMPORTANT]
> **Static Path Shift**: We are moving the "Source of Truth" for production assets to `app/static`. This is where Vite is currently dumping the files, so we’ll anchor the backend there.

## Proposed Changes

### [Backend Routing Correction]

#### [MODIFY] [main.py](file:///home/flintx/peacock-engine/app/main.py)
- Update static mounting to check `app/static` first.
- Mount `app/static` at both `/static` (for assets) and `/` (for the HTML entrypoint).

### [Frontend Config Refinement]

#### [MODIFY] [vite.config.ts](file:///home/flintx/peacock-engine/ui/vite.config.ts)
- Change `base: '/static/'` to `base: '/'` to allow the UI to function correctly when mounted at the domain root.
- (Optional) Keep `outDir: '../app/static'` as it aligns with the backend's internal structure.

## Open Questions

- None. The logs clearly show the build successfully hit `../app/static/`, so we just need to tell FastAPI to look there.

## Verification Plan

### Automated Tests
- `ls app/static/index.html` on VPS.
- `cat app/main.py | grep static` to verify mount points.

### Manual Verification
- Refresh `https://chat.save-aichats.com/` and confirm the UI loads with assets.
