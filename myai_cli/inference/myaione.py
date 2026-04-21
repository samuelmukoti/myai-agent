"""MyAIOne Inference provider — integration with api.myai1.ai.

The MyAIOne inference server is OpenAI-compatible (see
`~/projects/myaidev-inference-svr`).  It exposes chat, image, and audio
endpoints under ``https://api.myai1.ai/v1`` and authenticates via
``Authorization: Bearer <myai-key>``.

Two credential sources are supported, in priority order:

    1. ``MYAIONE_API_KEY`` env var (or ``~/.myai/.env``)
    2. An inference API key provisioned via the ``myaidev-method`` CLI
       (``~/.myaidev/auth.json`` → session token is exchanged at
       ``dev.myai1.ai`` for a long-lived ``myai-<64>`` inference key,
       cached into ``~/.myai/.env``).

Fresh containers therefore need either ``myaidev-method login`` or an
explicit ``MYAIONE_API_KEY`` before the first call.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ─── Constants ───────────────────────────────────────────────────────────────

# Public inference endpoint — OpenAI-compatible.
MYAIONE_BASE_URL = "https://api.myai1.ai/v1"

# Website that issues / manages inference keys.  The dev portal's
# ``/api/user/api-keys`` endpoint (with Bearer auth — see the
# ``feature/cli-api-keys-bearer-auth`` branch of myaidev-website) is what
# auto-provisioning calls.
MYAIDEV_WEBSITE_BASE_URL = "https://dev.myai1.ai"

# Env var name the rest of the agent looks up for the Bearer token used
# against ``api.myai1.ai``.  Stored in ``~/.myai/.env`` after
# auto-provisioning so it survives restarts without another round-trip.
MYAIONE_API_KEY_ENV = "MYAIONE_API_KEY"

# File the ``myaidev-method`` CLI writes on successful login.
MYAIDEV_AUTH_PATH = Path.home() / ".myaidev" / "auth.json"


# ─── Auth-file reader ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MyaidevAuth:
    """Parsed ``~/.myaidev/auth.json`` payload.

    The file currently stores a long-lived session token plus the user
    identity returned by ``dev.myai1.ai`` on login.  There is no
    ``expiresAt`` field in the current CLI release, so we don't attempt
    expiry checks — the server rejects invalid/revoked tokens with a 401
    and the caller surfaces that as "run ``myaidev-method login``".
    """

    token: str
    user_id: str
    user_email: str
    user_name: str


class MyaidevAuthError(RuntimeError):
    """Raised when the myaidev-method auth file is missing or malformed."""


def read_myaidev_auth(path: Path = MYAIDEV_AUTH_PATH) -> Optional[MyaidevAuth]:
    """Return the parsed auth payload, or ``None`` if the file is absent.

    Malformed JSON or missing required keys raise ``MyaidevAuthError`` so
    callers can distinguish "user never logged in" (``None``) from
    "something corrupted the file" (raise) — the former is a clean
    first-run path, the latter is a real error worth surfacing.
    """
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MyaidevAuthError(f"could not parse {path}: {exc}") from exc

    token = raw.get("token")
    user = raw.get("user") or {}
    if not isinstance(token, str) or not token.strip():
        raise MyaidevAuthError(
            f"{path} is missing a valid 'token' field; re-run `myaidev-method login`"
        )

    return MyaidevAuth(
        token=token.strip(),
        user_id=str(user.get("id", "")),
        user_email=str(user.get("email", "")),
        user_name=str(user.get("name", "")),
    )


# ─── Inference-key resolution ────────────────────────────────────────────────


def get_myaione_api_key(
    *,
    prefer_env: bool = True,
    env_var: str = MYAIONE_API_KEY_ENV,
) -> Optional[str]:
    """Return the inference API key for api.myai1.ai, or ``None`` if unavailable.

    Resolution order:
        1. ``MYAIONE_API_KEY`` env var (already loaded from ``~/.myai/.env``)
        2. *[future]* A cached token mapped from the myaidev-method session;
           we don't read that directly here — that path goes through the
           auto-provisioning flow, which writes into ``~/.myai/.env``.

    Callers that need to handle a fresh install (no key yet) should use
    ``resolve_or_provision_myaione_api_key`` instead.
    """
    if prefer_env:
        val = os.environ.get(env_var, "").strip()
        if val:
            return val
    return None


def myaione_base_url() -> str:
    """Return the OpenAI-compatible base URL for api.myai1.ai."""
    return os.environ.get("MYAIONE_BASE_URL", "").strip() or MYAIONE_BASE_URL


# ─── HTTP: list models + provision key ───────────────────────────────────────


@dataclass(frozen=True)
class ModelInfo:
    """Relevant subset of the OpenAI ``/v1/models`` response item."""

    id: str
    owned_by: str  # "local", "proxy", "openai", "anthropic", or similar

    @property
    def is_local(self) -> bool:
        """True when the model is served by the MyAIOne inference cluster itself.

        ``owned_by`` is the inference-server's classification; we also fall
        back to name-prefix heuristics so new local models don't require
        code changes to surface as "local" in the picker.
        """
        if self.owned_by.lower() in {"local", "vllm"}:
            return True
        prefix = self.id.lower()
        return prefix.startswith(("qwen", "llama", "mistral-", "deepseek-", "phi-", "gemma-"))


_CHAT_MODEL_BLOCKLIST_PREFIXES = (
    # These aren't chat completions — they're image / audio endpoints
    # served by the same inference server.  Hide them from chat-mode setup.
    "z-image",
    "whisper",
    "tts-",
    "dall-e",
    "stable-diffusion",
    "sd-",
    "sdxl",
)


def list_chat_models(api_key: str, timeout: float = 15.0) -> list[ModelInfo]:
    """Fetch ``/v1/models`` and return the chat-capable entries.

    Image-gen and audio models are filtered out via a name-prefix blocklist
    since the server's model metadata doesn't distinguish them explicitly.

    Raises ``RuntimeError`` on network failure or non-200 response so the
    caller can surface a user-visible error.
    """
    import urllib.error
    import urllib.request

    url = f"{myaione_base_url().rstrip('/')}/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(
            f"GET {url} returned {exc.code}: {body}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"could not reach {url}: {exc}") from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected /v1/models response shape: {payload!r}")

    models: list[ModelInfo] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        mid = item.get("id")
        if not isinstance(mid, str) or not mid.strip():
            continue
        mid = mid.strip()
        if mid.lower().startswith(_CHAT_MODEL_BLOCKLIST_PREFIXES):
            continue
        owned_by = item.get("owned_by") or ""
        models.append(ModelInfo(id=mid, owned_by=str(owned_by)))
    return models


def bucket_models(models: list[ModelInfo]) -> tuple[list[ModelInfo], list[ModelInfo]]:
    """Split ``models`` into (local, proxied) in display order.

    Local models come first in the picker — MyAIOne's own compute is the
    default positioning.  Proxied models (openai/anthropic/etc passing
    through the gateway) are shown below a divider and only selected
    explicitly.
    """
    local = [m for m in models if m.is_local]
    proxied = [m for m in models if not m.is_local]
    return local, proxied


def provision_inference_key(
    session_token: str,
    *,
    key_name: str = "MyAIOne Agent (auto-provisioned)",
    website_base_url: str = MYAIDEV_WEBSITE_BASE_URL,
    timeout: float = 20.0,
) -> Optional[str]:
    """Exchange a ``myaidev-method`` session token for an inference API key.

    Calls the website's ``/api/user/api-keys`` endpoint with bearer auth.
    Returns the raw ``myai-<64>`` string on success, or ``None`` when the
    website hasn't rolled out bearer support yet (HTTP 401/403 on the
    bearer call — clean signal for callers to fall back to env-var path).
    Raises ``RuntimeError`` for other transport failures.

    This is a best-effort provisioning helper; callers should treat a
    ``None`` return as "bearer auth not available, ask the user for a
    manually-pasted key or point them at the dashboard".
    """
    import urllib.error
    import urllib.request

    url = f"{website_base_url.rstrip('/')}/api/user/api-keys"

    # First try listing existing keys — if the user already has one
    # labelled as auto-provisioned, they gave it to us on a previous run
    # but we lost the plaintext (the website only shows the plaintext at
    # creation time).  In that case we can't reuse it; just create a new one.
    # List is still a useful signal for the caller.
    body = json.dumps({"name": key_name}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 401/403 on a bearer call → the website hasn't shipped bearer
        # support yet.  Caller falls back gracefully.
        if exc.code in (401, 403):
            return None
        body = exc.read().decode("utf-8", errors="replace")[:200]
        raise RuntimeError(f"POST {url} returned {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"could not reach {url}: {exc}") from exc

    key = (payload.get("key") or {}).get("apiKey") if isinstance(payload, dict) else None
    if not isinstance(key, str) or not key.strip():
        return None
    return key.strip()


# ─── Dotenv writer ──────────────────────────────────────────────────────────


def write_api_key_to_env(
    api_key: str,
    *,
    env_path: Optional[Path] = None,
    env_var: str = MYAIONE_API_KEY_ENV,
) -> Path:
    """Persist the inference API key to ``~/.myai/.env`` (idempotent).

    Existing ``MYAIONE_API_KEY=...`` lines are replaced in place; other
    lines are preserved so users keep their hand-tuned env vars.  Returns
    the path written.
    """
    if env_path is None:
        try:
            from myai_constants import get_myai_home
            env_path = get_myai_home() / ".env"
        except ImportError:
            env_path = Path.home() / ".myai" / ".env"

    env_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    if env_path.exists():
        try:
            existing = env_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            existing = []
        prefix = f"{env_var}="
        lines = [ln for ln in existing if not ln.startswith(prefix)]

    lines.append(f"{env_var}={api_key}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    return env_path
