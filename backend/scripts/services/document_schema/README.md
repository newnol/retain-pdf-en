# Document Schema Description

`scripts/services/document_schema/` defines the unified intermediate document structure.

The currently formally used:

- Schema name: `normalized_document_v1`
- Schema version: `1.1`
- Default filename: `document.v1.json`
- Default report filename: `document.v1.report.json`
- Machine-readable schema: `document.v1.schema.json`
- Python validator: `validator.py`

This JSON is now the standard OCR input for the translation/rendering main chain.

## Stage Boundary

The `document_schema` layer is only responsible for the OCR/Normalize stage handoff; it does not take on translation or rendering responsibilities toward downstream.

Formal input and output are fixed as:

- Input:
  Provider raw OCR payload, provider raw file directory, necessary context from the source PDF
- Output:
  `document.v1.json` and `document.v1.report.json`

Explicitly not responsible for:

- Translation strategy, terminology control, and translation artifact persistence
- Layout overlay, Typst compilation, and final PDF output
- Continuing to expose provider-private fields as the main contract in downstream stages

Stable handoff point:

- When the OCR stage ends here, downstream should only depend on `document.v1.json`
- `document.v1.report.json` only serves validation, troubleshooting, and compatibility summaries; it is not the main translation/rendering input
- Provider raw traces are retained for tracing, but are prohibited from becoming translation/rendering main logic dependencies

## Field Layering Specification

Fields in `document.v1` should no longer be treated as "a jumble." The current convention splits into three layers:

1. Core structure layer
2. Common trace layer
3. Provider raw trace layer

### 1. Core Structure Layer

This layer contains stable fields that translation, rendering, and strategy code can directly depend on.

Top-level:

- `schema`
- `schema_version`
- `document_id`
- `doc_id`
- `source.provider`
- `page_count`
- `pages`
- `assets`
- `derived`
- `markers`

Page-level:

- `page`
- `page_index`
- `width`
- `height`
- `unit`
- `blocks`

Block-level:

- `block_id`
- `page_index`
- `order`
- `reading_order`
- `geometry`
- `content`
- `layout_role`
- `semantic_role`
- `structure_role`
- `policy`
- `provenance`
- `type`
- `sub_type`
- `bbox`
- `text`
- `lines`
- `segments`
- `tags`
- `derived`
- `continuation_hint`

Principles:

- Downstream main logic should preferentially only read this layer
- When integrating a new provider, the first goal is to stably map raw JSON to this layer first
- The new main chain preferentially consumes `geometry/content/layout_role/semantic_role/structure_role/policy/provenance`
- Legacy `type/sub_type/bbox/text/lines/segments` are currently retained as a compatibility layer; semantics are no longer being extended
- The default translation chain should no longer reverse-infer body text from `type/sub_type/tags/derived/source.raw_*`
- `policy.translate` is the formal entry point for whether body text enters the translation chain

### 2. Common Trace Layer

This layer is not a hard dependency of the main chain, but multiple providers are recommended to align toward this set of fields.

Currently existing and reusable fields include:

- `content_is_rich`
- `content_format`
- `content_length`
- `content_line_count`
- `asset_key`
- `asset_url`
- `asset_resolved`
- `markdown_match_text`
- `markdown_match_found`
- `markdown_match_count`

Principles:

- This layer mainly serves troubleshooting, tuning, and future enhancement features
- It can be cautiously read by strategy code
- It should not replace `type/sub_type/tags/derived`

### 3. Provider Raw Trace Layer

This layer is only for tracing and troubleshooting; downstream business logic is prohibited from directly depending on it.

Including but not limited to:

- `source.raw_*`
- `metadata.raw_*`
- `layout_det_*`
- Provider original id/path/score/label
- Paddle's `model_settings`
- Paddle's `layout_det_res`
- Paddle's original `markdown.images`
- Other providers' original detection fields

Principles:

- This layer can be retained comprehensively
- But it should not be treated as the unified semantic entry point
- If a field is stably provided by multiple providers in the future, consider promoting it to the "common trace layer"

