from __future__ import annotations
import json
import os
import random
import re
import socket
import threading
import time
from typing import Any
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from foundation.shared.local_env import get_secret
from services.translation.diagnostics import get_active_translation_run_diagnostics
from services.translation.diagnostics import infer_stage_from_request_label
from services.translation.llm.shared.prompt_building import build_messages
from services.translation.llm.shared.prompt_building import build_single_item_fallback_messages
from services.translation.llm.shared.response_parsing import extract_json_text
from services.translation.llm.shared.response_parsing import extract_single_item_translation_text
from services.translation.llm.shared.response_parsing import unwrap_translation_shell


DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_API_KEY_FILE = "deepseek.env"
TRUST_ENV_PROXY_ENV = "PDF_TRANSLATOR_TRUST_ENV_PROXY"
STREAM_RESPONSES_ENV = "PDF_TRANSLATOR_DEEPSEEK_STREAM"
_THREAD_LOCAL = threading.local()
HTTP_RETRY_ATTEMPTS = 2
DNS_RETRY_MIN_ATTEMPTS = 3
HTTP_RETRY_BACKOFF_MAX_SECS = 20
HTTP_RATE_LIMIT_WAIT_MAX_SECS = 300
_TRANSPORT_RETRY_MARKERS = (
    "temporary failure in name resolution",
    "name resolution",
    "failed to resolve",
    "max retries exceeded",
    "connection aborted",
    "connection reset",
    "connection refused",
    "connect timeout",
    "read timeout",
    "timed out",
    "server disconnected",
    "remote end closed connection",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "too many requests",
)
_TRANSPORT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_DNS_RETRY_MARKERS = (
    "temporary failure in name resolution",
    "name resolution",
    "failed to resolve",
    "nodename nor servname provided",
    "no address associated with hostname",
    "getaddrinfo failed",
)
_DNS_CACHE_TTL_SECS = 60
_DNS_CACHE_LOCK = threading.Lock()
_DNS_CACHE: dict[str, float] = {}


def normalize_base_url(base_url: str) -> str:
    normalized = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
    if normalized.endswith("/chat/completions"):
        normalized = normalized[: -len("/chat/completions")]
    return normalized


def _hostname_from_base_url(base_url: str) -> str:
    parsed = urlparse(normalize_base_url(base_url))
    return str(parsed.hostname or "").strip().lower()


def is_dns_resolution_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _DNS_RETRY_MARKERS)


