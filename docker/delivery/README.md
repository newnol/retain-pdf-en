

**Pain Points**

Foreign-language papers, textbooks, and technical documents are information-dense, but difficult to read:

- High barrier to reading the original text, low efficiency
- Ordinary translation tools only output plain text — formulas, images, and layout basically fall apart
- Translated results are hard to organize, share, and archive

**What RetainPDF Does**

Upload a PDF, and get a Chinese translation that preserves the original layout with one click.

- Output as translated PDF, Markdown, or ZIP package — use what you need
- Operate directly from the web interface, also supports CLI and API access
- Image-based PDFs (scans, screenshots) can also be processed, not limited to editable PDFs

**Translation Effect Demo**

Ordinary SCI paper translation result:

![Ordinary SCI paper translation result](./g-1.png)

Image-based PDF translation comparison:

![Image-based PDF translation comparison](./g-2.png)

**Advantages Over Similar Solutions**

- Compared to [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate): fills the gap for image-based PDFs, inline formulas integrate more naturally with body text, and layout collapse probability is significantly lower
- Compared to closed-source solutions like Doc2X: can be self-deployed, with full control over APIs and result files; actual testing also shows better overall results
- Tested output is nearly ready-to-use without manual layout fixes


# Beginners

If you just want to get the service running, follow the steps below.

## 1. Check Your Machine Environment

Recommended environment:

- OS: `Linux` preferred, recommended `Ubuntu 22.04 / 24.04`
- CPU architecture: Current image is built for `x86_64 / amd64`, not ARM
- CPU: At least `4 cores`
- RAM: At least `8GB`, recommended `16GB` or more
- Disk: At least `10GB` free space
- Network: Needs access to Docker Hub, MinerU, and your model API

Notes:

- This project mainly consumes CPU, memory, and network; it does not require a dedicated GPU
- If your machine is a `Mac M`, Raspberry Pi, or ARM server, first confirm whether you have an `x86_64` compatible runtime environment
- For light personal use, `4 cores + 8GB` can start the service
- For multi-user concurrent use, recommend starting from `8 cores + 16GB`

## 2. Install Docker

First confirm that the following are already installed:

- `docker`
- `docker compose`

After installation, verify:

```bash
docker --version
docker compose version
```

## 3. Clone the GitHub Project

```bash
git clone https://github.com/wxyhgk/retain-pdf.git
cd retain-pdf
```

## 4. Start the Service

```bash
docker compose up -d
```

After startup, the default access address:

```text
http://127.0.0.1:40001
```

# Professional Users

## File Roles

- `docker-compose.yml`
  Docker orchestration entry point. By default, directly pulls Docker Hub images and starts `app` + `web`.
- `docker/app.env`
  Backend runtime parameters. Controls container paths, fonts, ports, concurrency, and upload limits.
- `docker/web.env`
  Docker public version frontend runtime parameters. Controls the backend key and model defaults injected into the frontend.
- `docker/auth.local.json`
  Rust API authentication whitelist. Both frontend and CLI need to use the backend key configured here to access the API.

## Common Configuration Items

### docker/auth.local.json

- `api_keys`
  List of backend keys allowed to access the Rust API. The `X-API-Key` in the frontend request header must match one of the values here.
- `max_running_jobs`
  Maximum number of concurrent tasks allowed by the backend.
- `simple_port`
  Port for the simple synchronous endpoint inside the container, default `42000`. Usually not directly exposed externally.

### docker/web.env

- `FRONT_API_BASE`
  API base address used internally by the frontend. Usually left empty to let the frontend automatically use the same-origin proxy.
- `FRONT_X_API_KEY`
  The `X-API-Key` automatically attached by the frontend to backend requests. Must match a value in `docker/auth.local.json`.
- `FRONT_OCR_PROVIDER`
  Default OCR provider for the frontend. Currently recommended to fill `paddle`, can also switch to `mineru`.
- `FRONT_PADDLE_TOKEN`
  Default Paddle token carried by the frontend. When left empty, the end user fills it in a page popup.
- `FRONT_MINERU_TOKEN`
  Default MinerU token carried by the frontend. When left empty, the end user fills it in a page popup.
- `FRONT_MODEL_API_KEY`
  Default model API key carried by the frontend. When left empty, the end user fills it in.
- `FRONT_MODEL`
  Default model name for the frontend, e.g., `deepseek-v4-flash`.
- `FRONT_BASE_URL`
  Default model service address for the frontend, e.g., `https://api.deepseek.com/v1`.

### docker/app.env

- `PROJECT_ROOT`
  Project root directory inside the container.
- `RUST_API_ROOT`
  Rust API directory inside the container.
- `RUST_API_DATA_DIR`
  Rust API runtime data directory, mainly for uploaded files, database, etc.
- `OUTPUT_ROOT`
  Task output directory.
- `PYTHON_BIN`
  Python interpreter used by the backend to call scripts.
- `TYPST_BIN`
  Path to the Typst executable.
- `RETAIN_PDF_FONT_PATH`
  Path to the default Chinese font file.
- `RETAIN_PDF_TYPST_FONT_FAMILY`
  Default Typst font family name.
- `RUST_API_PORT`
  Full API listen port inside the container, default `41000`.
- `RUST_API_SIMPLE_PORT`
  Simple synchronous endpoint listen port inside the container, default `42000`.
- `RUST_API_MAX_RUNNING_JOBS`
  Maximum concurrent running tasks.
