"""Shared constants for MyAIOne Agent.

Import-safe module with no dependencies — can be imported from anywhere
without risk of circular imports.

Home-directory resolution
-------------------------
The agent stores its state under ``~/.myai`` (new default). Legacy installs
using ``~/.hermes`` are migrated automatically on first resolve. The env-var
fallback chain for power users is:

    $MYAI_HOME → $HERMES_HOME → ~/.myai → (migrated) ~/.hermes → ~/.myai

``get_hermes_home()`` is kept as the public name for back-compat with the
~240 call sites throughout the codebase; a ``get_myai_home()`` alias is
exposed for new code.
"""

import os
from pathlib import Path


# Module-level guard so the ~/.hermes → ~/.myai migration is attempted once
# per process.  Migration is best-effort — failures are swallowed so the
# agent still boots with whichever dir exists.
_migration_attempted = False


def _maybe_migrate_legacy_home(new_home: Path, legacy_home: Path) -> None:
    """One-shot: if ``~/.hermes`` exists and ``~/.myai`` doesn't, rename and
    leave a symlink at the legacy path so any external tool (shell aliases,
    cron jobs written pre-rename) keeps working.  Never destructive.
    """
    global _migration_attempted
    if _migration_attempted:
        return
    _migration_attempted = True

    try:
        if not legacy_home.exists() or legacy_home.is_symlink():
            return
        if new_home.exists():
            return
        os.rename(str(legacy_home), str(new_home))
        try:
            os.symlink(str(new_home), str(legacy_home), target_is_directory=True)
        except OSError:
            # symlink creation can fail on some Windows/cross-fs setups —
            # rename already succeeded, so the agent works without the
            # back-compat symlink.
            pass
    except OSError:
        # Any failure (permissions, cross-mount, concurrent rename) is
        # non-fatal: the agent falls back to whichever dir is readable.
        pass


def _safe_exists(p: Path) -> bool:
    """Return ``p.exists()`` but swallow PermissionError.

    In sudo / cross-user contexts (e.g. a service-install helper resolving
    a target user's home while running as a different user), ``stat()`` on
    the candidate path can fail with EACCES.  Treat "can't tell" as "doesn't
    exist" so resolution keeps going with the remaining candidates instead
    of crashing.
    """
    try:
        return p.exists()
    except OSError:
        return False