### Downstream Reading Principles

Recommended order:

1. First read the core structure layer
2. Read the common trace layer when necessary
3. Only troubleshooting or provider research scripts should read the raw trace layer

In other words:

- The translation/rendering main chain preferentially uses `geometry/content/layout_role/semantic_role/structure_role/policy/provenance`
- If enhanced judgment is needed, common trace fields like `content_format` may be cautiously read
- Do not write main logic directly based on `layout_det_score`, `source.raw_type`, or `metadata.raw_*`

## Design Goals

- Isolate upstream OCR provider raw structures in the adapter layer
- Provide a stable intermediate layer contract for translation, rendering, strategy, and API
- Avoid over-design; do not force hard-to-stably-judge OCR semantics into the main type system

## Current Chain

Main chain conventions:

1. Upstream provider first outputs its own raw results
2. Adapter converts raw results into `normalized_document_v1`
3. `services/translation` and `services/rendering` only work around this unified structure

Using the current provider implementation as an example:

- Raw OCR: `ocr/unpacked/layout.json`
- Unified intermediate layer: `ocr/normalized/document.v1.json`
- Normalization report: `ocr/normalized/document.v1.report.json`
- Stage spec: `specs/normalize.spec.json` (`normalize.stage.v1`)

Note:

- Raw `layout.json` is retained for adapters, debugging, and tracing
- The translation/rendering main chain preferentially consumes `document.v1.json`
- `document.v1.report.json` is used for adapter detection, default value filling, and schema validation summary review
- The normalize worker called by the Rust main workflow now requires `--spec <job_root/specs/normalize.spec.json>`
- If you are only locally manually verifying schema/adapter, you should use `scripts/entrypoints/validate_document_schema.py`

## Adapter Conventions

Provider raw OCR should not directly enter the translation/rendering main chain.

The unified entry point is at:

- `services/document_schema/adapters.py`

Current adapter interfaces:

- `detect_ocr_provider(payload)`
- `adapt_payload_to_document_v1(...)`
- `adapt_payload_to_document_v1_with_report(...)`
- `adapt_path_to_document_v1(...)`
- `adapt_path_to_document_v1_with_report(...)`
- `register_ocr_adapter(...)`

Shared convention entry points:

- `services/document_schema/providers.py`
  Stable OCR provider identifier constants; adapter, fixture registry, and regression scripts preferentially share this layer
- `services/pipeline_shared/`
  Main chain shared `pipeline_summary.json`, stdout labels, JSON IO, and source-json selection rules
- `services/mineru/contracts.py`
  Only retains MinerU provider-private raw filename and directory name conventions

Current formal provider adapters:

- `mineru -> document.v1`
- `mineru_content_list_v2 -> document.v1`
- `generic_flat_ocr -> document.v1`
- `paddle -> document.v1`

## Provider Adapter Layering

The current adapters are split into two layers:

1. Common skeleton
2. Provider assembly layer

The common skeleton is located at:

- `services/document_schema/provider_adapters/common/`

Currently contains:

- `document_builder.py`
  Responsible for unified top-level `document.v1` assembly
- `page_builder.py`
  Responsible for unified page record assembly
- `block_builder.py`
  Responsible for unified block record assembly
- `normalize.py`
  Responsible for `bbox/polygon/segments/lines` and other common normalization helpers
- `relations.py`
  Provides the in-page relationship skeleton for "inferring current block semantics based on the previous anchor"
- `specs.py`
  Defines the intermediate block/page spec that providers first land on internally

Principles:

- `common/` does not directly read a specific OCR provider's raw field names
- `common/` only receives intermediate specs that have already been parsed by the provider
- This way, when integrating new OCR in the future, you only need to convert raw JSON to specs yourself, then hand them to the common builder

The provider assembly layer is located at:

- `services/document_schema/provider_adapters/`

Where:

