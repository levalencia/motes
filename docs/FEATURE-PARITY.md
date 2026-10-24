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
| Model-agnostic (any LLM) | ✗ (GPT only) | ✅ | OpenAI + Anthropic + Azure + local |
| Self-hosted | ✗ | ✅ | Docker Compose one-command setup |
| EU/UK available | ✗ | ✅ | Works everywhere |
| ReAct tool-calling loop | ✓ | ✅ | With streaming SSE |
| Streaming responses | ✓ | ✅ | Token-by-token SSE |
| Agent naming/identity | ✓ | ✅ | Name + system prompt + personality |
| Agent avatar/character | ✓ | ❌ | Dots has 3D blob characters |
| Multiple agents per user | Future | ✅ | Unlimited agents |

## Memory & Learning
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Persistent memory | ✓ | ✅ | CRUD + search + categories |
| Cross-session memory | ✓ | ✅ | Injected into system prompt |
| Memory from feedback | ✓ | ❌ | Auto-extract from conversations |
| View/edit individual memories | ✗ (Dots can't!) | ✅ | Full CRUD — we're ahead here |
| Memory categories | ✓ | ✅ | personal, work, preference, family, health |

## Connected Services
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Gmail (read/send) | ✓ | ✅ | OAuth + auto-refresh |
| Google Calendar | ✓ | ✅ | OAuth + auto-refresh |
| GitHub | ✓ | ✅ | API key tools |
| Slack | ✓ | ✅ | API key tools |
| Weather, Maps, News, Web Search | ✓ | ✅ | Built-in, no API key needed |
| Apple Reminders, Notes | ✗ | ✅ | AppleScript integration (macOS) |
| Todoist, Notion, Spotify | ✓ | ✅ | API key tools |
| Home Assistant | ✗ | ✅ | API key tools |
| Flights & Hotels | ✓ | ✅ | Amadeus API |
| MCP protocol support | ✗ | ✅ | stdio + HTTP transports |
| 4,000+ plugins | ✓ | ❌ | MCP ecosystem growing |
| OAuth consent screen flow | ✓ | ✅ | Google, GitHub, Slack |

## Approval System
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Action classification | ✓ | ✅ | safe / needs_approval / forbidden |
| Custom rules per tool | ✓ | ✅ | Per-agent, per-tool policies |
| Real-time approval UI | ✓ | ✅ | Web + iOS approval views |
| 4-level permission model | ✓ | ❌ | Dots: act freely / if asked / ask first / hand off |

## Scheduling
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Scheduled/recurring tasks | ✓ | ✅ | Cron expressions + CRUD |
| Task run history | ✓ | ✅ | Per-task run records |
| Pause/resume tasks | ✓ | ✅ | Full lifecycle |
| Background execution | ✓ | ✅ | Task runner with result delivery |

## Voice
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Voice calls (real-time) | ✓ | ✅ | Azure OpenAI Realtime API |
| Semantic VAD | ✓ | ✅ | Knows when you stop talking |
| Echo cancellation | ✓ | ✅ | AVAudioEngine on iOS |
| Voice personality | ✓ | ✅ | Configurable per user |
| Voice input (STT) | ✓ | ✅ | faster-whisper (local, free) |
| Voice output (TTS) | ✓ | ✅ | Edge TTS (free) + Azure |
| Live captions | ✓ | ✅ | Real-time transcription in call |

## Native Apps
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| iOS app | ✗ | ✅ | Native SwiftUI — no WebView |
| iOS voice calls | ✗ | ✅ | AVAudioEngine + WebSocket |
| iOS image/vision | ✗ | ✅ | Camera + photo library |
| Android app | ✗ | ❌ | Planned |

## UI / Web App
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Chat with streaming | ✓ | ✅ | Real-time token streaming |
| Markdown rendering | ✓ | ✅ | Bold, lists, code, tables |
| Provider management | ✓ | ✅ | Add/test/delete with validation |
| Agent management | ✓ | ✅ | Create/list/configure |
| Service connection UI | ✓ | ✅ | OAuth flow + setup guides |
| MCP server management | ✗ | ✅ | Add/remove/enable MCP servers |
| Voice settings | ✓ | ✅ | Voice provider + personality |
| Activity view (watch agent work) | ✓ | ❌ | See what agent is doing live |

## Proactive Intelligence
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Background monitoring | ✓ | ✅ | Gmail/Calendar scanner every 60s |
| Proactive notifications | ✓ | ✅ | In chat + voice calls via SSE |
| Pattern learning | ✓ | ✅ | Time-based habit detection |

## Vision
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Image understanding | ✓ | ✅ | Upload + analyze + respond |
| Camera capture (iOS) | ✗ | ✅ | PhotosPicker + camera |

## Advanced Features
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| Cloud VM per agent | ✓ | ❌ | Sandboxed execution environment |
| Proactive research mode | ✓ | 🟡 | Background scanning implemented |
| Multi-agent delegation | Future | ❌ | Agent-to-agent work sharing |
| Collaborative documents | ✓ | ❌ | Real-time human+agent editing |

## Security
| Feature | Dots | Motes | Status |
|---------|------|-------|--------|
| JWT authentication | ✓ | ✅ | Scrypt + JWT |
| OAuth for services | ✓ | ✅ | Google, GitHub, Slack |
| CORS protection | ✓ | ✅ | Configured per environment |
| Audit trail | ✓ | ✅ | Messages + tool calls logged |
| Token auto-refresh | ✓ | ✅ | Google OAuth automatic refresh |

## Scorecard
- **Implemented**: 48 features
- **Partially**: 1 feature
- **Not yet**: 7 features
- **Motes advantages**: Model-agnostic, self-hosted, EU/UK, native iOS app, editable memory, free local voice, MCP connectors, 20 integrations out of the box