def _prewarm_dns(base_url: str, *, request_label: str = "") -> None:
    hostname = _hostname_from_base_url(base_url)
    if not hostname:
        return
    now = time.time()
    with _DNS_CACHE_LOCK:
        cached_until = _DNS_CACHE.get(hostname, 0.0)
        if cached_until > now:
            return
    try:
        socket.getaddrinfo(hostname, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        if request_label:
            print(f"{request_label}: dns prewarm skipped host={hostname}: {type(exc).__name__}: {exc}", flush=True)
        return
    with _DNS_CACHE_LOCK:
        _DNS_CACHE[hostname] = now + _DNS_CACHE_TTL_SECS
    if request_label:
        print(f"{request_label}: dns prewarm ok host={hostname}", flush=True)


def chat_completions_url(base_url: str) -> str:
    return f"{normalize_base_url(base_url)}/chat/completions"


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def _message_chars(messages: list[dict[str, str]]) -> int:
    total = 0
    for message in messages:
        if not isinstance(message, dict):
            continue
        total += len(str(message.get("content", "") or ""))
    return total


def _body_bytes(body: dict[str, Any]) -> int:
    return len(json.dumps(body, ensure_ascii=False).encode("utf-8"))


def _response_text_excerpt(response: requests.Response, *, max_chars: int = 800) -> str:
    try:
        text = response.text or ""
    except Exception as exc:  # noqa: BLE001
        return f"<failed to read response body: {type(exc).__name__}: {exc}>"
    compact = " ".join(text.strip().split())
    if len(compact) > max_chars:
        return f"{compact[:max_chars]}...<truncated>"
    return compact


def _request_meta_summary(
    *,
    model: str,
    messages: list[dict[str, str]],
    body: dict[str, Any],
    use_stream: bool,
) -> str:
    response_format = body.get("response_format")
    response_format_type = (
        str(response_format.get("type", "") or "")
        if isinstance(response_format, dict)
        else ("present" if response_format is not None else "none")
    )
    return (
        f"model={model} messages={len(messages)} message_chars={_message_chars(messages)} "
        f"body_bytes={_body_bytes(body)} stream={use_stream} response_format={response_format_type or 'none'}"
    )


def _raise_for_status_with_context(
    response: requests.Response,
    *,
    model: str,
    messages: list[dict[str, str]],
    body: dict[str, Any],
    use_stream: bool,
) -> None:
    status_code = int(getattr(response, "status_code", 200) or 200)
    if status_code < 400:
        return
    response_body = _response_text_excerpt(response) or "<empty>"
    reason = getattr(response, "reason", "") or "Error"
    url = getattr(response, "url", "") or "<unknown-url>"
    raise requests.HTTPError(
        f"{status_code} Client Error: {reason} for url: {url} | "
        f"response_body={response_body} | "
        f"request_meta={_request_meta_summary(model=model, messages=messages, body=body, use_stream=use_stream)}",
        response=response,
    )


def _supports_response_schema_fallback(response_format: dict[str, Any] | None) -> bool:
    if not isinstance(response_format, dict):
        return False
    return str(response_format.get("type", "") or "").strip().lower() == "json_schema"


def _provider_supports_json_schema(*, model: str, base_url: str) -> bool:
    normalized_base = normalize_base_url(base_url).lower()
    normalized_model = (model or "").strip().lower()
    if "api.deepseek.com" in normalized_base:
        return False
    if normalized_model.startswith("deepseek"):
        return False
    return True


def _fallback_response_format(response_format: dict[str, Any] | None) -> dict[str, str] | None:
    if not _supports_response_schema_fallback(response_format):
        return response_format
    return {"type": "json_object"}


def should_use_stream_responses() -> bool:
    value = os.environ.get(STREAM_RESPONSES_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def should_trust_env_proxy() -> bool:
    value = os.environ.get(TRUST_ENV_PROXY_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = should_trust_env_proxy()
    if not session.trust_env:
        session.proxies.clear()
    diagnostics = get_active_translation_run_diagnostics()
    pool_size = 10
    if diagnostics is not None and diagnostics.provider_family == "deepseek_official":
        pool_size = min(256, max(32, int(diagnostics.configured_workers)))
    adapter = HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=Retry(
            total=0,
            connect=0,
            read=0,
            redirect=0,
            status=0,
            backoff_factor=0,
        )
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _drop_session(session_key: str) -> None:
    session = getattr(_THREAD_LOCAL, session_key, None)
    if session is not None:
        try:
            session.close()
        except Exception:
            pass
        setattr(_THREAD_LOCAL, session_key, None)


def get_session() -> requests.Session:
    session_key = "session_trust_env" if should_trust_env_proxy() else "session_direct"
    session = getattr(_THREAD_LOCAL, session_key, None)
    if session is None:
        session = _build_session()
        setattr(_THREAD_LOCAL, session_key, session)
    return session


def _request_session_key() -> str:
    return "session_trust_env" if should_trust_env_proxy() else "session_direct"


def is_transport_error(exc: Exception) -> bool:
    if isinstance(exc, (ValueError, KeyError, json.JSONDecodeError)):
        return False
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    text = str(exc).lower()
    if any(marker in text for marker in _TRANSPORT_RETRY_MARKERS):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return exc.response.status_code in _TRANSPORT_STATUS_CODES
    return isinstance(exc, requests.RequestException)


def _is_retryable_http_error(exc: Exception) -> bool:
    return is_transport_error(exc)


def _retry_delay(attempt: int) -> float:
    base_delay = min(float(HTTP_RETRY_BACKOFF_MAX_SECS), float(2 ** max(0, attempt - 1)))
    jitter_window = max(0.25, base_delay * 0.5)
    return min(float(HTTP_RETRY_BACKOFF_MAX_SECS), base_delay + random.uniform(0.0, jitter_window))


def _retry_after_delay(exc: Exception, attempt: int) -> tuple[float, str]:
    if isinstance(exc, requests.HTTPError) and exc.response is not None and exc.response.status_code == 429:
        header = str(exc.response.headers.get("Retry-After", "") or "").strip()
        if header.isdigit():
            return float(max(1, int(header))), "retry_after"
    return _retry_delay(attempt), "backoff"


def _extract_stream_delta_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list):
        return ""
    chunks: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta")
        if isinstance(delta, dict):
            content = delta.get("content")
            if isinstance(content, str) and content:
                chunks.append(content)
            reasoning_content = delta.get("reasoning_content")
            if isinstance(reasoning_content, str) and reasoning_content:
                chunks.append(reasoning_content)
            continue
        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content:
                chunks.append(content)
    return "".join(chunks)


def _read_streaming_chat_content(response: requests.Response) -> str:
    chunks: list[str] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if raw_line is None:
            continue
        line = raw_line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        data = json.loads(payload)
        piece = _extract_stream_delta_text(data)
        if piece:
            chunks.append(piece)
    return "".join(chunks)


def request_chat_content(
    messages: list[dict[str, str]],
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    temperature: float = 0.2,
    response_format: dict[str, str] | None = None,
    timeout: int = 120,
    request_label: str = "",
    max_attempts: int | None = None,
) -> str:
    last_error: Exception | None = None
    request_stage = infer_stage_from_request_label(request_label)
    diagnostics = get_active_translation_run_diagnostics()
    active_response_format = response_format
    if _supports_response_schema_fallback(active_response_format) and not _provider_supports_json_schema(
        model=model,
        base_url=base_url,
    ):
        active_response_format = _fallback_response_format(active_response_format)
    attempted_schema_fallback = False
    accumulated_rate_limit_wait = 0
    body: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }
    use_stream = should_use_stream_responses()
    if use_stream:
        body["stream"] = True
    if active_response_format is not None:
        body["response_format"] = active_response_format

    attempt_limit = max(1, int(max_attempts or HTTP_RETRY_ATTEMPTS))
    dns_retry_limit = max(attempt_limit, DNS_RETRY_MIN_ATTEMPTS)
    attempt = 1
    while attempt <= attempt_limit:
        started = time.perf_counter()
        diagnostics_request_id: int | None = None
        try:
            _prewarm_dns(base_url, request_label=request_label)
            if diagnostics is not None:
                diagnostics.acquire_request_slot()
                diagnostics_request_id = diagnostics.record_request_start(
                    stage=request_stage,
                    request_label=request_label,
                    timeout_s=timeout,
                    attempt=attempt,
                )
            if request_label:
                print(
                    f"{request_label}: http attempt {attempt}/{attempt_limit} -> {model} {chat_completions_url(base_url)} timeout={timeout}s stream={use_stream}",
                    flush=True,
                )
            response = get_session().post(
                chat_completions_url(base_url),
                headers=build_headers(api_key),
                json=body,
                timeout=timeout,
                stream=use_stream,
            )
            _raise_for_status_with_context(
                response,
                model=model,
                messages=messages,
                body=body,
                use_stream=use_stream,
            )
            if use_stream:
                content = _read_streaming_chat_content(response)
                if not content.strip():
                    raise ValueError("Stream response did not contain any content.")
            else:
                data: dict[str, Any] = response.json()
                content = data["choices"][0]["message"]["content"]
            if request_label:
                elapsed = time.perf_counter() - started
                print(f"{request_label}: http ok in {elapsed:.2f}s", flush=True)
            if diagnostics is not None and diagnostics_request_id is not None:
                diagnostics.record_request_end(
                    diagnostics_request_id,
                    success=True,
                    elapsed_ms=int(round((time.perf_counter() - started) * 1000)),
                )
                diagnostics.release_request_slot(
                    success=True,
                    elapsed_ms=int(round((time.perf_counter() - started) * 1000)),
                )
            return content
        except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError, socket.gaierror) as exc:
            last_error = exc
            elapsed = time.perf_counter() - started
            status_code = exc.response.status_code if isinstance(exc, requests.HTTPError) and exc.response is not None else None
            if diagnostics is not None and diagnostics_request_id is not None:
                diagnostics.record_request_end(
                    diagnostics_request_id,
                    success=False,
                    elapsed_ms=int(round(elapsed * 1000)),
                    status_code=status_code,
                    error_class=type(exc).__name__,
                )
                diagnostics.release_request_slot(
                    success=False,
                    elapsed_ms=int(round(elapsed * 1000)),
                    status_code=status_code,
                    error_class=type(exc).__name__,
                )
            if request_label:
                print(
                    f"{request_label}: http failed attempt {attempt}/{attempt_limit} after {elapsed:.2f}s: {type(exc).__name__}: {exc}",
                    flush=True,
                )
            if (
                not attempted_schema_fallback
                and _supports_response_schema_fallback(active_response_format)
                and isinstance(exc, requests.HTTPError)
                and exc.response is not None
                and exc.response.status_code == 400
            ):
                attempted_schema_fallback = True
                active_response_format = _fallback_response_format(active_response_format)
                if active_response_format is None:
                    body.pop("response_format", None)
                else:
                    body["response_format"] = active_response_format
                if request_label:
                    print(f"{request_label}: response_format fallback json_schema -> json_object after 400", flush=True)
                continue
            dns_failure = is_dns_resolution_error(exc)
            if dns_failure and attempt_limit < dns_retry_limit:
                attempt_limit = dns_retry_limit
            if attempt >= attempt_limit or not _is_retryable_http_error(exc):
                raise
            _drop_session(_request_session_key())
            if dns_failure:
                with _DNS_CACHE_LOCK:
                    _DNS_CACHE.pop(_hostname_from_base_url(base_url), None)
            delay_secs, delay_kind = _retry_after_delay(exc, attempt)
            if status_code == 429:
                accumulated_rate_limit_wait += delay_secs
                if accumulated_rate_limit_wait > HTTP_RATE_LIMIT_WAIT_MAX_SECS:
                    raise requests.HTTPError(
                        f"rate-limit wait budget exceeded ({accumulated_rate_limit_wait}s > {HTTP_RATE_LIMIT_WAIT_MAX_SECS}s)",
                        response=exc.response if isinstance(exc, requests.HTTPError) else None,
                    ) from exc
            if request_label:
                print(
                    f"{request_label}: retrying in {delay_secs:.2f}s ({delay_kind})",
                    flush=True,
                )
            time.sleep(delay_secs)
        attempt += 1

    if last_error is not None:
        raise last_error
    raise RuntimeError("Chat completion failed without an exception.")


def translate_batch(
    batch: list[dict],
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    mode: str = "fast",
) -> dict[str, str]:
    from services.translation.llm.shared.orchestration.retrying_translator import translate_batch as _translate_batch

    return _translate_batch(batch, api_key=api_key, model=model, base_url=base_url, mode=mode)


def get_api_key(explicit_api_key: str = "", env_var: str = DEFAULT_API_KEY_ENV, required: bool = True) -> str:
    api_key = get_secret(
        explicit_value=explicit_api_key,
        env_var=env_var,
        env_file_name=DEFAULT_API_KEY_FILE,
    )
    if required and not api_key:
        raise RuntimeError(f"Missing API key. Set {env_var}, scripts/.env/{DEFAULT_API_KEY_FILE}, or pass --api-key.")
    return api_key