- `paddle/`
  Uses a directory-based split, responsible for parsing Paddle raw `layoutParsingResults` into common specs
  Currently further subdivided into reader, relations, page trace, and rich-content trace.
  The reader layer now internally converges interfaces via page/block context, no longer scattering markdown/layout trace parameters.
- `mineru_content_list_v2_adapter.py`
  Already integrated with the common builder, but not yet fully directory-based like Paddle
- `generic_flat_ocr_adapter.py`
  Currently still the thinnest passthrough adapter
- `mineru`
  Main chain still resides in `services/mineru/document_v1.py`; currently not in scope for this round of generalization

In other words, when extending OCR providers in the future, the preferred goal is not to continue piling up "large adapter files," but rather:

1. Provider raw JSON -> provider internal spec
2. Spec -> `common` builder
3. Adapter registered in `adapters.py`
4. Fixture connected to regression

Paddle's current rich-content trace has also been further split into three layers:

- Content profile: `content_profile.py`
- Asset references: `asset_links.py`
- Markdown light matching: `markdown_match.py`

`rich_content.py` only retains the aggregation entry point, no longer carrying specific parsing details.

Note:

- Paddle's `content_format / asset_* / markdown_match_*` currently fall into the "common trace layer"
- Paddle's `layout_det_* / model_settings / markdown.images` currently fall into the "provider raw trace layer"

New providers can reference:

- `services/document_schema/provider_adapters/provider_adapter_template.py`
- `services/document_schema/provider_adapters/paddle/`

When adding new OCR providers in the future, the correct approach is:

1. Add a new provider adapter
2. Convert raw JSON into `normalized_document_v1`
3. Perform schema validation immediately after adapter output
4. Downstream continues to only consume `document.v1.json`

Recommended integration order:

1. First clarify field placement rules
   That is, first decide which fields enter `content/layout_role/semantic_role/structure_role/policy`, which only remain in `tags/derived`, and which only remain in `metadata/source`.
2. Prepare a minimal raw fixture
   Place it in `scripts/devtools/tests/document_schema/fixtures/`.
3. Write and register the adapter
   Preferentially reuse shared provider constants from `providers.py`; do not each write a raw string in the adapter, fixture, and regression entry point.
   If the raw structure is relatively complex, preferentially split by responsibility such as `payload_reader / block_labels / relations / content_extract / trace`, rather than continuing to pile up single files.
4. Register the fixture in `fixtures/registry.py`
5. Run `regression_check.py`
   Let detector, adapt, validation, and extractor smoke pass in one go.

## Check Entry Points

Long-term check entry points:

- `scripts/entrypoints/validate_document_schema.py`
- `scripts/devtools/tests/document_schema/regression_check.py`

Now supports two usage modes:

1. Directly validate an already-generated `document.v1.json`
2. Execute `adapter -> defaults -> validation` on raw OCR JSON and output a report

Examples:

```bash
python scripts/entrypoints/validate_document_schema.py output/.../ocr/normalized/document.v1.json
python scripts/entrypoints/validate_document_schema.py output/.../ocr/unpacked/layout.json --adapt --document-id demo --write-report /tmp/document-schema-report.json
```

The report currently includes:

- Input path
- Adapter/provider detection result
- Default value filling statistics
- Schema validation summary

`validate_document_schema.py --write-report` current conventions:

- When `mode = "adapt"`:
  - `input_path`
  - `normalization`
  - `normalization_summary`
  - `validation`
- When `mode = "validate"`:
  - `input_path`
  - `validation`

In other words:

- For complete adapter / defaults / detection details, look at `normalization`
- For stable lightweight summary, prefer looking at `normalization_summary`
- For top-level validation results, look at `validation`

Unified consumption entry point:

- `services/document_schema/reporting.py`
- `load_normalization_report(path)`
- `build_normalization_summary(report)`

Conventions:

- If the Python side only wants to display provider / detected provider / pages observed / blocks observed / defaulted field counts / validation summary, preferentially use these two helpers
- Do not each rewrite `report['defaults']['pages_seen']` style reads in `mineru/summary.py`, troubleshooting scripts, or subsequent API layers
- When the full original report is needed, use the report dict directly; the original fields are not prevented from being retained

