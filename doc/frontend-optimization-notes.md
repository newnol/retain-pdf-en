# Frontend Optimization Notes

This document focuses solely on the real technical debt in the current `frontend/`, with the goal of helping frontend developers quickly determine:

- Which issues must be fixed first
- Which issues will directly slow down future development
- Which issues are only experience-level optimizations

## Current Structure Overview

The frontend is currently a very lightweight native JS + Tailwind page, with no framework and no bundler/runtime state management layer.

Quantitative overview:

- Core interaction entry point: [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js) approximately `1291` lines
- UI rendering layer: [ui.js](/home/wxyhgk/tmp/Code/frontend/src/js/ui.js) approximately `624` lines
- Job data shaping layer: [job.js](/home/wxyhgk/tmp/Code/frontend/src/js/job.js) approximately `424` lines
- Main stylesheet: [components.css](/home/wxyhgk/tmp/Code/frontend/src/styles/components.css) approximately `1747` lines
- Total frontend source code approximately `224K`
- `frontend/node_modules` has been committed to the repository, approximately `16M`

Conclusion: This is not a case of "too many features", but rather "no stable layering has been established", so complexity is concentrated in a few large files.

## P0: Issues That Should Be Addressed First

### 1. Main entry point is too large; business logic, event binding, polling, and form assembly are all tightly coupled

File:

- [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)

Problem:

- `main.js` is simultaneously responsible for:
  - Token validation
  - Form collection
  - Task submission
  - Task polling
  - Recent tasks list
  - Developer settings
  - Browser credential dialog
  - Global page event binding
- This means any small change can easily affect other flows.

Recommendation:

- Split into at least 4 modules:
  - `job-submit.js`
  - `job-polling.js`
  - `recent-jobs.js`
  - `settings-dialog.js`
- `main.js` should only retain:
  - Page initialization
  - Module assembly
  - Top-level error handling

### 2. Global mutable state is too primitive, with no update boundaries

Files:

- [state.js](/home/wxyhgk/tmp/Code/frontend/src/js/state.js)
- [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)
- [ui.js](/home/wxyhgk/tmp/Code/frontend/src/js/ui.js)

Problem:

- `state` is a bare object, with multiple files directly writing to it:
  - `state.currentJobId = ...`
  - `state.recentJobsItems = ...`
  - `state.timer = ...`
- There are no mutation boundaries and no subscription mechanism.
- It still works now because the page is simple; once the frontend adds more features, tracing state sources will become increasingly difficult.

Recommendation:

- You don't necessarily need to adopt React/Vue.
- First, create a lightweight store:
  - `getState()`
  - `patchState(partial)`
  - `subscribe(key, fn)` or simple `subscribe(fn)`
- At minimum, separate these into independent modules:
  - `jobState`
  - `uploadState`
  - `recentJobsState`
  - `developerState`

### 3. Extensive `innerHTML` concatenation makes rendering and event binding fragile

Files:

- [ui.js](/home/wxyhgk/tmp/Code/frontend/src/js/ui.js)
- [templates.js](/home/wxyhgk/tmp/Code/frontend/src/js/templates.js)
- [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)

Problem:

- Multiple places do full-section rewrites:
  - `document.body.innerHTML = ...`
  - `list.innerHTML = ...`
- The recent tasks list also uses:
  - `list.innerHTML = reset ? markup : \`\${list.innerHTML}\${markup}\``
- Problems with this approach:
  - Event bindings are easily lost
  - Partial refreshes are uncontrollable
  - Both performance and state consistency are mediocre

Recommendation:

- No need to refactor into a component framework.
- First, convert high-frequency lists to DOM node rendering:
  - `document.createElement`
  - `replaceChildren`
  - `append`
- Prioritize:
  - Event stream list
  - Stage history
  - Recent tasks list

### 4. Hardcoded developer password in the frontend is an obvious security issue

File:

- [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)

Problem:

- Contains:
  - `const DEVELOPER_PASSWORD = "Gk265157!";`
- This is equivalent to a publicly exposed frontend password with no real security.

Recommendation:

- If this is only for "hiding advanced settings", simply change to:
  - Local toggle
  - `runtime-config`
  - Desktop app settings page entry
- If real authentication is needed, it must be moved to the backend or the desktop host layer.

## P1: Issues That Significantly Impact Maintenance Efficiency

### 5. Job data shaping layer is too thick; frontend bears too much backend compatibility logic

File:

- [job.js](/home/wxyhgk/tmp/Code/frontend/src/js/job.js)

Problem:

- `normalizeJobPayload()` does a lot of "fallback-style compatibility":
  - Multi-field fallback
  - Absolute URL completion
  - Dual-source compatibility for actions / artifacts
  - Runtime / failure / legacy style field merging
