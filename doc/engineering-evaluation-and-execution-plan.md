# Engineering Evaluation and Follow-up Execution Plan

This document is an internal assessment based on external evaluation, the current repository state, and issues encountered during the most recent round of actual development and delivery.

The goal is not to repeat the README, but to answer three questions:

1. How well is this project currently doing
2. What are the real current shortcomings
3. What should be the priority order going forward

## 1. What Stage Is the Project Currently In

The current project is no longer just a collection of scripts, nor is it just a demo for demonstration purposes.

It already has the following characteristics:

- Has a browser frontend
- Has a Rust API service layer
- Has a Python processing pipeline
- Has a Docker delivery format
- Has a desktop packaging pipeline
- Has productized capabilities like task directory, event stream, artifact download, and stage diagnostics

A more accurate description is:

- It is already a "working product prototype"
- But it has not yet fully entered the engineering state of "low maintenance cost, stable delivery"

## 2. Which Judgments from External Evaluation Are Correct

### 2.1 The README's Navigation Approach Is Correct

The repository truly cannot be explained by a single file anymore.

Using the README as a navigation hub rather than stuffing all details into it is the right direction.

### 2.2 The Overall Shape of Frontend + Backend + Pipeline Is Complete

The current repository already covers:

- Frontend interaction
- Task submission and querying
- OCR integration
- Translation processing
- Layout reconstruction
- Artifact download
- Docker and desktop delivery

From a product pipeline perspective, this project is complete.

### 2.3 The Rust API + Python Pipeline Combination Is Reasonable

This architecture is not strange; it is actually very suitable for the current scenario:

- Rust handles the server side, task scheduling, state management, interfaces, and delivery
- Python handles OCR, translation, layout, model ecosystem, and rapid experimentation

This technical approach has no fundamental issues.

## 3. Issues External Evaluation Did Not Fully Articulate but Are More Critical Now

External evaluation mentioned "documentation consistency, boundary definition, reproducible builds" — all correct.

But from recent real-world pitfall experiences, the truly more core issues are:

## 3.1 The System Still Lacks Sufficiently Hard "Single Sources of Truth"

Many problems appear on the surface as:

- GitHub Actions errors
- Desktop build failures
- Frontend cannot get fields
- Endpoint changes needed after download path changes

The essence is that the following sources of truth are not yet unified enough:

- Documentation source of truth
- Configuration source of truth
- Artifact source of truth
- Desktop build input source of truth
- Path and directory structure source of truth

That is:

- Files that exist locally may not exist in CI
- A parameter that works with default values locally may not work in a clean environment
- A download path is derived from code rather than registered in the database
- A field exists in the documentation but the endpoint does not stably return it

If these issues are not resolved, every new feature added will amplify maintenance costs.

## 3.2 The Biggest Shortcoming Is Not Algorithms but Engineering Consistency

The project's core selling points are of course:

- Preserving layout
- Translation quality
- Final PDF output quality

But the most time-consuming current problems do not primarily come from insufficient model capabilities, but from:

- Long block translation instability
- Insufficient formula placeholder protection
- Unstable degradation strategies after block-level failures
- Insufficiently direct stage diagnostics
- Inconsistent build pipeline between local and CI
- Occasional disconnects between documentation and code structure

In other words:

- What is currently lacking most is not "integrating a stronger model"
- But "making the existing pipeline more stable, more explainable, and easier to troubleshoot"

## 3.3 A Large Repository Is Not the Sin; Unclear Boundaries Are

The current repository is a mono-repo with multiple components; this is acceptable in itself.

The real issue is not that there are many directories, but that the contracts between these directories are not hard enough, for example:

- Which stable endpoints the frontend depends on
- Which backend fields are long-term commitments
- Which parameters Python should accept
- Whether download functionality depends on directory derivation or database registration
- Which explicit files desktop packaging depends on

As long as boundaries are clear, a mono-repo is perfectly maintainable.

## 4. How to Judge Whether the Project Is "Mature Enough" at This Stage

To judge whether this project is truly mature, don't just look at "can it produce a PDF"; more importantly, look at the following four things.

### 4.1 Can It Stably Build in a Clean Environment

