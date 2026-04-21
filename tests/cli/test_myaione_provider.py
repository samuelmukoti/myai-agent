"""Unit tests for the MyAIOne Inference provider integration.

Covers:
- auth.json reader handles missing, malformed, and well-formed input
- model bucketing puts local models first and filters image/audio by prefix
- env-var resolution + dotenv writer is idempotent
- PROVIDER_REGISTRY exposes myaione with the right base URL / env var
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ─── auth.json reader ────────────────────────────────────────────────────────


def test_read_myaidev_auth_missing_file_returns_none(tmp_path: Path) -> None:
    from myai_cli.inference.myaione import read_myaidev_auth

    assert read_myaidev_auth(tmp_path / "does-not-exist.json") is None


def test_read_myaidev_auth_malformed_raises(tmp_path: Path) -> None:
    from myai_cli.inference.myaione import MyaidevAuthError, read_myaidev_auth

    bad = tmp_path / "auth.json"
    bad.write_text("{ not valid json")

    with pytest.raises(MyaidevAuthError):
        read_myaidev_auth(bad)


def test_read_myaidev_auth_missing_token_raises(tmp_path: Path) -> None:
    from myai_cli.inference.myaione import MyaidevAuthError, read_myaidev_auth

    f = tmp_path / "auth.json"
    f.write_text(json.dumps({"user": {"email": "a@b"}}))

    with pytest.raises(MyaidevAuthError, match="missing a valid 'token'"):
        read_myaidev_auth(f)


def test_read_myaidev_auth_well_formed(tmp_path: Path) -> None:
    from myai_cli.inference.myaione import read_myaidev_auth

    f = tmp_path / "auth.json"
    f.write_text(
        json.dumps(
            {
                "token": "myaidev_abc123",
                "user": {"id": "u1", "email": "a@b.com", "name": "Alice"},
            }
        )
    )

    auth = read_myaidev_auth(f)
    assert auth is not None
    assert auth.token == "myaidev_abc123"
    assert auth.user_email == "a@b.com"
    assert auth.user_name == "Alice"
    assert auth.user_id == "u1"


# ─── Model bucketing ─────────────────────────────────────────────────────────


def test_bucket_models_puts_local_first() -> None:
    from myai_cli.inference.myaione import ModelInfo, bucket_models

    models = [
        ModelInfo(id="gpt-4o", owned_by="openai"),
        ModelInfo(id="qwen3.6-35b-a3b", owned_by="local"),
        ModelInfo(id="claude-sonnet-4", owned_by="anthropic"),
    ]
    local, proxied = bucket_models(models)
    assert [m.id for m in local] == ["qwen3.6-35b-a3b"]
    assert [m.id for m in proxied] == ["gpt-4o", "claude-sonnet-4"]


def test_model_is_local_by_owned_by() -> None:
    from myai_cli.inference.myaione import ModelInfo

    assert ModelInfo(id="whatever", owned_by="local").is_local
    assert ModelInfo(id="whatever", owned_by="vllm").is_local
    assert not ModelInfo(id="whatever", owned_by="openai").is_local


def test_model_is_local_by_name_prefix() -> None:
    from myai_cli.inference.myaione import ModelInfo

    # owned_by unset but the name starts with a known local prefix
    assert ModelInfo(id="qwen3-6b", owned_by="").is_local
    assert ModelInfo(id="llama-3-70b", owned_by="").is_local
    assert ModelInfo(id="mistral-7b", owned_by="").is_local
    assert not ModelInfo(id="gpt-4o", owned_by="").is_local


# ─── Env-var key resolver + dotenv writer ────────────────────────────────────


def test_get_myaione_api_key_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from myai_cli.inference.myaione import get_myaione_api_key

    monkeypatch.setenv("MYAIONE_API_KEY", "myai-test-abc")
    assert get_myaione_api_key() == "myai-test-abc"


def test_get_myaione_api_key_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from myai_cli.inference.myaione import get_myaione_api_key

    monkeypatch.delenv("MYAIONE_API_KEY", raising=False)
    assert get_myaione_api_key() is None


def test_write_api_key_to_env_creates_and_overwrites(tmp_path: Path) -> None:
    from myai_cli.inference.myaione import write_api_key_to_env

    env = tmp_path / ".env"
    env.write_text("OTHER_VAR=keep-me\nMYAIONE_API_KEY=old-key\n")

    result = write_api_key_to_env("myai-new-value", env_path=env)
    assert result == env

    contents = env.read_text()
    assert "OTHER_VAR=keep-me" in contents
    assert "MYAIONE_API_KEY=myai-new-value" in contents
    assert "old-key" not in contents


def test_write_api_key_to_env_creates_parent_dir(tmp_path: Path) -> None:
    from myai_cli.inference.myaione import write_api_key_to_env

    env = tmp_path / "nested" / "dir" / ".env"
    assert not env.parent.exists()

    write_api_key_to_env("myai-fresh", env_path=env)

    assert env.read_text().strip() == "MYAIONE_API_KEY=myai-fresh"


# ─── Provider registry wiring ────────────────────────────────────────────────


def test_provider_registry_has_myaione() -> None:
    from myai_cli.auth import PROVIDER_REGISTRY

    assert "myaione" in PROVIDER_REGISTRY
    cfg = PROVIDER_REGISTRY["myaione"]
    assert cfg.auth_type == "api_key"
    assert cfg.inference_base_url == "https://api.myai1.ai/v1"
    assert "MYAIONE_API_KEY" in cfg.api_key_env_vars
    assert cfg.base_url_env_var == "MYAIONE_BASE_URL"


def test_canonical_providers_put_myaione_first() -> None:
    from myai_cli.models import CANONICAL_PROVIDERS

    assert CANONICAL_PROVIDERS[0].slug == "myaione"
    assert CANONICAL_PROVIDERS[0].label == "MyAIOne Inference"