- This indicates that while the backend response contract has stabilized, the frontend is still written with "loose compatibility" in mind.

Recommendation:

- Frontend developers can request the backend to provide a more stable view contract.
- `normalizeJobPayload()` should converge to two types of work:
  - Envelope unwrapping
  - Lightweight formatting
- Stop letting it serve as an "API compatibility layer".

### 6. Polling logic and detail requests are too deeply coupled

File:

- [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)

Problem:

- `fetchJob(jobId)` fetches in a single serial request:
  - Job detail
  - Job events
  - Artifacts manifest
- Polling frequency is fixed at `3000ms`
- No adaptive behavior based on status.

Recommendation:

- Split into:
  - `pollJobSnapshot`
  - `refreshEvents`
  - `refreshArtifactsManifest`
- Strategy:
  - High-frequency polling for detail when `queued/running`
  - Low-frequency refresh for events / manifest
  - Stop immediately when `succeeded/failed/canceled`

### 7. Configuration sources are scattered; browser and desktop version logic are mixed together

Files:

- [config.js](/home/wxyhgk/tmp/Code/frontend/src/js/config.js)
- [desktop.js](/home/wxyhgk/tmp/Code/frontend/src/js/desktop.js)
- [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)

Problem:

- Currently three sources are mixed together:
  - Runtime config
  - localStorage browser config
  - Desktop bridge config
- Page logic checks `desktopMode` everywhere

Current progress:

- [desktop-host.js](/home/wxyhgk/tmp/Code/frontend/src/js/desktop-host.js) has been added, which uniformly identifies `retainPdfDesktop` and only retains the `__TAURI_INTERNALS__` compatibility shim.
- [config.js](/home/wxyhgk/tmp/Code/frontend/src/js/config.js) no longer directly detects legacy bridge names; desktop calls uniformly enter through the host abstraction.

Follow-up recommendations:

- Continue moving desktop-specific flows like "first launch / save config" from `desktop.js` another layer into the host layer.
- UI layer should only read capabilities, not directly read host differences.

### 8. Styles are concentrated in a single file; component boundaries are unclear

File:

- [components.css](/home/wxyhgk/tmp/Code/frontend/src/styles/components.css)

Problem:

- Single file approximately `1747` lines
- Dialog, topbar, hero, developer panel, status area, and event list are all mixed together

Recommendation:

- At least split by area:
  - `layout.css`
  - `dialogs.css`
  - `job-status.css`
  - `developer-panel.css`
  - `recent-jobs.css`

## P2: Experience and Engineering Standards Suggestions

### 9. `node_modules` should not be committed to the repository

File:

- `frontend/node_modules`

Problem:

- The repository currently contains the entire dependency directory, approximately `16M`

Recommendation:

- Frontend developers should remove it and confirm `.gitignore` is working.
- Only keep:
  - `package.json`
  - `package-lock.json`

### 10. Currently no frontend tests or basic linting

File:

- [package.json](/home/wxyhgk/tmp/Code/frontend/package.json)

Problem:

- Only has:
  - `build:css`
  - `watch:css`
- Missing:
  - `lint`
  - `test`
  - `format`

Recommendation:

- Minimum additions:
  - ESLint
  - Prettier
  - 1-2 basic pure function tests, starting with the normalize/summarize series in [job.js](/home/wxyhgk/tmp/Code/frontend/src/js/job.js)

## Recommended Optimization Order

### Phase 1: Low-risk Consolidation

- Remove hardcoded developer password from the frontend
- Remove `node_modules`
- Convert recent tasks list / event stream / stage history from `innerHTML` concatenation to DOM rendering
- Split `main.js`, at least extracting submit, polling, and recent jobs into separate modules

### Phase 2: Structural Governance

- Add lightweight store, consolidate `state`
- Split configuration sources, isolate browser/desktop host differences
- Reduce the "compatibility layer" responsibilities of [job.js](/home/wxyhgk/tmp/Code/frontend/src/js/job.js)

### Phase 3: Engineering Completeness

- Split stylesheet files
- Add lint / format / minimal tests
- Then decide whether to adopt a framework

## Conclusion for Frontend Developers

The current frontend is not "poorly performing", but "loosely structured".

The most important first steps are not switching frameworks, but:

1. Split [main.js](/home/wxyhgk/tmp/Code/frontend/src/js/main.js)
2. Consolidate the bare `state`
3. Convert high-frequency areas from `innerHTML` to stable DOM rendering
4. Remove pseudo-authentication and host differences from the frontend

Once these steps are done, whether you continue writing native JS or migrate to React/Vue, the cost will be much lower.
