import json
import sys
from pathlib import Path


REPO_SCRIPTS_ROOT = Path("/home/wxyhgk/tmp/Code/backend/scripts")
sys.path.insert(0, str(REPO_SCRIPTS_ROOT))

from foundation.shared.structured_errors import classify_exception


def test_classify_exception_emits_new_and_legacy_failure_fields():
    try:
        raise RuntimeError("token expired while calling provider")
    except RuntimeError as exc:
        failure = classify_exception(exc, default_stage="translation", provider="translation")

    payload = json.loads(failure.to_json())
    assert payload["failed_stage"] == "translation"
    assert payload["stage"] == "translation"
    assert payload["failure_code"] == "auth_failed"
    assert payload["error_type"] == "auth_failed"
    assert payload["failure_category"] == "auth"
    assert payload["provider_stage"] == ""
    assert payload["provider_code"] == ""
    assert payload["retryable"] is False
    assert payload["suggestion"]
    assert payload["raw_excerpt"] == "token expired while calling provider"
    assert payload["detail"] == "token expired while calling provider"


def test_classify_exception_extracts_provider_code_and_provider_category():
    try:
        raise RuntimeError("MinerU API error code=A0211: token expired during mineru_processing")
    except RuntimeError as exc:
        failure = classify_exception(exc, default_stage="provider", provider="mineru")

    payload = json.loads(failure.to_json())
    assert payload["failed_stage"] == "provider"
    assert payload["failure_code"] == "auth_failed"
    assert payload["failure_category"] == "auth"
    assert payload["provider_stage"] == "mineru_processing"
    assert payload["provider_code"] == "A0211"
    assert payload["provider"] == "mineru"
    assert payload["summary"] == "Authentication failed"
    assert "credentials" in payload["suggestion"] or "token" in payload["suggestion"].lower()