- `RUST_API_NORMAL_MAX_BYTES`
  Normal upload size limit for the backend. Currently set to `200MB` in the delivery package.
- `RUST_API_NORMAL_MAX_PAGES`
  Normal page count limit for the backend. Currently set to `600` pages in the delivery package.

## Notes

- Current compose exposes by default:
  - `40001`: Frontend page
  - `41000`: Full Rust API
  - `42000`: Simple synchronous endpoint
- The frontend accesses the backend through a same-origin proxy; ordinary users usually don't need to manually understand `API Base`
- The current mainline frontend default OCR provider is `paddle`
- The size/page limits displayed on the page come from the current backend runtime configuration; they should no longer be understood based on the old MinerU fixed upstream limits

## Optional Defaults

If you want the frontend to carry downstream configuration by default, you can fill in:

- `FRONT_OCR_PROVIDER`
- `FRONT_PADDLE_TOKEN`
- `FRONT_MINERU_TOKEN`
- `FRONT_MODEL_API_KEY`
- `FRONT_MODEL`
- `FRONT_BASE_URL`

If left empty, the end user needs to fill them in the "API Configuration" popup at the top-right corner of the page.

## Using Your Own Image Version

You can also start like this:

```bash
APP_IMAGE=wxyhgk/retainpdf-app:latest \
WEB_IMAGE=wxyhgk/retainpdf-web:latest \
docker compose up -d
```

# Developers

If you want to call the API directly via CLI instead of through the frontend page, you can use the methods below.

First, define some variables:

```bash
export HOST="http://127.0.0.1:40001"
export X_API_KEY="replace-with-your-backend-key"
export OCR_PROVIDER="paddle"
export PADDLE_TOKEN="your-paddle-token"
export MINERU_TOKEN="your-mineru-token"
export MODEL_API_KEY="your-model-api-key"
export MODEL="deepseek-v4-flash"
export BASE_URL="https://api.deepseek.com/v1"
```

## Health Check

```bash
curl "$HOST/health"
```

## Upload PDF

```bash
curl -X POST "$HOST/api/v1/uploads" \
  -H "X-API-Key: $X_API_KEY" \
  -F "file=@/absolute/path/to/your.pdf"
```

The response will return:

- `upload_id`
- `filename`
- `page_count`

## Create Async Task

First fill in the `upload_id` returned from the previous step:

```bash
curl -X POST "$HOST/api/v1/jobs" \
  -H "X-API-Key: $X_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow": "book",
    "source": {
      "upload_id": "your-upload-id"
    },
    "ocr": {
      "provider": "'"$OCR_PROVIDER"'",
      "paddle_token": "'"$PADDLE_TOKEN"'",
      "mineru_token": "'"$MINERU_TOKEN"'"
    },
    "translation": {
      "api_key": "'"$MODEL_API_KEY"'",
      "model": "'"$MODEL"'",
      "base_url": "'"$BASE_URL"'",
      "mode": "sci"
    },
    "render": {
      "render_mode": "auto"
    },
    "runtime": {
      "workers": 100,
      "batch_size": 1,
      "classify_batch_size": 12,
      "compile_workers": 8,
      "timeout_seconds": 1800
    }
  }'
```

The response will return:

- `job_id`
- `status`

## Query Task Status

```bash
curl -H "X-API-Key: $X_API_KEY" \
  "$HOST/api/v1/jobs/your-job-id"
```

Key fields to check:

- `status`
- `stage`
- `stage_detail`
- `progress`
- `actions`

Common terminal states:

- `succeeded`
- `failed`
- `canceled`

## Download Results

Download PDF:

```bash
curl -L -H "X-API-Key: $X_API_KEY" \
  "$HOST/api/v1/jobs/your-job-id/pdf" \
  -o translated.pdf
```

Download Markdown:

```bash
curl -L -H "X-API-Key: $X_API_KEY" \
  "$HOST/api/v1/jobs/your-job-id/markdown?raw=true" \
  -o translated.md
```

Download ZIP:

```bash
curl -L -H "X-API-Key: $X_API_KEY" \
  "$HOST/api/v1/jobs/your-job-id/download" \
  -o result.zip
```

## Cancel Task

```bash
curl -X POST -H "X-API-Key: $X_API_KEY" \
  "$HOST/api/v1/jobs/your-job-id/cancel"
```

## Simple Synchronous Endpoint

If you don't want to manage upload / create task / poll status yourself, you can directly call the synchronous endpoint.

Notes:

- This endpoint is proxied through the frontend same-origin proxy
- Default path is `/api/v1/translate/bundle`
- The request will block until the task completes, then directly return the ZIP
- This is a compatibility synchronous entry point; the current formal async contract still uses `/api/v1/uploads + /api/v1/jobs` as the primary interface

```bash
curl -X POST "$HOST/api/v1/translate/bundle" \
  -H "X-API-Key: $X_API_KEY" \
  -F "file=@/absolute/path/to/your.pdf" \
  -F "provider=$OCR_PROVIDER" \
  -F "paddle_token=$PADDLE_TOKEN" \
  -F "mineru_token=$MINERU_TOKEN" \
  -F "base_url=$BASE_URL" \
  -F "api_key=$MODEL_API_KEY" \
  -F "model=$MODEL" \
  -F "mode=sci" \
  -F "workers=100" \
  -F "batch_size=1" \
  -o result.zip
```

Notes:

- `provider` should be explicitly set to `paddle` or `mineru`
- `paddle_token` / `mineru_token` only needs the one corresponding to the current `provider`
