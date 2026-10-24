# Motes — Competitive Analysis & Feature Report

## Competitor Landscape

| | OpenAI Dots | Meta Muse | Grok Bots (xAI) | OpenClaw (OSS) | **Motes** |
|---|---|---|---|---|---|
| Price | $200/mo | Free | Pro tier | Free (self-host) | **Free (self-host)** |
| Open Source | No | No | No | Yes | **Yes (MIT)** |
| Model Choice | GPT only | Llama only | Grok only | Any model | **Any model** |
| EU/UK Available | ❌ | ✅ | ✅ | ✅ | **✅** |
| Self-Hosted | ❌ | ❌ | ❌ | ✅ | **✅** |
| Always-On Agent | ✅ | ✅ | ✅ | ✅ | **✅** |
| Voice Calls | ✅ | ❌ | ❌ | ❌ | **✅** |
| Native iOS App | ❌ | ❌ | ❌ | ✅ | **✅** |
| Proactive Intelligence | ✅ | ✅ | ✅ | Partial | **✅** |
| Persistent Memory | ✅ | ✅ | Unknown | Partial | **✅** |
| Single Thread (Dots UX) | ✅ | ✅ | ✅ | ❌ | **✅** |

---

## Implemented Features (48)

### Core Platform
| Feature | Platforms | Notes |
|---|---|---|
| Model-agnostic (OpenAI, Anthropic, Azure, local) | Web + iOS | Azure AI Foundry + Anthropic format |
| Self-hosted / privacy-first | All | Docker Compose one-command |
| EU/UK available | All | No geo restrictions |
| Real-time voice calls | iOS | Semantic VAD, echo cancellation, streaming PCM16 |
| Native iOS app (SwiftUI) | iOS | Chat + call + services + settings |
| SvelteKit web frontend | Web | Dark theme, responsive |
| Single thread (Dots UX model) | Web + iOS | Chat + call + proactive unified |

### Intelligence
| Feature | Platforms | Notes |
|---|---|---|
| Proactive intelligence (agentic) | Web | LLM decides, user controls |
| Persistent memory (save/recall) | Web + iOS | memory_save, memory_recall tools |
| Pattern learning | Web | Multilingual keyword extraction |
| Background scanner | Web | Gmail/Calendar every 60s |
| Image/vision understanding | iOS | Camera + photo library + analysis |

### Integrations (20 services)
| Feature | Status | Notes |
|---|---|---|
| Gmail (read/send) | ✅ OAuth | Auto-refresh tokens |
| Google Calendar (list/create) | ✅ OAuth | Auto-refresh tokens |
| GitHub | ✅ API key | Issues, PRs, repos |
| Slack | ✅ API key + webhook | Message send/receive |
| Weather | ✅ Built-in | Free, no API key |
| Web Search | ✅ Built-in | Brave or DuckDuckGo |
| Maps | ✅ Built-in | Directions, places |
| News | ✅ Built-in | Current headlines |
| Apple Reminders | ✅ AppleScript | macOS native |
| Apple Notes | ✅ AppleScript | macOS native |
| Local Files | ✅ Built-in | File system tools |
| Todoist | ✅ API key | Task management |
| Notion | ✅ API key | Page access |
| Spotify | ✅ API key | Playback control |
| Home Assistant | ✅ API key | Smart home |
| Outlook | ✅ API key | Email via Graph API |
| Flights & Hotels | ✅ Amadeus | Travel search |
| Telegram | ✅ Bot token | Webhook messaging |
| MCP servers (stdio) | ✅ | Community connectors |
| MCP servers (HTTP) | ✅ | Proxy service |

### Voice & Audio
| Feature | Status | Notes |
|---|---|---|
| Voice calls (real-time) | ✅ | Azure OpenAI Realtime API |
| Semantic VAD | ✅ | Knows when you stop talking |
| Echo cancellation | ✅ | AVAudioEngine on iOS |
| Voice personality | ✅ | Per-user customizable |
| Edge TTS (free) | ✅ | Default TTS provider |
| Local STT (faster-whisper) | ✅ | Free, no API key |
| Live captions in calls | ✅ | Real-time transcription |

### Platform Features
| Feature | Status | Notes |
|---|---|---|
| Approval system | ✅ Web + iOS | Card-based approve/deny |
| Scheduled tasks (cron) | ✅ Web + iOS | Create, pause, delete, run |
| Personality presets | ✅ Web | 6 presets + custom |
| OAuth consent flows | ✅ | Google, GitHub, Slack |
| Structured logging | ✅ | structlog JSON + PII redaction |
| OTEL observability | ✅ | Jaeger distributed traces |
| Alembic migrations | ✅ | Async DB schema management |
| CI/CD pipeline | ✅ | GitHub Actions |
| Auto-refresh sync | ✅ | 30s polling web + iOS |

---

## Test Coverage

| Platform | Framework | Tests | Status |
|---|---|---|---|
| Backend | pytest | 172+ | ✅ All passing |
| Frontend | vitest | 32 | ✅ All passing |
| iOS | XCTest | 28+ | ✅ All passing |
| **Total** | | **229+** | **✅** |

---

## Competitive Advantages

1. **Free** vs $200/month (OpenAI Dots)
2. **Any model** vs vendor-locked (GPT, Llama, Grok)
3. **EU/UK available** vs blocked (Dots)
4. **Self-hosted** — your data stays on your server
5. **Voice calls + native iOS** — no other OSS alternative has both
6. **Proactive intelligence** — agentic background scanning with pattern learning
7. **20 integrations** out of the box with MCP extensibility
8. **Production architecture** — structlog, OTEL, async SQLAlchemy, TDD

## Planned Features

| Feature | Priority | Effort |
|---|---|---|
| Microsoft Graph OAuth | High | Medium |
| Multiple agents per user | Medium | Medium |
| Android app | Medium | High |
| Activity view (live agent work) | Medium | Easy |
| Offline/local-only mode | Medium | Medium |
| Plugin marketplace | Low | High |
