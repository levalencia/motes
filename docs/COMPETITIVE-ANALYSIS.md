# Motes — Competitive Analysis & Feature Gap Report

## Competitor Landscape (Oct 2026)

| | OpenAI Dots | Meta Muse | Grok Bots (xAI) | OpenClaw (OSS) | **Motes** |
|---|---|---|---|---|---|
| Price | $200-500/mo | Free | Pro tier | Free (self-host) | **Free (self-host)** |
| Open Source | No | No | No | Yes (380k⭐) | **Yes** |
| Model Choice | GPT-6 only | Llama only | Grok only | Any model | **Any model** |
| EU/UK Available | ❌ No | ✅ | ✅ | ✅ | **✅** |
| Self-Hosted | ❌ | ❌ | ❌ | ✅ | **✅** |
| Always-On Agent | ✅ | ✅ | ✅ | ✅ | **✅** |
| Voice Calls | ✅ | ❌ | ❌ | ❌ | **✅** |
| iOS Native App | ❌ (ChatGPT) | ❌ (WhatsApp) | ❌ (X app) | ✅ | **✅** |
| Proactive/Agentic | ✅ | ✅ | ✅ | Partial | **✅** |
| Memory | ✅ | ✅ | Unknown | Partial | **✅** |
| Single Thread (Dots) | ✅ | ✅ | ✅ | ❌ | **✅** |

---

## Feature-by-Feature: What We Have vs What We Need

### ✅ HAVE — Already in Motes

| # | Feature | Status | Notes |
|---|---|---|---|
| 1 | Model-agnostic (OpenAI, Anthropic, Ollama, etc.) | ✅ Done | Our #1 differentiator |
| 2 | Self-hosted / privacy-first | ✅ Done | Docker Compose one-command |
| 3 | EU/UK available | ✅ Done | No geo restrictions |
| 4 | Real-time voice calls | ✅ Done | Azure Realtime API, semantic VAD |
| 5 | Native iOS app (SwiftUI) | ✅ Done | Chat + call + services + settings |
| 6 | SvelteKit web frontend | ✅ Done | Dark theme, responsive |
| 7 | Single thread (Dots model) | ✅ Done | Chat + call + proactive unified |
| 8 | Proactive intelligence (agentic) | ✅ Done | LLM decides, user controls via chat |
| 9 | Memory (save/recall facts) | ✅ Done | memory_save, memory_recall tools |
| 10 | 20 tool integrations | ✅ Done | Gmail, Calendar, Weather, News, etc. |
| 11 | Pattern learning | ✅ Done | Multilingual keyword extraction |
| 12 | Personality presets | ✅ Done | 6 presets, custom prompt, voice accent |
| 13 | Background scanner | ✅ Done | Gmail/Calendar every 60s |
| 14 | Echo cancellation (iOS calls) | ✅ Done | setVoiceProcessingEnabled |
| 15 | Markdown rendering | ✅ Done | Tables, code blocks, lists |
| 16 | Structured logging (structlog) | ✅ Done | JSON, correlation IDs, PII redaction |
| 17 | OTEL observability | ✅ Done | Jaeger traces |
| 18 | OAuth flows (Gmail/Calendar) | ✅ Done | Token refresh |
| 19 | Edge TTS (free) | ✅ Done | Default voice provider |
| 20 | Whisper STT (local) | ✅ Done | faster-whisper |

### 🟡 PARTIAL — Started but needs work

| # | Feature | Gap | Effort | Priority |
|---|---|---|---|---|
| 21 | Approval system | No UI — backend has concept but no "approve/deny" flow | Medium | High |
| 22 | Multi-channel (Slack/Teams) | Tools exist to send messages, but no INCOMING channel | Medium | High |
| 23 | Activity view | No log viewer in UI showing what agent is doing in background | Easy | Medium |
| 24 | SSE proactive push (live) | Backend publishes to event bus but frontend doesn't always receive | Easy | High |
| 25 | Phone calls (make calls) | Voice calls work iPhone→agent, but agent can't call businesses | Hard | Medium |

### ❌ MISSING — Not implemented yet