Regression smoke check:

```bash
python scripts/devtools/tests/document_schema/regression_check.py
python scripts/devtools/tests/document_schema/regression_check.py --write-report /tmp/document-schema-regression.json
```

This regression script now is not simply printing logs; it hard-validates:

- The adapter registry must contain current formal providers
- Current `document.v1.json` must pass schema validation
- Raw layout / `content_list_v2.json` / generic fixture / paddle fixture must all be auto-detected, adapted, and pass schema validation again
- Paths with explicitly specified providers must also be usable, preventing "auto-detection passes but explicit calls degrade"
- Providers like Paddle also need additional semantic assertions, at least locking:
  - `header/footer`
  - `image_caption/table_caption`
  - `table_footnote`
  - `display_formula -> formula segment`

Recommendations:

- New providers should add at least one "provider semantic assertion"
- Do not only look at `pages / blocks`; otherwise, classification regression can easily be missed

## Default Value Filling Rules

The current version of `document.v1.json` produced by the adapter will have stable default values uniformly filled before entering the main chain.

### Hard Fields

These fields cannot be automatically guessed; when missing, they should be treated as structural errors:

- Document-level:
  - `schema`
  - `schema_version`
  - `document_id`
  - `source`
  - `pages`
- Page-level:
  - `width`
  - `height`
  - `unit`
  - `blocks`
- Block-level:
  - `block_id`
  - `geometry`
  - `content`
  - `layout_role`
  - `semantic_role`
  - `structure_role`
  - `policy`
  - `provenance`

### Soft Fields

These fields allow the default value consolidation layer to fill in defaults:

- Document-level:
  - `derived -> {}`
  - `markers -> {}`
  - `page_count -> len(pages)`
- Page-level:
  - `page_index -> current page index`
- Block-level:
  - `page_index -> current page index`
  - `order -> current block order`
  - `reading_order -> order`
  - `geometry -> {bbox:[0,0,0,0]}`
  - `content -> {kind:"unknown", text:""}`
  - `layout_role -> "unknown"`
  - `semantic_role -> "unknown"`
  - `structure_role -> ""`
  - `policy -> {translate:false, translate_reason:"missing_contract_fields"}`
  - `provenance -> {provider:"", raw_label:"", raw_sub_type:"", raw_bbox:[0,0,0,0], raw_path:""}`
  - `tags -> []`
  - `derived -> {role:"", by:"", confidence:0.0}`
  - `continuation_hint -> {source:"", group_id:"", role:"", scope:"", reading_order:-1, confidence:0.0}`
  - `metadata -> {}`
  - `source -> {}`

Principles:

- The default value consolidation layer only fills fields with "clearly stable defaults"
- The default value consolidation layer only fills empty slots; the formal semantic scope is still consolidated by `contract_v1.py`
- True structural errors are still intercepted by the validator

## Top-level Structure

Top-level fields:

- `schema: str`
  Fixed as `normalized_document_v1`
- `schema_version: str`
  Current latest version is `1.1`
  The validator only accepts the current version `1.1`
- `document_id: str`
  Document identifier, typically corresponding to the job or input document
- `source: dict`
  Top-level source information, recording provider and original file
- `page_count: int`
  Page count
- `pages: list[dict]`
  Page list
- `derived: dict`
  Document-level derivation notes or post-processing remarks
- `markers: dict`
  Document-level stable markers, such as the starting point of references

Example:

```json
{
  "schema": "normalized_document_v1",
  "schema_version": "1.1",
  "document_id": "20260330145544-14ab20",
  "source": {},
  "page_count": 1,
  "pages": [],
  "derived": {},
  "markers": {}
}
```

## Page Structure

Each page object currently contains:

- `page_index: int`
  Starting from `0`
- `width: number`
  Page width
- `height: number`
  Page height
- `unit: str`
  Currently uses `pt`