def get_myai_home() -> Path:
    """Return the MyAIOne home directory (default: ``~/.myai``).

    Resolution order:
        1. ``$MYAI_HOME`` env var
        2. ``$HERMES_HOME`` env var (back-compat — old installers & users)
        3. ``~/.myai`` if it exists on disk
        4. ``~/.hermes`` if it exists (triggers one-time migration → ``~/.myai``)
        5. ``~/.myai`` as the new-install default

    This is the single source of truth — all other copies should import this.
    """
    for env_var in ("MYAI_HOME", "HERMES_HOME"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return Path(val)

    home = Path.home()
    new_home = home / ".myai"
    legacy_home = home / ".hermes"

    if _safe_exists(new_home):
        return new_home
    if _safe_exists(legacy_home):
        _maybe_migrate_legacy_home(new_home, legacy_home)
        # After migration ``new_home`` is the dir; before it, fall back to
        # legacy so a failed migration still lets the agent find existing state.
        return new_home if _safe_exists(new_home) else legacy_home
    return new_home


# Back-compat alias — 200+ call sites import this by name.
get_hermes_home = get_myai_home


def get_default_hermes_root() -> Path:
    """Return the root MyAIOne directory for profile-level operations.

    In standard deployments this is ``~/.myai`` (or the legacy ``~/.hermes``
    if that's what the system was installed with).

    In Docker or custom deployments where ``MYAI_HOME`` / ``HERMES_HOME``
    points outside the native home (e.g. ``/opt/data``), returns that path
    directly — that IS the root.

    In profile mode where ``*_HOME`` is ``<root>/profiles/<name>``, returns
    ``<root>`` so that ``profile list`` can see all profiles.

    Import-safe — no dependencies beyond stdlib.
    """
    env_home = os.environ.get("MYAI_HOME", "") or os.environ.get("HERMES_HOME", "")
    home = Path.home()
    # The "plausible defaults" are the per-user standard paths, independent of
    # the env var. Only these count as "the root already" — if env_home points
    # to one of them, that's the root; if it points below profiles/, the root
    # is the parent of profiles/. We must compute these before consulting
    # get_myai_home() because that function short-circuits on env_home and
    # therefore can't distinguish "env var IS the root" from "env var is a
    # profile under the root".
    plausible_defaults = [home / ".myai", home / ".hermes"]

    if not env_home:
        # No env override — pick the first plausible default that exists, or
        # fall back to ~/.myai for fresh installs.
        for cand in plausible_defaults:
            if _safe_exists(cand):
                return cand
        return plausible_defaults[0]

    env_path = Path(env_home)

    # Profile pattern takes precedence: ``<root>/profiles/<name>`` → ``<root>``.
    # This is the common profile-mode layout used by ``myai profile create``
    # and the Docker entrypoint.
    if env_path.parent.name == "profiles":
        return env_path.parent.parent

    # Env var points to one of the plausible default homes → that IS the root.
    for cand in plausible_defaults:
        try:
            if env_path.resolve() == cand.resolve():
                return cand
        except OSError:
            continue

    # Env var points somewhere else entirely (Docker custom mount,
    # /opt/shared, etc.) — treat it as the root.
    return env_path


def get_optional_skills_dir(default: Path | None = None) -> Path:
    """Return the optional-skills directory, honoring package-manager wrappers.

    Packaged installs may ship ``optional-skills`` outside the Python package
    tree and expose it via ``MYAI_OPTIONAL_SKILLS`` (or the legacy
    ``MYAI_AGENT_OPTIONAL_SKILLS``).
    """
    override = (
        os.getenv("MYAI_OPTIONAL_SKILLS", "").strip()
        or os.getenv("MYAI_AGENT_OPTIONAL_SKILLS", "").strip()
    )
    if override:
        return Path(override)
    if default is not None:
        return default
    return get_myai_home() / "optional-skills"


def get_hermes_dir(new_subpath: str, old_name: str) -> Path:
    """Resolve a MyAIOne subdirectory with backward compatibility.

    New installs get the consolidated layout (e.g. ``cache/images``).
    Existing installs that already have the old path (e.g. ``image_cache``)
    keep using it — no migration required.

    Args:
        new_subpath: Preferred path relative to the home dir (e.g. ``"cache/images"``).
        old_name: Legacy path relative to the home dir (e.g. ``"image_cache"``).

    Returns:
        Absolute ``Path`` — old location if it exists on disk, otherwise the new one.
    """
    home = get_myai_home()
    old_path = home / old_name
    if old_path.exists():
        return old_path
    return home / new_subpath


def display_hermes_home() -> str:
    """Return a user-friendly display string for the current home dir.

    Uses ``~/`` shorthand for readability::

        default:  ``~/.myai``
        profile:  ``~/.myai/profiles/coder``
        legacy:   ``~/.hermes`` (symlinked to ``~/.myai`` post-migration)
        custom:   ``/opt/myai-custom``

    Use this in **user-facing** print/log messages instead of hardcoding
    ``~/.myai``.  For code that needs a real ``Path``, use
    :func:`get_myai_home` instead.
    """
    home = get_myai_home()
    try:
        return "~/" + str(home.relative_to(Path.home()))
    except ValueError:
        return str(home)


# Back-compat alias.
display_myai_home = display_hermes_home


def get_subprocess_home() -> str | None:
    """Return a per-profile HOME directory for subprocesses, or None.

    When ``{MYAI_HOME}/home/`` exists on disk, subprocesses should use it
    as ``HOME`` so system tools (git, ssh, gh, npm …) write their configs
    inside the MyAIOne data directory instead of the OS-level ``/root`` or
    ``~/``.  This provides:

    * **Docker persistence** — tool configs land inside the persistent volume.
    * **Profile isolation** — each profile gets its own git identity, SSH
      keys, gh tokens, etc.

    The Python process's own ``os.environ["HOME"]`` and ``Path.home()`` are
    **never** modified — only subprocess environments should inject this value.
    Activation is directory-based: if the ``home/`` subdirectory doesn't
    exist, returns ``None`` and behavior is unchanged.
    """
    myai_home = os.getenv("MYAI_HOME") or os.getenv("HERMES_HOME")
    if not myai_home:
        return None
    profile_home = os.path.join(myai_home, "home")
    if os.path.isdir(profile_home):
        return profile_home
    return None


VALID_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")


def parse_reasoning_effort(effort: str) -> dict | None:
    """Parse a reasoning effort level into a config dict.

    Valid levels: "none", "minimal", "low", "medium", "high", "xhigh".
    Returns None when the input is empty or unrecognized (caller uses default).
    Returns {"enabled": False} for "none".
    Returns {"enabled": True, "effort": <level>} for valid effort levels.
    """
    if not effort or not effort.strip():
        return None
    effort = effort.strip().lower()
    if effort == "none":
        return {"enabled": False}
    if effort in VALID_REASONING_EFFORTS:
        return {"enabled": True, "effort": effort}
    return None


def is_termux() -> bool:
    """Return True when running inside a Termux (Android) environment.

    Checks ``TERMUX_VERSION`` (set by Termux) or the Termux-specific
    ``PREFIX`` path.  Import-safe — no heavy deps.
    """
    prefix = os.getenv("PREFIX", "")
    return bool(os.getenv("TERMUX_VERSION") or "com.termux/files/usr" in prefix)


_wsl_detected: bool | None = None


def is_wsl() -> bool:
    """Return True when running inside WSL (Windows Subsystem for Linux).

    Checks ``/proc/version`` for the ``microsoft`` marker that both WSL1
    and WSL2 inject.  Result is cached for the process lifetime.
    Import-safe — no heavy deps.
    """
    global _wsl_detected
    if _wsl_detected is not None:
        return _wsl_detected
    try:
        with open("/proc/version", "r") as f:
            _wsl_detected = "microsoft" in f.read().lower()
    except Exception:
        _wsl_detected = False
    return _wsl_detected


_container_detected: bool | None = None


def is_container() -> bool:
    """Return True when running inside a Docker/Podman container.

    Checks ``/.dockerenv`` (Docker), ``/run/.containerenv`` (Podman),
    and ``/proc/1/cgroup`` for container runtime markers.  Result is
    cached for the process lifetime.  Import-safe — no heavy deps.
    """
    global _container_detected
    if _container_detected is not None:
        return _container_detected
    if os.path.exists("/.dockerenv"):
        _container_detected = True
        return True
    if os.path.exists("/run/.containerenv"):
        _container_detected = True
        return True
    try:
        with open("/proc/1/cgroup", "r") as f:
            cgroup = f.read()
            if "docker" in cgroup or "podman" in cgroup or "/lxc/" in cgroup:
                _container_detected = True
                return True
    except OSError:
        pass
    _container_detected = False
    return False


# ─── Well-Known Paths ─────────────────────────────────────────────────────────


def get_config_path() -> Path:
    """Return the path to ``config.yaml`` under the MyAIOne home dir."""
    return get_myai_home() / "config.yaml"


def get_skills_dir() -> Path:
    """Return the path to the skills directory under the MyAIOne home dir."""
    return get_myai_home() / "skills"


def get_env_path() -> Path:
    """Return the path to the ``.env`` file under the MyAIOne home dir."""
    return get_myai_home() / ".env"


# ─── Network Preferences ─────────────────────────────────────────────────────


def apply_ipv4_preference(force: bool = False) -> None:
    """Monkey-patch ``socket.getaddrinfo`` to prefer IPv4 connections.

    On servers with broken or unreachable IPv6, Python tries AAAA records
    first and hangs for the full TCP timeout before falling back to IPv4.
    This affects httpx, requests, urllib, the OpenAI SDK — everything that
    uses ``socket.getaddrinfo``.

    When *force* is True, patches ``getaddrinfo`` so that calls with
    ``family=AF_UNSPEC`` (the default) resolve as ``AF_INET`` instead,
    skipping IPv6 entirely.  If no A record exists, falls back to the
    original unfiltered resolution so pure-IPv6 hosts still work.

    Safe to call multiple times — only patches once.
    Set ``network.force_ipv4: true`` in ``config.yaml`` to enable.
    """
    if not force:
        return

    import socket

    # Guard against double-patching
    if getattr(socket.getaddrinfo, "_hermes_ipv4_patched", False):
        return

    _original_getaddrinfo = socket.getaddrinfo

    def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if family == 0:  # AF_UNSPEC — caller didn't request a specific family
            try:
                return _original_getaddrinfo(
                    host, port, socket.AF_INET, type, proto, flags
                )
            except socket.gaierror:
                # No A record — fall back to full resolution (pure-IPv6 hosts)
                return _original_getaddrinfo(host, port, family, type, proto, flags)
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    _ipv4_getaddrinfo._hermes_ipv4_patched = True  # type: ignore[attr-defined]
    socket.getaddrinfo = _ipv4_getaddrinfo  # type: ignore[assignment]


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELS_URL = f"{OPENROUTER_BASE_URL}/models"

AI_GATEWAY_BASE_URL = "https://ai-gateway.vercel.sh/v1"
