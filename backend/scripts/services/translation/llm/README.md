# LLM Directory Conventions

The current directory is split by "provider-specific implementations" and "cross-provider shared logic."

## New Contributors Start Here

- To see provider API requests and default models:
  `providers/deepseek/client.py`
- To see the unified runtime entry point for the "currently active provider":
  `shared/provider_runtime.py`
- To see provider registry/capability assembly:
  `shared/provider_registry.py`
- To see provider-side translation implementation:
  `providers/deepseek/translation_client.py`
- To see translation control context, glossary, and prompt assembly entry point:
  `shared/control_context.py`
- To see translation prompt/message construction:
  `shared/prompt_building.py`
- To see main translation orchestration and batch retry:
  `shared/orchestration/retrying_translator.py`
- To see plain-text degradation and placeholder stability strategy:
  `shared/orchestration/fallbacks.py`
- To see the complete responsibility map of the orchestration directory:
  `shared/orchestration/README.md`
- To see formula windowing and segment routing:
  `shared/orchestration/segment_routing.py`
- To see placeholder validation and degradation reasons:
  `placeholder_guard.py`

## Directory Map

- `providers/`
  Only contains provider-specific API adapters, request/response handling, and provider defaults.
  Should not carry cross-provider retry orchestration or common structured parsing rules.
- `shared/`
  Only contains cross-provider shared capabilities such as control context, caching, structured schema, and parsers.
- `shared/prompt_building.py`
  Contains cross-provider prompt/message construction logic, no longer piled into provider transport files.
- `shared/provider_runtime.py`
  Is the stable adapter for the shared layer to access the currently active provider.
- `shared/provider_registry.py`
  Contains provider runtime definitions, provider family/default model/base URL, and transport/translation capability assembly.
- `shared/orchestration/`
  Only contains cross-provider translation orchestration, fallback, and segment routing.
  This should prioritize depending on `shared/provider_runtime.py` and should not directly import `providers/deepseek/*`.
  More granular module boundary descriptions within the directory are in `shared/orchestration/README.md`.
- Top-level `llm/`
  Now only retains stable aggregation entry points and a small number of top-level shared modules.
  New code should prioritize depending on the real implementations under `providers/` or `shared/`.

## Directory Listing

- `providers/deepseek/`
  Contains DeepSeek-specific API adapters, defaults, and request/response handling
- `shared/`
  Contains cross-provider caching, control context, structured schema, and parsers
- `shared/prompt_building.py`
  Contains prompt and message builders
- `shared/provider_runtime.py`
  Contains the shared-to-current-active-provider runtime adapter layer
- `shared/provider_registry.py`
  Contains active provider registry and capability runtime
- `shared/orchestration/`
  Contains cross-provider translation orchestration, fallback, and formula segment routing
- Top-level `llm/`
  Retains stable aggregation entry points and a small number of top-level shared logic modules

## Current Layering

- Provider-specific
  - `providers/deepseek/client.py`
  - `providers/deepseek/translation_client.py`
- Shared common layer
  - `shared/control_context.py`
  - `shared/cache.py`
  - `shared/prompt_building.py`
  - `shared/provider_registry.py`
  - `shared/provider_runtime.py`
  - `shared/structured_models.py`
  - `shared/structured_output.py`
  - `shared/structured_parsers.py`
- Shared orchestration layer
  - `shared/orchestration/README.md`
  - `shared/orchestration/fallbacks.py`
  - `shared/orchestration/batched_plain.py`
  - `shared/orchestration/direct_typst.py`
  - `shared/orchestration/direct_typst_long_text.py`
  - `shared/orchestration/direct_typst_salvage.py`
  - `shared/orchestration/heavy_formula.py`
  - `shared/orchestration/plain_text_validation.py`
  - `shared/orchestration/sentence_level.py`
  - `shared/orchestration/transport.py`
  - `shared/orchestration/keep_origin.py`
  - `shared/orchestration/metadata.py`
  - `shared/orchestration/common.py`
  - `shared/orchestration/segment_routing.py`
  - `shared/orchestration/retrying_translator.py`
- Common logic
  - `placeholder_guard.py`
  - `domain_context.py`

## Stable Entry Points and Compatibility Entry Points

- Stable aggregation entry points
  - `llm/__init__.py`
  - `providers/deepseek/__init__.py`
  - `shared/__init__.py`
  - `shared/orchestration/__init__.py`

## Provider Runtime Layering

- `providers/<provider>/`
  Only cares about provider-specific transport, defaults, and the provider's own translation details
- `shared/provider_registry.py`
  Assembles provider-specific capabilities into `TranslationProviderRuntime`
- `shared/provider_runtime.py`
  Exposes a stable alias for the "currently active provider" to the business layer and orchestration layer
- Business layer
  By default only depends on `shared/provider_runtime.py`, does not directly import `providers/deepseek/*`

## Key Call Chains

- Main translation chain:
  `workflow/translation_workflow.py`
  -> `services.translation.llm.translate_batch`
  -> `shared/orchestration/retrying_translator.py`
  -> `providers/deepseek/translation_client.py`
  -> `providers/deepseek/client.py`
- Domain hint chain:
  `domain_context.py`
  -> `shared/control_context.py`
  -> `providers/deepseek/client.py`
- Formula degradation chain:
  `shared/orchestration/retrying_translator.py`
  -> `shared/orchestration/segment_routing.py`
  -> `shared/orchestration/fallbacks.py`
  -> `placeholder_guard.py`

## Troubleshooting Entry Points

- Placeholder anomalies, keep-origin degradation:
  `placeholder_guard.py`
- Batch retry, single-item degradation:
  `shared/orchestration/retrying_translator.py`
  `shared/orchestration/fallbacks.py`
  `shared/orchestration/README.md`
- Structured output parsing failures:
  `shared/structured_output.py`
  `shared/structured_parsers.py`
- Debug and replay:
  `backend/scripts/devtools/replay_translation_item.py`
  `backend/scripts/devtools/tests/translation/`

## Future Conventions

- When adding a new provider, prioritize adding implementations under `providers/<provider>/`
- When adding a new provider, also register the runtime in `shared/provider_registry.py`
- Shared capabilities should be placed in `shared/` by default
- Top-level `llm/` should only retain stable aggregation entry points and a small number of top-level shared modules; do not continue to pile on provider-specific exceptions
- Business code should by default access default models, base_url, api_key resolution, and generic chat transport through `shared/provider_runtime.py`