- `blocks: list[dict]`
  Page block list

Constraints:

- `pages[i].page_index` should match the array order
- Block order within `blocks` is explicitly specified by `order`

## Block Structure

Each block currently contains:

- `block_id: str`
  Stable block id, e.g., `p001-b0000`
- `page_index: int`
  Containing page
- `order: int`
  In-page order
- `reading_order: int`
  Normalized reading order
- `geometry: dict`
  Stable geometry field, currently at least contains `bbox`
- `content: dict`
  Stable content field, currently at least contains `kind` and `text`
- `layout_role: str`
  Explicit layout role
- `semantic_role: str`
  Explicit semantic role
- `structure_role: str`
  Explicit body structure role
- `policy: dict`
  Explicit execution policy, currently at least contains `translate`
- `provenance: dict`
  Provider original label and tracing information
- `type: str`
  Compatibility main type
- `sub_type: str`
  Compatibility sub-type
- `bbox: [x0, y0, x1, y1]`
  Compatibility block-level bounding box
- `text: str`
  Block's normalized plain text
- `lines: list[dict]`
  Line-level structure
- `segments: list[dict]`
  Span/segment flat structure
- `tags: list[str]`
  Lightweight derived markers
- `derived: dict`
  Stronger derived semantic conclusions
- `continuation_hint: dict`
  Paragraph continuity hints from the provider or upstream structure layer
- `metadata: dict`
  Debug/mapping metadata
- `source: dict`
  Provider original source information

## `continuation_hint` Convention

`continuation_hint` is a block-level stable field, used to carry hints from the OCR provider or subsequent structure layer indicating "these blocks originally belong to the same paragraph."

Current fields:

- `source`
  Currently retained as `"" | "provider"`
- `group_id`
  Stable id for the same continuity group
- `role`
  `"" | "single" | "head" | "middle" | "tail"`
- `scope`
  `"" | "intra_page" | "cross_page"`
- `reading_order`
  Reading order within the group as given by the provider; `-1` when unknown
- `confidence`
  `0.0 ~ 1.0`

Current behavior constraints:

- `document.v1` is only responsible for stably persisting the hints; it does not hard-code a specific provider's private fields at the schema layer
- The translation main chain currently preferentially consumes hints with `source="provider"` and `scope="intra_page"`
- `cross_page` hints are only consumed at the translation layer when controlled conditions are met (adjacent pages, clear order, safe layout zone boundaries, sufficient text length); the schema layer is only responsible for defining and preserving the contract
- New OCR providers that can also stably produce continuity group information should preferentially write to this field, rather than directly exposing private raw fields to downstream

## `type / sub_type` Convention

`type / sub_type` only carries stable structure, and does not force high-level semantics that OCR can rarely stably determine.

Current main types:

- `text`
- `formula`
- `image`
- `table`
- `code`
- `unknown`

Currently used `sub_type` examples:

- `title`
- `body`
- `metadata`
- `header`
- `footer`
- `page_number`
- `footnote`
- `display_formula`
- `figure`
- `table_body`
- `code_block`

Rules:

- Structures that can be stably mapped should preferentially enter `type / sub_type`
- Unstable high-level semantics should not directly extend the main type system
- First ask "Is this structure, or semantic judgment?"
- First ask "Can it likely be stably placed across providers?"

Examples:

- Body paragraph:
  - `type = "text"`
  - `sub_type = "body"`
- Header:
  - `type = "text"`
  - `sub_type = "header"`
- Display formula:
  - `type = "formula"`
  - `sub_type = "display_formula"`
- Code block:
  - `type = "code"`
  - `sub_type = "code_block"`
- OCR cannot stably subdivide but can confirm it is text:
  - `type = "text"`
  - `sub_type = "metadata"` or `body`

Counter-examples:

- Do not stuff `caption` directly into `type`
- Do not stuff `reference_entry` directly into `sub_type`
- Do not create a new main type just because a single provider has a special field

When integrating a provider, you can use the following judgment:

