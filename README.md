# MyAIOne Agent ◆

<p align="center">
  <a href="https://docs.myai1.ai/"><img src="https://img.shields.io/badge/Docs-docs.myai1.ai-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://github.com/samuelmukoti/myai-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://myai1.ai"><img src="https://img.shields.io/badge/Part%20of-MyAIOne%20Rig-blueviolet?style=for-the-badge" alt="Part of MyAIOne Rig"></a>
</p>

**The self-improving AI agent at the core of the MyAIOne Rig.** It creates skills from experience, improves them during use, searches its own past conversations, and builds a deepening model of who you are across sessions. Runs inside your dedicated MyAIOne container alongside DevStation, or standalone on a $5 VPS, a GPU cluster, or serverless infrastructure.

Use any model you want — OpenAI, Anthropic, [OpenRouter](https://openrouter.ai) (200+ models), [NVIDIA NIM](https://build.nvidia.com), Google Gemini, [Hugging Face](https://huggingface.co), or your own endpoint. Switch with `myai model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Six terminal backends — local, Docker, SSH, Daytona, Singularity, and Modal. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, Atropos RL environments, trajectory compression for training the next generation of tool-calling models.</td></tr>
</table>

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/samuelmukoti/myai-agent/main/scripts/install.sh | bash
```

Works on Linux, macOS, WSL2, and Android via Termux. The installer handles the platform-specific setup for you.

> **Android / Termux:** On Termux, MyAIOne installs a curated `.[termux]` extra because the full `.[all]` extra currently pulls Android-incompatible voice dependencies.
>
> **Windows:** Native Windows is not supported. Please install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) and run the command above.
>
> **Inside DevStation:** If you have a MyAIOne Rig container provisioned via [myai1.ai](https://myai1.ai), `myai` is already on your PATH — just run it.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
myai              # start chatting!
```

---

## Getting Started

```bash
myai              # Interactive CLI — start a conversation
myai model        # Choose your LLM provider and model
myai tools        # Configure which tools are enabled
myai config set   # Set individual config values
myai gateway      # Start the messaging gateway (Telegram, Discord, etc.)
myai setup        # Run the full setup wizard (configures everything at once)
myai claw migrate # Migrate from OpenClaw (if coming from OpenClaw)
myai update       # Update to the latest version
myai doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://docs.myai1.ai/)**

## CLI vs Messaging Quick Reference

MyAIOne Agent has two entry points: start the terminal UI with `myai`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action | CLI | Messaging platforms |
|---------|-----|---------------------|
| Start chatting | `myai` | Run `myai gateway setup` + `myai gateway start`, then send the bot a message |
| Start fresh conversation | `/new` or `/reset` | `/new` or `/reset` |
| Change model | `/model [provider:model]` | `/model [provider:model]` |
| Set a personality | `/personality [name]` | `/personality [name]` |
| Retry or undo the last turn | `/retry`, `/undo` | `/retry`, `/undo` |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]` |
| Browse skills | `/skills` or `/<skill-name>` | `/skills` or `/<skill-name>` |
| Interrupt current work | `Ctrl+C` or send a new message | `/stop` or send a new message |
| Platform-specific status | `/platforms` | `/status`, `/sethome` |

For the full command lists, see the [CLI guide](https://docs.myai1.ai/user-guide/cli) and the [Messaging Gateway guide](https://docs.myai1.ai/user-guide/messaging).

---

## Documentation

All documentation lives at **[docs.myai1.ai](https://docs.myai1.ai/)**:

| Section | What's Covered |
|---------|---------------|
| [Quickstart](https://docs.myai1.ai/getting-started/quickstart) | Install → setup → first conversation in 2 minutes |
| [CLI Usage](https://docs.myai1.ai/user-guide/cli) | Commands, keybindings, personalities, sessions |
| [Configuration](https://docs.myai1.ai/user-guide/configuration) | Config file, providers, models, all options |
| [Messaging Gateway](https://docs.myai1.ai/user-guide/messaging) | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://docs.myai1.ai/user-guide/security) | Command approval, DM pairing, container isolation |
| [Tools & Toolsets](https://docs.myai1.ai/user-guide/features/tools) | 40+ tools, toolset system, terminal backends |
| [Skills System](https://docs.myai1.ai/user-guide/features/skills) | Procedural memory, Skills Hub, creating skills |
| [Memory](https://docs.myai1.ai/user-guide/features/memory) | Persistent memory, user profiles, best practices |
| [MCP Integration](https://docs.myai1.ai/user-guide/features/mcp) | Connect any MCP server for extended capabilities |
| [Cron Scheduling](https://docs.myai1.ai/user-guide/features/cron) | Scheduled tasks with platform delivery |
| [Context Files](https://docs.myai1.ai/user-guide/features/context-files) | Project context that shapes every conversation |
| [Architecture](https://docs.myai1.ai/developer-guide/architecture) | Project structure, agent loop, key classes |
| [Contributing](https://docs.myai1.ai/developer-guide/contributing) | Development setup, PR process, code style |
| [CLI Reference](https://docs.myai1.ai/reference/cli-commands) | All commands and flags |
| [Environment Variables](https://docs.myai1.ai/reference/environment-variables) | Complete env var reference |

---

## Migrating from OpenClaw

If you're coming from OpenClaw, MyAIOne Agent can automatically import your settings, memories, skills, and API keys.

**During first-time setup:** The setup wizard (`myai setup`) automatically detects `~/.openclaw` and offers to migrate before configuration begins.

**Anytime after install:**

```bash
myai claw migrate              # Interactive migration (full preset)
myai claw migrate --dry-run    # Preview what would be migrated
myai claw migrate --preset user-data   # Migrate without secrets
myai claw migrate --overwrite  # Overwrite existing conflicts
```

What gets imported:
- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.hermes/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs)
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

See `myai claw migrate --help` for all options, or use the `openclaw-migration` skill for an interactive agent-guided migration with dry-run previews.

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://docs.myai1.ai/developer-guide/contributing) for development setup, code style, and PR process.

Quick start for contributors — clone and go with `setup-myai.sh`:

```bash
git clone https://github.com/samuelmukoti/myai-agent.git
cd myaione-agent
./setup-myai.sh     # installs uv, creates venv, installs .[all], symlinks ~/.local/bin/myai
./hermes              # auto-detects the venv (compat wrapper; calls myai)
```

Manual path (equivalent to the above):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv venv --python 3.11
source venv/bin/activate
uv pip install -e ".[all,dev]"
python -m pytest tests/ -q
```

> **RL Training (optional):** To work on the RL/Tinker-Atropos integration:
> ```bash
> git submodule update --init tinker-atropos
> uv pip install -e "./tinker-atropos"
> ```

---

## Community

- 🌐 [myai1.ai](https://myai1.ai) — MyAIOne Rig home
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/samuelmukoti/myai-agent/issues)
- 💡 [Discussions](https://github.com/samuelmukoti/myai-agent/discussions)

---

## Inspiration & Credits

MyAIOne Agent draws on the ideas and lineage of several projects that came before it:

- **[Hermes Agent](https://github.com/NousResearch/hermes-agent)** by [Nous Research](https://nousresearch.com) — the agent core this project was originally forked from, and where much of the tool-calling and skills architecture was first explored.
- **[OpenClaw](https://github.com/openclaw/openclaw)** — an inspiration for the messaging-gateway, personality, and migration model. MyAIOne Agent ships a `claw migrate` command to import OpenClaw installations.
- **[Pi Agent Harness](https://github.com/badlogic/pi-mono)** (`pi-mono`) — a minimalist agent-harness reference that informed the shape of the runtime loop and harness boundaries.

Thanks to the authors and communities behind each of these for the prior art.

---

## License

MIT — see [LICENSE](LICENSE).

Part of the **MyAIOne Rig**.
