# Motes vs OpenAI Dots — Feature Parity Tracker

## Legend
- ✅ = Implemented in Motes
- 🟡 = Partially implemented
- ❌ = Not yet built
- 🚫 = Not applicable (architectural difference)

## Core Agent
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Always-on AI agent | ✓ | ✅ | Agent persists across sessions |
| Model-agnostic (any LLM) | ✗ (GPT-6 only) | ✅ | OpenAI + Anthropic + any compatible |
| Self-hosted | ✗ | ✅ | Docker Compose one-command setup |
| EU/UK available | ✗ | ✅ | Works everywhere |
| ReAct tool-calling loop | ✓ | ✅ | With streaming SSE |
| Streaming responses | ✓ | ✅ | Token-by-token SSE |
| Agent naming/identity | ✓ | ✅ | Name + system prompt |
| Agent avatar/character | ✓ | ❌ | Dots has 3D blob characters |
| Multiple agents per user | Future | ✅ | Unlimited agents now |

## Memory & Learning
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Persistent memory | ✓ | ✅ | CRUD + search + categories |
| Cross-session memory | ✓ | ✅ | Injected into system prompt |
| Memory from feedback | ✓ | ❌ | Auto-extract from conversations |
| View/edit individual memories | ✗ (Dots can't!) | ✅ | Full CRUD — we're ahead here |

## Connected Services
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Gmail (read/send) | ✓ (plugin) | ✅ | OAuth + direct API tools |
| Google Calendar | ✓ (plugin) | ✅ | OAuth + direct API tools |
| GitHub | ✓ (plugin) | 🟡 | OAuth setup ready, tools not wired |
| Slack | ✓ (plugin) | 🟡 | OAuth setup ready, tools not wired |
| 4,000+ plugins | ✓ | ❌ | MCP catalog has 6, growing |
| OAuth consent screen flow | ✓ | ✅ | Google, GitHub, Slack |
| Service setup guides | ✓ | ✅ | Step-by-step with links |

## Approval System
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Action classification | ✓ | ✅ | safe / needs_approval / forbidden |
| Custom rules per tool | ✓ | ✅ | Per-agent, per-tool policies |
| Auto-review before actions | ✓ | 🟡 | Classification exists, not inline in loop yet |
| 4-level permission model | ✓ | ❌ | Dots: act freely / if asked / ask first / hand off |
| Mandatory approval (passwords, money) | ✓ | ❌ | Hard-coded sensitive action tiers |

## Scheduling
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Scheduled/recurring tasks | ✓ | ✅ | Cron expressions + CRUD |
| Task run history | ✓ | ✅ | Per-task run records |
| Pause/resume tasks | ✓ | ✅ | Full lifecycle |
| Background execution | ✓ | ❌ | Task runner not implemented yet |

## Voice
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Voice input (STT) | ✓ | ✅ | Mic button in chat |
| Voice output (TTS) | ✓ | ✅ | Listen button on responses |
| Voice provider settings | ✓ | ✅ | Settings page with presets |
| Voice calls | ✓ | ❌ | Real-time voice conversation |
| Provider-agnostic voice | ✗ (OpenAI only) | ✅ | Any OpenAI-compatible + Edge (free) |
| Free local TTS (Edge) | ✗ | ❌ | Can add edge-tts (free, no API key) |
| Free local STT (Whisper) | ✗ | ❌ | Can add faster-whisper (local) |

## UI / Web App
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Dashboard with stats | ✓ | ✅ | Agents, providers, services, status |
| Chat with streaming | ✓ | ✅ | Real-time token streaming |
| Markdown rendering | ✓ | ✅ | Bold, lists, code, headers |
| Provider management | ✓ | ✅ | Add/test/delete with validation |
| Agent management | ✓ | ✅ | Create/list/delete |
| Service connection UI | ✓ | ✅ | OAuth flow + setup guides |
| Voice settings | ✓ | ✅ | Voice provider CRUD |
| Activity view (watch agent work) | ✓ | ❌ | See what agent is doing live |
| Agent profile page | ✓ | ❌ | In progress / scheduled / completed |
| Approval inbox | ✓ | ❌ | Pending approvals dashboard |

## Multi-Channel
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Web UI | ✓ | ✅ | SvelteKit frontend |
| Slack bot | ✓ | ❌ | Planned Phase 2.4 |
| Telegram bot | ✗ | ❌ | Planned Phase 2.4 |
| Discord bot | ✗ | ❌ | Planned Phase 2.4 |
| Microsoft Teams | ✓ | ❌ | Planned Phase 2.4 |
| SMS/iMessage | ✓ (beta) | ❌ | Not planned |
| Email gateway | ✗ | ❌ | Planned Phase 2.4 |

## Advanced Features
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Cloud VM per agent | ✓ | ❌ | Sandboxed execution environment |
| Local computer access | ✓ | ❌ | Desktop app integration |
| Proactive research mode | ✓ | ❌ | Background monitoring of services |
| Multi-agent delegation | Future | ❌ | Agent-to-agent work sharing |
| Collaborative documents (Pages) | ✓ | ❌ | Real-time human+agent editing |
| Shared workspaces (Space) | ✓ | ❌ | Team + agent shared context |
| Specialist agents (enterprise) | ✓ | ❌ | Org-identity agents |

## Security
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| JWT authentication | ✓ | ✅ | Scrypt + JWT |
| OAuth for services | ✓ | ✅ | Google, GitHub, Slack |
| CORS protection | ✓ | ✅ | Configured |
| Audit trail (run ledger) | ✓ | 🟡 | Messages saved, no full run ledger |
| Encrypted token storage | ✓ | 🟡 | Stored but not yet encrypted at rest |

## Scorecard
- **Implemented**: 30 features
- **Partially**: 4 features
- **Not yet**: 22 features
- **Motes advantages**: Model-agnostic, self-hosted, EU/UK, editable memory, unlimited agents, provider-agnostic voice, free local voice options