- Layout structures like `text/header/footer/page_number/footnote` are stable; enter `type / sub_type`
- Block-level structures like `formula/display_formula`, `image/figure`, `table/table_body`, `code/code_block` are stable; enter `type / sub_type`
- Items like `image_caption/table_caption/table_footnote/reference_entry/reference_heading` are more like "semantic tags"; prefer entering `tags`
- If local rules or subsequent LLMs have made a stronger conclusion about a block, write it into `derived.role`
- Content like `author/date/affiliation/doi` that OCR often cannot stably separate and provider differences are large should not be expanded into new stable `sub_type` by default

## `tags / markers / derived` Layering

This is the most important design convention of the current schema.

### `tags`

`tags` are block-level lightweight markers.

Suitable for:

- `caption`
- `image_caption`
- `table_caption`
- `table_footnote`
- `image_footnote`
- `reference_heading`
- `reference_entry`
- `reference_zone`

Characteristics:

- Lightweight
- Can be combined in parallel
- Suitable for fast rule-based consumption

Examples suitable for `tags`:

- A block is simultaneously a `caption` and can be further subdivided into `image_caption`
- A block has entered the references zone and can be additionally tagged with `reference_zone`

Examples not suitable for `tags`:

- Stable structures like body / header / footer
- Provider temporary debug fields

### `markers`

`markers` are document-level stable markers.

Currently in use:

- `reference_start`

Example:

```json
{
  "reference_start": {
    "page_index": 10,
    "block_id": "p011-b0021",
    "order": 21
  }
}
```

Examples suitable for `markers`:

- Document-level `reference_start`

Examples not suitable for `markers`:

- A single block's semantics
- Debug information that is only temporarily meaningful for a specific page

### `derived`

`derived` is for stronger derived semantic conclusions.

Block-level `derived` current structure:

- `role: str`
- `by: str`
- `confidence: float`

Examples:

- `role = "caption"`
- `role = "reference_heading"`
- `role = "reference_entry"`

Significance of `derived`:

- Allows provider rules to write
- Allows local rules to write
- Subsequently also allows LLMs to write

In other words, `derived` is the main entry point for continuing to evolve the semantic layer.

Examples suitable for `derived`:

- `role = "caption"`
- `role = "reference_heading"`
- `role = "reference_entry"`
- `role = "algorithm"`, but the premise is that this conclusion comes from local rules or higher-level judgment, rather than forcibly copying provider raw fields into the main contract

Examples not suitable for `derived`:

- Provider's original `raw_type`
- Structures that can be stably placed directly into `type / sub_type`
- Temporary markers meaningful only to a specific local script

A practical judgment:

- If downstream logic wants to "quickly filter a batch of blocks," prefer `tags`
- If downstream logic wants to "treat this block as a certain explicit semantic object," prefer `derived.role`
- If this is layout ground truth, do not put it in `tags/derived`; directly place it in `type / sub_type`

## `metadata` and `source` Boundaries

### `metadata`

`metadata` stores local mapping, debugging, and structure tracing information.

Currently used examples:

- `raw_index`
- `raw_angle`
- `raw_sub_type`
- `parent_block_id`

Characteristics:

- Tends toward local implementation
- Tends toward debugging/tracing
- Not recommended to bind too much business logic at the upper layer

### `source`

`source` stores provider source information.

Currently used examples:

- `provider`
- `raw_page_index`
- `raw_path`
- `raw_type`
- `raw_sub_type`
- `raw_bbox`
- `raw_text_excerpt`

Characteristics:

- Retains original mapping
- Facilitates tracing provider output
- Should not become a long-term dependency of translation/rendering main logic

## Line and Segment Structure

`lines[*]` current fields:

- `bbox`
- `spans`

`lines[*].spans[*]` current fields:

- `type`
- `raw_type`
- `text`
- `bbox`
- `score`

`segments[*]` current fields:

- `type`
- `raw_type`
- `text`
- `bbox`
- `score`

Conventions:

