# Motes

Open-source, model-agnostic, self-hosted personal AI agents.

**Your agents. Your models. Your data. Everywhere.**

Motes is an open-source alternative to [OpenAI Dots](https://openai.com/index/introducing-dots/) — always-on AI agents that connect to your email, calendar, GitHub, maps, and services to work autonomously on your behalf.

## Why Motes?

| | OpenAI Dots | Motes |
|--|-------------|-------|
| **Price** | $100+/mo | Free (self-hosted) |
| **Models** | GPT-6 only | Any: OpenAI, Anthropic, local, etc. |
| **EU/UK** | Blocked | Works everywhere |
| **Data** | OpenAI's servers | Your infrastructure |
| **Connectors** | 4,000 plugins (closed) | MCP ecosystem (open) |
| **Code** | Proprietary | MIT open source |

## Features

- **Model-agnostic** — plug in any LLM provider or run local models
- **Self-hosted** — Docker Compose one-command setup
- **MCP connectors** — Gmail, Calendar, GitHub, Maps, Slack, and growing
- **Approval system** — configurable auto/manual/never per action type
- **Persistent memory** — agents remember across sessions
- **Scheduled tasks** — cron-based autonomous background work
- **Multi-channel** — web UI, Telegram, Discord, Slack, email
- **Activity view** — watch your agents work in real-time
- **Audit trail** — every action logged and inspectable

## Quick Start

```bash
git clone https://github.com/levalencia/motes.git
cd motes
cp .env.example .env  # configure your LLM provider
docker compose up
```

Open http://localhost:3000 and create your first agent.

## Architecture

Built on production patterns with 1200+ tests:

- **Policy Engine** — deterministic rules for what agents can/cannot do
- **Approval Broker** — human-in-the-loop for sensitive actions
- **MCP Runtime** — governed access to external services
- **Memory Service** — persistent, scoped, encrypted agent memory
- **Run Ledger** — append-only audit trail for every action

## Status

🚧 **Early development** — not production-ready yet.

See [Development Plan](docs/MASTER-PLAN.md) for the roadmap.

## License

MIT
