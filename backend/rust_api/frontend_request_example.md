# Frontend Request Examples

This document is for frontend integration, providing the most common call sequences, request headers, request bodies, and example code.

Use alongside the main documentation:

- [Rust API README](/home/wxyhgk/tmp/Code/backend/rust_api/README.md)
- [API_SPEC](/home/wxyhgk/tmp/Code/backend/rust_api/API_SPEC.md)
- [CURRENT_API_MAP](/home/wxyhgk/tmp/Code/backend/rust_api/CURRENT_API_MAP.md)

Documentation conventions:

- This document is a frontend integration example, not the protocol specification source; the formal specification is `API_SPEC.md`
- Frontend request examples are unified based on the grouped formal request structure
- Legacy flat fields have been removed and are no longer accepted
- Frontend only needs to care about interface contracts, not Rust internal module names

## 1. The 5 Values You Must Prepare

When calling the Rust API, the frontend needs to prepare at least the following values:

1. `X-API-Key`
2. `mineru_token`
3. `base_url`
4. `api_key`
5. `model`

Meanings:

- `X-API-Key`: Your own Rust backend access key
- `mineru_token`: MinerU's API Key
- `base_url`: OpenAI-compatible URL of the model service
- `api_key`: API Key of the model service
- `model`: Model name

Optional but recommended fields for frontend support:

- `translation.math_mode`: Formula translation mode
  - `direct_typst`: Default mode, directly asks the model to output body text + `$...$` math
  - `placeholder`: Conservative mode for compatibility with the legacy formula protection chain

## 2. Call Sequence

Recommended frontend sequence:

1. Upload PDF
2. Create task using the `upload_id` returned from upload
3. Poll task status
4. After success, download PDF / Markdown / Bundle

## 3. Upload PDF

Request:

```http
POST /api/v1/uploads
X-API-Key: your-rust-api-key
Content-Type: multipart/form-data
```

Frontend example:

```ts
async function uploadPdf(file: File, backendKey: string, developerMode = false) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("developer_mode", String(developerMode));

  const resp = await fetch("http://127.0.0.1:41000/api/v1/uploads", {
    method: "POST",
    headers: {
      "X-API-Key": backendKey,
    },
    body: formData,
  });

  const data = await resp.json();
  if (!resp.ok || data.code !== 0) {
    throw new Error(data.message || "upload failed");
  }
  return data.data;
}
```

After success you will get:

```json
{
  "upload_id": "20260327-abc123",
  "filename": "paper.pdf",
  "bytes": 1832451,
  "page_count": 18,
  "uploaded_at": "2026-03-27T18:20:31+08:00"
}
```

Upload limit notes:

- The current backend does not additionally limit PDF size and page count by default
- If the deployer has configured `RUST_API_UPLOAD_MAX_BYTES` / `RUST_API_UPLOAD_MAX_PAGES`, use the actual server error received by the frontend as the reference

## 4. Create Task

Request:

```http
POST /api/v1/jobs
X-API-Key: your-rust-api-key
Content-Type: application/json
```

Notes:

- `workflow: "book"` is the current formal protocol value for the complete main pipeline
- OCR provider selection is based on `ocr.provider`, not `workflow`
- If you only want to run OCR-only, use `POST /api/v1/ocr/jobs`; do not pass `workflow="ocr"` to `/api/v1/jobs`
- When calling locally for manual use, prefer the neutral entry name `run_provider_case.py`
- If the input is already OCR JSON + PDF, prefer using `run_document_flow.py`
- If you only want to run OCR-only, prefer using `run_provider_ocr.py`

### 4.1 DeepSeek Example

Recommended request body:

