# Pipeline Shared Notes

`services/pipeline_shared/` contains cross-stage shared, generic protocol layers that don't belong to any single provider.

It currently mainly hosts three types of things:

- `contracts.py`
  Shared stdout labels and summary filenames used by provider/translate/render workers.
- `io.py`
  Neutral JSON persistence helpers.
- `source_json.py`
  Neutral rules for how the main pipeline selects formal input between raw provider layout and normalized document.
- `summary.py`
  Shared pipeline summary generation and printing logic for main pipeline workers.

Design boundaries:

- Only stage-level shared protocols are placed here; no provider-specific semantics like MinerU or Paddle.
- Only generic capabilities needed by the entire main pipeline are placed here; no translation strategy, rendering implementation, or OCR adaptation details.
- `services/mineru/` may continue to retain compatibility shells, but new main pipeline dependencies should preferentially point here.

The goal of this layer is not to add another level of abstraction, but to consolidate capabilities that were originally hung under `services/mineru/*` but were actually shared across the entire pipeline into a neutral module, facilitating further evolution of the backend into a "modular monolith."
