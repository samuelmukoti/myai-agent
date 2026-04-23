FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c4f23a5f2df22866bd7857e5d304b67a564f4feab6ac22044dde719b AS uv_source
FROM tianon/gosu:1.19-trixie@sha256:3b176695959c71e123eb390d427efc665eeb561b1540e82679c15e992006b8b9 AS gosu_source
FROM debian:13.4

# Disable Python stdout buffering to ensure logs are printed immediately
ENV PYTHONUNBUFFERED=1

# Store Playwright browsers outside the volume mount so the build-time
# install survives the /opt/data volume overlay at runtime.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/hermes/.playwright

# Install system dependencies in one layer, clear APT cache
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential nodejs npm python3 ripgrep ffmpeg gcc python3-dev libffi-dev procps git && \
    rm -rf /var/lib/apt/lists/*

# Non-root user for runtime; UID can be overridden via MYAI_UID at runtime
RUN useradd -u 10000 -m -d /opt/data hermes

COPY --chmod=0755 --from=gosu_source /gosu /usr/local/bin/
COPY --chmod=0755 --from=uv_source /usr/local/bin/uv /usr/local/bin/uvx /usr/local/bin/

WORKDIR /opt/hermes

# ---------- Layer-cached dependency install ----------
# Copy only package manifests first so npm install + Playwright are cached
# unless the lockfiles themselves change.
COPY package.json package-lock.json ./
COPY scripts/whatsapp-bridge/package.json scripts/whatsapp-bridge/package-lock.json scripts/whatsapp-bridge/
COPY web/package.json web/package-lock.json web/

RUN npm install --prefer-offline --no-audit && \
    npx playwright install --with-deps chromium --only-shell && \
    (cd scripts/whatsapp-bridge && npm install --prefer-offline --no-audit) && \
    (cd web && npm install --prefer-offline --no-audit) && \
    npm cache clean --force

# ---------- Source code ----------
# .dockerignore excludes node_modules, so the installs above survive.
COPY --chown=hermes:hermes . .

# Build web dashboard (Vite outputs to myai_cli/web_dist/)
RUN cd web && npm run build

# ---------- Python virtualenv ----------
# `.[all]` pulls in every optional extra — including [messaging] and [slack],
# which install slack-bolt + slack-sdk for the Slack Socket Mode adapter
# (gateway/platforms/slack.py). Don't narrow this to a subset without
# adding the messaging extras back explicitly; the image is meant to
# boot any platform the user configures via `myai setup`.
RUN chown hermes:hermes /opt/hermes
USER hermes
RUN uv venv && \
    uv pip install --no-cache-dir -e ".[all]"

# Defensive check: fail the build if the Slack adapter's imports aren't
# satisfied — catches a regression where someone removes [messaging]/[slack]
# from the `all` extra in pyproject.toml.
RUN .venv/bin/python -c "import slack_bolt, slack_sdk; print('slack deps OK')"

# ---------- Runtime ----------
ENV MYAI_AGENT_WEB_DIST=/opt/hermes/myai_cli/web_dist
ENV MYAI_HOME=/opt/data
VOLUME [ "/opt/data" ]
ENTRYPOINT [ "/opt/hermes/docker/entrypoint.sh" ]