```json
{
  "workflow": "book",
  "source": {
    "upload_id": "20260327-abc123"
  },
  "ocr": {
    "provider": "mineru",
    "mineru_token": "your-mineru-api-key"
  },
  "translation": {
    "base_url": "https://api.deepseek.com/v1",
    "api_key": "your-deepseek-api-key",
    "model": "deepseek-v4-flash",
    "mode": "sci",
    "math_mode": "direct_typst",
    "workers": 50,
    "batch_size": 1,
    "glossary_id": "glossary-20260411-abc123",
    "glossary_entries": [
      {"source": "band gap", "target": "band gap", "note": "materials"}
    ]
  },
  "render": {
    "render_mode": "auto"
  }
}
```

### 4.2 OpenAI-Compatible Endpoint Example

```json
{
  "workflow": "book",
  "source": {
    "upload_id": "20260327-abc123"
  },
  "ocr": {
    "provider": "mineru",
    "mineru_token": "your-mineru-api-key"
  },
  "translation": {
    "base_url": "http://127.0.0.1:10001/v1",
    "api_key": "your-openai-compatible-api-key",
    "model": "Q3.5-turbo",
    "mode": "precise",
    "math_mode": "direct_typst",
    "workers": 4,
    "batch_size": 1,
    "glossary_id": "",
    "glossary_entries": []
  },
  "render": {
    "render_mode": "auto"
  }
}
```

Frontend example:

```ts
type CreateJobPayload = {
  workflow?: "book" | "translate" | "render";
  source: {
    upload_id: string;
  };
  ocr: {
    provider?: "mineru" | "paddle";
    mineru_token: string;
    page_ranges?: string;
  };
  translation: {
    base_url: string;
    api_key: string;
    model: string;
    mode?: "sci" | "precise";
    math_mode?: "placeholder" | "direct_typst";
    workers?: number;
    batch_size?: number;
    rule_profile_name?: string;
    custom_rules_text?: string;
    glossary_id?: string;
    glossary_entries?: Array<{
      source: string;
      target: string;
      note?: string;
    }>;
  };
  render?: {
    render_mode?: string;
    compile_workers?: number;
  };
};

async function createJob(payload: CreateJobPayload, backendKey: string) {
  const resp = await fetch("http://127.0.0.1:41000/api/v1/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": backendKey,
    },
    body: JSON.stringify(payload),
  });

  const data = await resp.json();
  if (!resp.ok || data.code !== 0) {
    throw new Error(data.message || "create job failed");
  }
  return data.data;
}
```

### 4.3 Current Mandatory Validation

`POST /api/v1/jobs` currently enforces validation on:

- `source.upload_id`
- `ocr.mineru_token`
- `translation.base_url`
- `translation.api_key`
- `translation.model`

Additionally:

- `base_url` must start with `http://` or `https://`

Current `translation.math_mode` conventions:

- Defaults to `direct_typst` when not provided
- If the frontend wants to expose an experimental toggle, the recommended label is "Formula Direct Output Experimental Mode"
- `direct_typst` only affects the formula processing chain in the translation stage, not the rendering endpoint call method

### 4.4 How to Pass Glossary

Recommended approach:

- When the frontend maintains a "named glossary" list, first call `POST /api/v1/glossaries` to save it, then only pass `translation.glossary_id` in the task
- If it's just a one-time task with temporary terms, directly pass `translation.glossary_entries`
- If the user uploads Excel, the frontend should parse it into JSON first; the backend does not directly parse Excel
- If the frontend only has CSV text, it can first call `POST /api/v1/glossaries/parse-csv` to convert to standard entries

Merge rules:

- Named glossary is the base layer
- Task-level `glossary_entries` is the override layer
- Same `source` uses the task-level entry as the authoritative value

Current behavior boundaries:

- Glossary v1 only participates in prompt injection and result statistics
- No forced text replacement after translation is performed

## 5. Poll Task Status

Request:

```http
GET /api/v1/jobs/{job_id}
X-API-Key: your-rust-api-key
```

Frontend example:

