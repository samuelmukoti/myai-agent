# Ink Gateway TUI Migration — Post-mortem

Planned: 2026-04-01 · Delivered: 2026-04 · Status: shipped, classic (prompt_toolkit) CLI still present

## What Shipped

Three layers, same repo, Python runtime unchanged.

```
ui-tui (Node/TS)  ──stdio JSON-RPC──▶  tui_gateway (Py)  ──▶  AIAgent (run_agent.py)
```

### Backend — `tui_gateway/`

```
tui_gateway/
├── entry.py          # subprocess entrypoint, stdio read/write loop
├── server.py         # everything: sessions dict, @method handlers, _emit
├── render.py         # stream renderer, diff rendering, message rendering
├── slash_worker.py   # subprocess that runs hermes_cli slash commands
└── __init__.py
```

`server.py` owns the full runtime-control surface: session store (`_sessions: dict[str, dict]`), method registry (`@method("…")` decorator), event emitter (`_emit`), agent lifecycle (`_make_agent`, `_init_session`, `_wire_callbacks`), approval/sudo/clarify round-trips, and JSON-RPC dispatch.

Protocol methods (`@method(...)` in `server.py`):

- session: `session.{create, resume, list, close, interrupt, usage, history, compress, branch, title, save, undo}`
- prompt: `prompt.{submit, background, btw}`
- tools: `tools.{list, show, configure}`
- slash: `slash.exec`, `command.{dispatch, resolve}`, `commands.catalog`, `complete.{path, slash}`
- approvals: `approval.respond`, `sudo.respond`, `clarify.respond`, `secret.respond`
- config/state: `config.{get, set, show}`, `model.options`, `reload.mcp`
- ops: `shell.exec`, `cli.exec`, `terminal.resize`, `input.detect_drop`, `clipboard.paste`, `paste.collapse`, `image.attach`, `process.stop`
- misc: `agents.list`, `skills.manage`, `plugins.list`, `cron.manage`, `insights.get`, `rollback.{list, diff, restore}`, `browser.manage`

Protocol events (`_emit(…)` → handled in `ui-tui/src/app/createGatewayEventHandler.ts`):

- lifecycle: `gateway.{ready, stderr}`, `session.info`, `skin.changed`
- stream: `message.{start, delta, complete}`, `thinking.delta`, `reasoning.{delta, available}`, `status.update`
- tools: `tool.{start, progress, complete, generating}`, `subagent.{start, thinking, tool, progress, complete}`
- interactive: `approval.request`, `sudo.request`, `clarify.request`, `secret.request`
- async: `background.complete`, `btw.complete`, `error`

### Frontend — `ui-tui/src/`

```
src/
├── entry.tsx            # node bootstrap: bootBanner → spawn python → dynamic-import Ink → render(<App/>)
├── app.tsx              # <GatewayProvider> wraps <AppLayout>
├── bootBanner.ts        # raw-ANSI banner to stdout in ~2ms, pre-React
├── gatewayClient.ts     # JSON-RPC client over child_process stdio
├── gatewayTypes.ts      # typed RPC responses + GatewayEvent union
├── theme.ts             # DEFAULT_THEME + fromSkin
│
├── app/                 # hooks + stores — the orchestration layer
│   ├── uiStore.ts             # nanostore: sid, info, busy, usage, theme, status…
│   ├── turnStore.ts           # nanostore: per-turn activity / reasoning / tools
│   ├── turnController.ts      # imperative singleton for stream-time operations
│   ├── overlayStore.ts        # nanostore: modal/overlay state
│   ├── useMainApp.ts          # top-level composition hook
│   ├── useSessionLifecycle.ts # session.create/resume/close/reset
│   ├── useSubmission.ts       # shell/slash/prompt dispatch + interpolation
│   ├── useConfigSync.ts       # config.get + mtime poll
│   ├── useComposerState.ts    # input buffer, paste snippets, editor mode
│   ├── useInputHandlers.ts    # key bindings
│   ├── createGatewayEventHandler.ts  # event-stream dispatcher
│   ├── createSlashHandler.ts         # slash command router (registry + python fallback)
│   └── slash/commands/        # core.ts, ops.ts, session.ts — TS-owned slash commands
│
├── components/          # AppLayout, AppChrome, AppOverlays, MessageLine, Thinking, Markdown, pickers, prompts, Banner, SessionPanel
├── config/              # env, limits, timing constants
├── content/             # charms, faces, fortunes, hotkeys, placeholders, verbs
├── domain/              # details, messages, paths, roles, slash, usage, viewport
├── protocol/            # interpolation, paste regex
├── hooks/               # useCompletion, useInputHistory, useQueue, useVirtualHistory
└── lib/                 # history, messages, osc52, rpc, text
```

### CLI entry points — `hermes_cli/main.py`

- `hermes --tui`      → `node dist/entry.js` (auto-builds when `.ts`/`.tsx` newer than `dist/entry.js`)
- `hermes --tui --dev` → `tsx src/entry.tsx` (skip build)
- `MYAI_AGENT_TUI_DIR=…`  → external prebuilt dist (nix, distro packaging)

## Diverged From Original Plan

| Plan | Reality | Why |
|---|---|---|
| `tui_gateway/{controller,session_state,events,protocol}.py` | all collapsed into `server.py` | no second consumer ever emerged, keeping one file cheaper than four |
| `ui-tui/src/main.tsx` | split into `entry.tsx` (bootstrap) + `app.tsx` (shell) | boot banner + early python spawn wanted a pre-React moment |
| `ui-tui/src/state/store.ts` | three nanostores (`uiStore`, `turnStore`, `overlayStore`) | separate lifetimes: ui persists, turn resets per reply, overlay is modal |
| `approval.requested` / `sudo.requested` / `clarify.requested` | `*.request` (no `-ed`) | cosmetic |
| `session.cancel` | dropped | `session.interrupt` covers it |
| `HERMES_EXPERIMENTAL_TUI=1`, `display.experimental_tui: true`, `/tui on/off/status` | none shipped | `--tui` went from opt-in to first-class without an experimental phase |

## Post-migration Additions (not in original plan)

- **Async `session.create`** — returns sid in ~1ms, agent builds on a background thread, `session.info` broadcasts when ready; `_wait_agent()` gates every agent-touching handler via `_sess`
- **`bootBanner`** — raw-ANSI logo painted to stdout at T≈2ms, before Ink loads; `<AlternateScreen>` wipes it seamlessly when React mounts
- **Selection uniform bg** — `theme.color.selectionBg` wired via `useSelection().setSelectionBgColor`; replaces SGR-inverse per-cell swap that fragmented over amber/gold fg
- **Slash command registry** — TS-owned commands in `app/slash/commands/{core,ops,session}.ts`, everything else falls through to `slash.exec` (python worker)
- **Turn store + controller split** — imperative singleton (`turnController`) holds refs/timers, nanostore (`turnStore`) holds render-visible state

## What's Still Open

- **Classic CLI not deleted.** `cli.py` still has ~80 `prompt_toolkit` references; classic REPL is still the default when `--tui` is absent. The original plan's "Cut 4 · prompt_toolkit removal later" hasn't happened.
- **No config-file opt-in.** `HERMES_EXPERIMENTAL_TUI` and `display.experimental_tui` were never built; only the CLI flag exists. Fine for now — if we want "default to TUI", a single line in `main.py` flips it.