| # | Feature | What competitors have | Effort | Priority |
|---|---|---|---|---|
| 26 | **Cloud VM per agent** | Dots/Grok: each agent gets own computer, browser, filesystem | Very Hard | Low (we're local-first) |
| 27 | **Computer use** | Dots: can control user's laptop. Grok: logs into user's accounts | Very Hard | Low |
| 28 | **4000+ app integrations** | Dots: plugin ecosystem. We have 20 tools | Hard | High — MCP servers |
| 29 | **Slack/Teams as input channel** | Dots: user talks to agent FROM Slack. We only send TO Slack | Medium | High |
| 30 | **Multiple agents** | Dots: 1 per user (more planned). Users want specialized agents | Medium | Medium |
| 31 | **WhatsApp/Telegram channel** | Meta Muse: native WhatsApp. We have Telegram tool but no incoming | Medium | High |
| 32 | **Recurring scheduled tasks** | Dots: "check my stocks every morning". We have proactive but no scheduler | Easy | High |
| 33 | **File/document processing** | Dots: upload PDFs, analyze spreadsheets. We have basic file read | Medium | Medium |
| 34 | **Image understanding** | Dots/Muse: analyze photos, screenshots. We have no vision | Medium | Medium |
| 35 | **Code execution sandbox** | Dots: runs code in cloud VM. We have no sandbox | Hard | Low |
| 36 | **Team/shared agents** | Enterprise feature. One agent shared across team | Medium | Low |
| 37 | **Custom tool builder** | Let users create their own tools via UI | Medium | Medium |
| 38 | **SMS/text channel** | Dots: "coming soon". Would be useful for notifications | Easy | Low |
| 39 | **Mascot/avatar customization** | Dots: colorful blob with accessories. We have static mascot | Easy | Low |
| 40 | **Offline/local-only mode** | No cloud required at all (Ollama + local tools) | Medium | Medium |
| 41 | **Alembic migrations** | DB schema changes are manual ALTER TABLE | Easy | High |
| 42 | **CI/CD pipeline** | No GitHub Actions, no automated tests on PR | Easy | High |
| 43 | **Multi-user support** | Single user works, but no proper user isolation | Medium | Medium |
| 44 | **Rate limiting** | No API rate limiting, no abuse prevention | Easy | Medium |
| 45 | **Tauri desktop app** | Cross-platform desktop (macOS/Windows/Linux) | Medium | Medium |

---

## What Users LOVE about competitors (and we should copy)

1. **"It just works"** — Zero config for non-technical users. We need simpler onboarding.
2. **Persistent context** — Remembers everything. ✅ We have this (single thread + memory).
3. **Proactive without being asked** — ✅ We have this now.
4. **Multi-channel same context** — Talk via web, phone, Slack, same thread. We need incoming channels.
5. **Permission/approval model** — "Ask before doing X". We need this UI.

## What Users HATE about competitors (our opportunity)

1. **$200-500/month** → We're FREE and self-hosted
2. **No EU/UK** → We work everywhere
3. **Locked to one model** → We support any LLM
4. **Privacy concerns** → Our data stays on your server
5. **Vendor lock-in** → Open source, switch models anytime
6. **"Childish branding"** → Our mascot is tasteful 😊
7. **Can't make phone calls** → We already have voice calls!

---

## Recommended Roadmap (by priority)

### Phase 1 — Ship quality (1-2 weeks)
- [ ] Fix SSE proactive push (live updates in thread)
- [ ] Alembic migrations (proper DB versioning)
- [ ] CI/CD (GitHub Actions: lint + test on PR)
- [ ] Rate limiting on API endpoints
- [ ] Activity view (show agent background work in UI)

### Phase 2 — Growth features (2-4 weeks)
- [ ] MCP server support (unlock 100+ community integrations)
- [ ] Incoming Slack/Teams channel (talk to Motes FROM Slack)
- [ ] Incoming Telegram/WhatsApp channel
- [ ] Recurring scheduled tasks ("check stocks every morning")
- [ ] File upload + document analysis
- [ ] Approval system UI ("Motes wants to send this email. Allow?")

### Phase 3 — Differentiation (1-2 months)
- [ ] Image/vision understanding (GPT-4V, Claude Vision)
- [ ] Multiple agents (work agent, personal agent, coding agent)
- [ ] Custom tool builder (UI to create new integrations)
- [ ] Tauri desktop app (macOS/Windows/Linux)
- [ ] Offline mode (Ollama + local tools, zero cloud)

### Phase 4 — Enterprise (2-3 months)
- [ ] Multi-user with proper isolation
- [ ] Team/shared agents
- [ ] SSO (SAML/OIDC)
- [ ] Audit trail
- [ ] Admin dashboard