```ts
async function getJob(jobId: string, backendKey: string) {
  const resp = await fetch(`http://127.0.0.1:41000/api/v1/jobs/${jobId}`, {
    headers: {
      "X-API-Key": backendKey,
    },
  });

  const data = await resp.json();
  if (!resp.ok || data.code !== 0) {
    throw new Error(data.message || "get job failed");
  }
  return data.data;
}

async function pollJobUntilDone(jobId: string, backendKey: string) {
  while (true) {
    const job = await getJob(jobId, backendKey);
    const status = job.status;

    if (status === "succeeded" || status === "failed" || status === "canceled") {
      return job;
    }

    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}
```

The recent task list endpoint also returns protocol aggregation:

- `items[].invocation`
- `invocation_summary.stage_spec_count`
- `invocation_summary.unknown_count`

Notes:

- Do not use `progress.percent >= 90` to determine completion
- Must use `status` to determine if finished
- `queued` means the task has been created but may still be waiting for an execution slot
- The `invocation` field in task details can be directly used to display the stage spec protocol used by the current task
  - `invocation.input_protocol`
  - `invocation.stage_spec_schema_version`

## 6. Download Results

Common endpoints:

- PDF: `GET /api/v1/jobs/{job_id}/pdf`
- Markdown(JSON): `GET /api/v1/jobs/{job_id}/markdown`
- Markdown(raw): `GET /api/v1/jobs/{job_id}/markdown?raw=true`
- Bundle(zip): `GET /api/v1/jobs/{job_id}/download`

It is more recommended for the frontend to first get task details or artifact details, then use the `actions` returned by the server:

- `actions.download_pdf.url`
- `actions.open_markdown.url`
- `actions.open_markdown_raw.url`
- `actions.download_bundle.url`

## 7. Complete Frontend Example

```ts
async function runPdfTranslateFlow(file: File, config: {
  backendKey: string;
  mineruToken: string;
  modelBaseUrl: string;
  modelApiKey: string;
  model: string;
  mode?: "sci" | "precise";
  mathMode?: "placeholder" | "direct_typst";
}) {
  const upload = await uploadPdf(file, config.backendKey, false);

  const job = await createJob({
    workflow: "book",
    source: {
      upload_id: upload.upload_id,
    },
    ocr: {
      provider: "mineru",
      mineru_token: config.mineruToken,
    },
    translation: {
      base_url: config.modelBaseUrl,
      api_key: config.modelApiKey,
      model: config.model,
      mode: config.mode ?? "sci",
      math_mode: config.mathMode ?? "direct_typst",
      workers: 50,
      batch_size: 1,
    },
    render: {
      render_mode: "auto",
    },
  }, config.backendKey);

  const finalJob = await pollJobUntilDone(job.job_id, config.backendKey);

  if (finalJob.status !== "succeeded") {
    throw new Error(finalJob.stage_detail || "job failed");
  }

  return {
    jobId: finalJob.job_id,
    pdfUrl: finalJob.actions.download_pdf.url,
    markdownUrl: finalJob.actions.open_markdown.url,
    bundleUrl: finalJob.actions.download_bundle.url,
  };
}
```

## 8. Frontend Variable Naming Recommendations

It is recommended that the frontend clearly separates internal variables:

- `backendKey`: The Rust API's `X-API-Key`
- `mineruToken`: MinerU's key
- `modelBaseUrl`: Model service URL
- `modelApiKey`: Model service key
- `model`: Model name
- `mathMode`: Formula translation mode, default `direct_typst`

## 9. When to Enable `math_mode`

The current default recommendation is `direct_typst`. If the frontend wants to expose a toggle, it can be placed in advanced options, but `placeholder` should not be used as the default.

- Normal tasks: Don't pass it, or explicitly pass `direct_typst`
- Only pass `placeholder` when you want to fall back to the legacy formula protection chain
- If the frontend later wants to add a toggle, it is recommended to directly pass the string value rather than having the frontend infer whether the document "has many formulas"

This prevents confusion when integrating with multiple service providers later.