- `segments` is a flat sequence within a block, facilitating translation and formula protection
- `lines` retains line-level structure, facilitating typesetting and local analysis
- Inline formulas are not treated as the block main type; they are retained in `segments/spans`

## Stable Contracts vs Non-stable Fields

Fields currently recommended as stable contracts:

- Top-level: `schema`, `schema_version`, `document_id`, `page_count`, `pages`, `markers`
- Page: `page_index`, `width`, `height`, `unit`, `blocks`
- Block: `block_id`, `page_index`, `order`, `type`, `sub_type`, `bbox`, `text`, `lines`, `segments`, `tags`, `derived`, `continuation_hint`, `metadata`, `source`
- `derived.role/by/confidence`

Parts currently not recommended for strong external binding:

- `metadata` internal details
- `source.raw_*` specific field sets
- Certain provider-specific `tags`

In other words:

- Upper-layer business should preferentially depend on `type / sub_type / tags / derived / markers`
- Do not treat provider raw fields as the main contract again

## Version Evolution Principles

`v1` is currently usable, but it is not the "once and for all" ultimate version.

Future evolution principles:

- Small changes should preferentially add fields; do not easily change semantics
- If existing stable contracts must be broken, upgrade to `v2`
- Provider adapters are responsible for absorbing upstream changes; changes should not be directly leaked to the main chain

### Current Conclusion

At this stage, starting `document.v2` is not recommended.

Reasons:

- The current main chain has just completed the consolidation of `raw -> adapter -> defaults -> validator -> document.v1`; the primary goal is to polish and stabilize `v1`
- Most existing new requirements still belong to adapter extensions, `tags/derived/markers` semantic solidification, and regression coverage enhancement; they have not reached the point of requiring contract breaking
- If `v2` is started prematurely, it will simultaneously pull in provider integration, translation main chain, rendering main chain, and legacy task compatibility; the benefit does not outweigh stabilizing `v1` first

### Only Consider Starting `v2` When These Conditions Are Met

At least meet one category:

1. `v1`'s stable field definitions must be entirely replaced.
   For example:
   - The `type / sub_type` system needs a major overhaul
   - The basic organization of `lines / segments` needs to change
   - The responsibility boundaries of `tags / derived / markers` need to be entirely redrawn

2. Long-term cross-provider common needs emerge that cannot be expressed with "adding fields."
   For example:
   - Multiple OCR providers stably produce certain structures that `v1` cannot losslessly carry
   - Existing field semantics have forced downstream to maintain compatibility branches continuously

3. Legacy compatibility costs clearly begin to exceed upgrade costs.
   For example:
   - The default value consolidation layer increasingly resembles a "semi-rewrite"
   - The validator and main chain need to maintain two conflicting sets of assumptions long-term

### Default Strategy Before That

- Prioritize expanding adapters, not expanding main chain contracts
- Prioritize supplementing `tags / derived / markers` semantics; do not easily change `type / sub_type`
- Prioritize appending machine-readable schema and regression samples; do not first upgrade the version number

## Current Most Important Implementation Principles

- The main chain preferentially centers around `document.v1.json`
- The adapter layer is responsible for `raw -> normalized`
- The business layer preferentially consumes:
  - `type / sub_type`
  - `tags`
  - `derived`
  - `markers`

Do not treat MinerU's original JSON structure as the translation/rendering main contract anymore.

## Collaboration Rules

This layer is the most important protocol boundary between OCR and downstream modules.

- `document.v1.json` is the formal contract that translation/rendering can directly depend on
- `document.v1.report.json` is for validation, troubleshooting, and compatibility summaries; it is not the downstream main input
- When adding new fields, preferentially supplement the core structure layer or common trace layer; do not let downstream long-term depend on raw trace
- If modifying `document.v1` structure, field semantics, or default filename, you must simultaneously update the adapter, README, fixtures, schema validation, and downstream compatibility tests
- Translation/rendering owners, if they need more semantics, should first define them clearly here before entering their respective module implementations; they cannot directly bypass this layer to read provider-private fields