Judgment criteria:

- On a different machine or GitHub Actions
- Does not depend on local historical files
- Does not depend on manual resource supplementation
- Can directly produce a runnable package

Recent continuous GitHub Actions errors indicate this area is still in the remediation phase.

### 4.2 Are API Contracts Stable

Judgment criteria:

- Fields documented in the docs are stably returned by the endpoint
- Frontend displaying a timeline does not need to guess how event streams are assembled
- Artifact download paths are uniformly exposed by the backend; frontend does not need to guess directories

### 4.3 Are Tasks and Artifacts Traceable

Judgment criteria:

- What happened to each task can be looked up
- Elapsed time for each stage can be looked up
- Why something failed can be identified
- What files should ultimately be downloaded can be stably obtained

### 4.4 Does the Translation Pipeline Have Stability Mechanisms

Judgment criteria:

- Long paragraphs do not easily break
- Formulas/placeholders are not easily lost
- Automatic degradation occurs when anomalies are encountered
- Users see an explainable failure reason rather than just "task failed"

## 5. Directions Most Worth Continued Investment

Looking at both "product effectiveness" and "engineering returns," the most worthwhile investment directions are not blindly expanding features, but the following three main lines.

### 5.1 First Main Line: Delivery Engineering Consolidation

Goals:

- Stable GitHub Actions packaging
- Reproducible Windows desktop builds
- Clear Docker, frontend, and backend delivery materials
- No longer depending on local implicit files

This is the prerequisite for moving the project from "it works on my machine" to "stable delivery on other people's machines."

### 5.2 Second Main Line: Continue Hardening Backend Contracts

Goals:

- API documentation stays consistent with actual responses
- `runtime.stage_history`, `events`, `artifacts` structures remain stable long-term
- Download capabilities go through database registration rather than guessing directories
- Request parameters, task persistence, and downstream pass-through pipelines are traceable

This is the key to reducing frontend-backend integration testing costs.

### 5.3 Third Main Line: Translation Stability Takes Priority Over "Fancier Enhancements"

Goals:

- More stable long text block splitting
- More stable formula and placeholder protection
- More stable failure retry and degradation strategies
- More intuitive page-level quality diagnostics

This takes priority over RAG, glossary enhancement, etc.

The reason is simple:

- If basic stability is not sufficient, integrating more enhancement capabilities will be offset by unstable results
- Only when the basic pipeline is stable will glossaries, abbreviation tables, and RAG truly amplify their value

## 6. Recommended Three-Phase Follow-up

## Phase One: Unify Engineering Sources of Truth

Priority actions:

- Unify documentation entry points
- Unify version source of truth
- Unify desktop packaging inputs
- Unify configuration sources
- Unify artifact registration method

Acceptance criteria:

- Clean environment builds no longer fail due to missing local files
- Documentation no longer makes people unclear about which is the current valid entry point

## Phase Two: Make API and Task State Layer a Stable Contract

Priority actions:

- Solidify task details structure
- Solidify stage timeline structure
- Solidify event stream structure
- Solidify artifact inventory structure
- Solidify error diagnostics structure

Acceptance criteria:

- Frontend does not need to guess fields
- Frontend does not need to reconstruct on its own the state the backend should directly provide

## Phase Three: Focus on Polishing Translation Quality Stability

Priority actions:

- Long block splitting strategy
- Formula/placeholder protection
- Single block failure rollback
- Page-level quality diagnostics
- Observability of quality issues

Acceptance criteria:

- Success rate for the same type of PDF significantly improves
- Users see fewer "failures"
- Even when failures occur, users can know exactly which stage and which block went wrong

## 7. One-Sentence Conclusion

The strongest aspect of this project right now is not any single algorithm, but the fact that it has truly built the entire pipeline of "PDF upload -> OCR -> Translation -> Layout reconstruction -> Download delivery."

What needs the most continued investment now is not blindly adding more capabilities, but polishing the following aspects of this pipeline to a level suitable for long-term maintenance:

- Engineering consistency
- Contract stability
- Build reproducibility
- Translation stability

If these four things are done solidly, this project will move from "a strong prototype" to truly entering the "stably deliverable product engineering" stage.
