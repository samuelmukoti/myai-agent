#!/bin/bash
# Docker/Podman entrypoint: bootstrap config files into the mounted volume, then run hermes.
set -e

MYAI_HOME="${MYAI_HOME:-/opt/data}"
INSTALL_DIR="/opt/hermes"

# --- Privilege dropping via gosu ---
# When started as root (the default for Docker, or fakeroot in rootless Podman),
# optionally remap the hermes user/group to match host-side ownership, fix volume
# permissions, then re-exec as hermes.
if [ "$(id -u)" = "0" ]; then
    if [ -n "$HERMES_UID" ] && [ "$HERMES_UID" != "$(id -u hermes)" ]; then
        echo "Changing hermes UID to $HERMES_UID"
        usermod -u "$HERMES_UID" hermes
    fi

    if [ -n "$HERMES_GID" ] && [ "$HERMES_GID" != "$(id -g hermes)" ]; then
        echo "Changing hermes GID to $HERMES_GID"
        # -o allows non-unique GID (e.g. macOS GID 20 "staff" may already exist
        # as "dialout" in the Debian-based container image)
        groupmod -o -g "$HERMES_GID" hermes 2>/dev/null || true
    fi

    actual_hermes_uid=$(id -u hermes)
    if [ "$(stat -c %u "$MYAI_HOME" 2>/dev/null)" != "$actual_hermes_uid" ]; then
        echo "$MYAI_HOME is not owned by $actual_hermes_uid, fixing"
        # In rootless Podman the container's "root" is mapped to an unprivileged
        # host UID — chown will fail.  That's fine: the volume is already owned
        # by the mapped user on the host side.
        chown -R hermes:hermes "$MYAI_HOME" 2>/dev/null || \
            echo "Warning: chown failed (rootless container?) — continuing anyway"
    fi

    echo "Dropping root privileges"
    exec gosu hermes "$0" "$@"
fi

# --- Running as hermes from here ---
source "${INSTALL_DIR}/.venv/bin/activate"

# Create essential directory structure.  Cache and platform directories
# (cache/images, cache/audio, platforms/whatsapp, etc.) are created on
# demand by the application — don't pre-create them here so new installs
# get the consolidated layout from get_hermes_dir().
# The "home/" subdirectory is a per-profile HOME for subprocesses (git,
# ssh, gh, npm …).  Without it those tools write to /root which is
# ephemeral and shared across profiles.  See issue #4426.
mkdir -p "$MYAI_HOME"/{cron,sessions,logs,hooks,memories,skills,skins,plans,workspace,home}

# .env
if [ ! -f "$MYAI_HOME/.env" ]; then
    cp "$INSTALL_DIR/.env.example" "$MYAI_HOME/.env"
fi

# config.yaml
if [ ! -f "$MYAI_HOME/config.yaml" ]; then
    cp "$INSTALL_DIR/cli-config.yaml.example" "$MYAI_HOME/config.yaml"
fi

# SOUL.md
if [ ! -f "$MYAI_HOME/SOUL.md" ]; then
    cp "$INSTALL_DIR/docker/SOUL.md" "$MYAI_HOME/SOUL.md"
fi

# Sync bundled skills (manifest-based so user edits are preserved)
if [ -d "$INSTALL_DIR/skills" ]; then
    python3 "$INSTALL_DIR/tools/skills_sync.py"
fi

exec myai "$@"
