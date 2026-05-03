# Local Startup and Configuration

## 1. Start the Backend

```bash
cd /home/wxyhgk/tmp/Code/backend/rust_api
RUST_API_BIND_HOST=0.0.0.0 \
DATA_ROOT=/home/wxyhgk/tmp/Code/data \
RUST_API_SCRIPTS_DIR=/home/wxyhgk/tmp/Code/backend/scripts \
cargo run
```

## 2. Start the Frontend

```bash
cd /home/wxyhgk/tmp/Code/frontend
python3 -m http.server 8080 --bind 0.0.0.0
```

## 3. Authentication

Except for `GET /health`, all other endpoints require by default:

```http
X-API-Key: your-rust-api-key
```

Note the distinction:

- `X-API-Key`: Backend credential for accessing the Rust API
- `api_key` in the request body: API Key for the downstream model service
- `mineru_token` in the request body: MinerU Token

## 4. Local Key Source

Local backend keys typically come from:

- `backend/rust_api/auth.local.json`
- Or the environment variable `RUST_API_KEYS`

## 5. Commonly Used Environment Variables

- `RUST_API_BIND_HOST`
- `DATA_ROOT`
- `RUST_API_SCRIPTS_DIR`
- `RUST_API_PORT`
- `RUST_API_SIMPLE_PORT`
