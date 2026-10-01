# Motes — Your agents, your models, your data

<p align="center">
  <img src="frontend/static/mascot.png" alt="Motes Mascot" width="180" />
</p>

<p align="center">
  <strong>Open-source, model-agnostic, self-hosted personal AI agents.</strong><br/>
  An alternative to OpenAI Dots that works with any LLM, runs on your infrastructure, and respects your privacy.
</p>

<p align="center">
  <img src="frontend/static/logo.png" alt="Motes Logo" width="120" />
</p>

## Why Motes?

| Feature | OpenAI Dots | Motes |
|---|---|---|
| Model choice | GPT only | Any LLM (OpenAI, Anthropic, local) |
| Data location | OpenAI servers | Your server |
| EU/UK | Not available | Works everywhere |
| Integrations | Limited | 20 services, community-driven |
| Voice calls | Yes | Yes (Azure Realtime API) |
| iOS app | No | Native SwiftUI |
| Self-hosted | No | Docker Compose |
| Open source | No | MIT License |

## Features

### Chat
- SSE streaming responses with tool calling
- Markdown rendering (tables, code blocks, lists)
- Conversation history (rename, delete, resume)
- Proactive notifications IN the conversation

### Voice Calls
- Real-time voice via Azure OpenAI Realtime API
- Semantic VAD (knows when you're done talking)
- Echo cancellation on iOS
- Configurable voice personality and accent
- Speaker/earpiece toggle, mute, captions

### 20 Integrations
**Built-in (free):** Weather, Web Search, Apple Reminders, Apple Notes, Maps, News, Local Files

**OAuth:** Gmail, Google Calendar

**API Key:** GitHub, Slack, Todoist, Notion, Spotify, Home Assistant, Outlook, Flights & Hotels, Telegram

### Proactive Intelligence
- Background scanner checks Gmail/Calendar every 60 seconds
- Notifications appear directly in your conversation
- Pattern learning (knows when you check email)

### Memory
- Say "remember that I live in Brussels" — agent saves it persistently
- Memory works in both chat and voice calls
- Agent recalls facts when relevant to the conversation
- Memory categories: personal, work, preference, family, health

### How Proactive Works

```
Background Scanner (every 60s)
  ├─ scan_gmail() → new email? → notify in chat
  ├─ scan_calendar() → upcoming event? → notify in chat
  └─ check_patterns() → time-based suggestion? → notify in chat
                              │
               ┌──────────────┼──────────────┐
               │              │              │
          💬 Chat         📞 Voice Call    🔔 Stored
          (SSE push)      (TTS speech)    (for later)
```

**Pattern Learning**: Every message (chat or voice) is analyzed for topics.
After 3+ messages about "email" at the same hour, Motes proactively suggests
checking your inbox at that time.

**Memory Tools**: The agent has `memory_save` and `memory_recall` tools.
When you say "recuerda que mi hija se llama Victoria", the agent calls
`memory_save(fact="User's daughter is named Victoria", category="family")`.
Next time you ask about family, it recalls this fact.

### iOS Native App
- Pure SwiftUI (no WebView)
- Chat with streaming, voice calls with AVAudioEngine
- Connects via Tailscale HTTPS

## Quick Start

### Prerequisites
- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Node.js 20+, npm
- Docker & Docker Compose
- An LLM API key (OpenAI, Anthropic, Azure, or any OpenAI-compatible)

### 1. Clone and setup

```bash
git clone https://github.com/levalencia/motes.git
cd motes
```

### 2. Start infrastructure

```bash
docker compose up -d  # PostgreSQL + Redis + Jaeger
```

### 3. Start the backend

```bash
cd backend
cp .env.example .env  # Edit with your API keys
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

### 5. First login

Open http://localhost:5173. Create your account (first user = admin).

## Configuration

### Environment Variables

All config via `MOTES_` prefix or `.env` file in `backend/`:

```bash
# Required: at least one LLM provider
MOTES_DATABASE_URL=postgresql+asyncpg://motes:motes_dev@localhost:5433/motes
MOTES_REDIS_URL=redis://localhost:6380/0
MOTES_SECRET_KEY=your-secret-key-here  # Auto-generated if not set, but set it to survive restarts

# LLM Provider (example: Azure AI Foundry with Anthropic)
# Configure via the web UI at /providers
```

### LLM Providers

Motes needs at least one LLM provider to chat. Configure it via the **web UI** after first login:

1. Open `http://localhost:5173` and create your account
2. Go to **Settings** (gear icon)
3. Under **AI Provider**, fill in:

| Provider | Base URL | API Key | Model |
|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `sk-...` | `gpt-4o` |
| Anthropic | `https://api.anthropic.com/v1` | `sk-ant-...` | `claude-sonnet-4-20250514` |
| Azure AI Foundry | `https://your-resource.openai.azure.com/openai/deployments/your-deployment` | Azure key | `gpt-4o` |
| OpenRouter | `https://openrouter.ai/api/v1` | `sk-or-...` | `anthropic/claude-sonnet-4` |
| Ollama (local) | `http://localhost:11434/v1` | _(empty)_ | `llama3.1` |

4. Select **API Format**: `openai` for most providers, `anthropic` for Anthropic direct
5. Click **Save**

> **Quickest start**: Sign up at [OpenRouter](https://openrouter.ai) (free tier available), paste the API key, and pick any model.

### Voice Call Provider (Optional)

Voice calls require Azure OpenAI Realtime API. If you only need chat, skip this.

1. Create an [Azure OpenAI resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesOpenAI)
2. Deploy `gpt-4o-realtime-preview` or `gpt-realtime-2.1-mini` model
3. In the Motes web UI, go to **Settings**
4. Under **Realtime Voice Calls**, enter:
   - **WebSocket URL**: `wss://YOUR-RESOURCE.openai.azure.com/openai/v1/realtime?model=gpt-realtime-2.1-mini`
   - **API Key**: Your Azure OpenAI key (from Azure Portal → Keys and Endpoint)

| Model | Latency | Cost | Recommendation |
|---|---|---|---|
| `gpt-realtime-2.1-mini` | ~200ms | Low | Best for voice (fast + cheap) |
| `gpt-4o-realtime-preview` | ~400ms | High | Better reasoning, slower |

> **No Azure?** Voice calls won't work, but chat, tools, proactive — everything else works fine with any provider.

### Voice Personality

Set a custom voice personality per user. Go to **Settings** or call the API:

```bash
curl -X POST http://localhost:8001/api/voice/voice-personality \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"personality": "Colombian paisa accent, warm and casual"}'
```

### Connecting Services

Go to **Services** in the web UI:
- **Gmail/Calendar**: Click "Connect" → OAuth flow
- **GitHub/Slack/etc**: Click "Setup" → follow the guide → paste API key

## iOS App

### Prerequisites
- Xcode 26+ (iOS 26 SDK)
- Tailscale installed on both Mac and iPhone
- Tailscale HTTPS cert for your Mac

### Setup Tailscale HTTPS

The iOS app requires HTTPS (App Transport Security). Tailscale provides free, trusted HTTPS certs:

```bash
# Get your Tailscale domain
tailscale status --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['CertDomains'])"
# Output: ['your-machine.tailXXXXX.ts.net']

# Generate cert
cd backend
tailscale cert --cert-file ts-cert.pem --key-file ts-key.pem your-machine.tailXXXXX.ts.net

# Start backend with HTTPS
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload \
  --ssl-keyfile ts-key.pem --ssl-certfile ts-cert.pem
```

### Build and Run

```bash
cd MotesiOS/MotesiOS
open MotesiOS.xcodeproj
```

1. Select your iPhone as the build target
2. Build and Run (Cmd+R)
3. On the login screen, enter:
   - **Server URL**: `https://your-machine.tailXXXXX.ts.net:8001`
   - **Username/Password**: Your Motes credentials

### Troubleshooting iOS

**"App Transport Security" error**: The server must use HTTPS with a trusted cert. Use `tailscale cert` as described above. Self-signed certs do NOT work on iOS.

**"Agent not found" on Call tab**: Make sure you've created at least one agent (happens automatically on first login).

**Call audio not working**: Ensure microphone permission is granted. Echo cancellation requires `setVoiceProcessingEnabled(true)` on AVAudioEngine (already implemented).

**Login screen doesn't appear after reinstall**: Keychain persists across installs. The app auto-clears stale tokens when the server URL isn't configured.

## Viewing Logs

### Backend logs
```bash
# If running with tee
tail -f /tmp/motes-backend.log

# Or check uvicorn output directly
# Logs use structlog JSON format with correlation IDs
```

### Key log events
```
scanner_gmail_notification  — New email detected
event_bus_published         — Proactive notification sent
realtime_call_connected     — Voice call established
realtime_call_audio_forwarded — iOS audio forwarded to Azure
realtime_call_wav_sent      — Agent audio sent to client
realtime_call_tool_call     — Agent used a tool during call
```

### iOS logs
In Xcode console, look for `[Motes]` prefix:
```
[Motes] Audio sent OK: 12345 chars
[Motes] WebSocket send error: ...
```

## Architecture

```mermaid
graph TB
    subgraph Clients
        Web["🌐 SvelteKit<br/>:5173"]
        iOS["📱 iOS SwiftUI<br/>via Tailscale"]
        API["🔌 Any HTTP Client"]
    end

    subgraph Backend["FastAPI Backend :8001"]
        Chat["💬 Chat SSE<br/>Streaming"]
        Voice["📞 Voice WS<br/>Azure Realtime"]
        Tools["🔧 Tools (20)<br/>Gmail, Calendar,<br/>Weather, Maps..."]
        Memory["🧠 Memory<br/>Save & Recall"]
        Proactive["⚡ Proactive<br/>Scanner (60s)"]
        EventBus["📡 Event Bus<br/>Pub/Sub"]
        Logging["📊 structlog<br/>+ OTEL"]
    end

    subgraph Infrastructure
        PG["🐘 PostgreSQL<br/>:5433"]
        Redis["⚡ Redis<br/>:6380"]
        Jaeger["🔍 Jaeger<br/>:16687"]
    end

    subgraph External
        LLM["🤖 LLM Provider<br/>OpenAI / Anthropic / Azure"]
        AzureRT["🎙️ Azure Realtime<br/>gpt-realtime-2.1-mini"]
        Gmail["📧 Gmail API"]
        CalAPI["📅 Calendar API"]
    end

    Web --> Chat
    iOS --> Chat
    iOS --> Voice
    API --> Chat
    Chat --> Tools
    Chat --> Memory
    Voice --> Tools
    Voice --> Memory
    Voice --> AzureRT
    Chat --> LLM
    Proactive --> EventBus
    EventBus --> Chat
    EventBus --> Voice
    Proactive --> Gmail
    Proactive --> CalAPI
    Tools --> Gmail
    Tools --> CalAPI
    Backend --> PG
    Backend --> Redis
    Logging --> Jaeger
```

### Voice Call Pipeline

```mermaid
sequenceDiagram
    participant iPhone
    participant Backend
    participant Azure as Azure Realtime API

    iPhone->>Backend: WebSocket connect (wss://)
    iPhone->>Backend: {"type": "auth", "token": "..."}
    Backend->>Azure: WebSocket connect (wss://)
    Backend->>Azure: session.update (semantic_vad, 24kHz PCM16)
    Backend->>Azure: response.create (greeting)
    Azure-->>Backend: audio chunks (PCM16)
    Backend-->>iPhone: {"type": "audio_wav", "data": "base64..."}
    
    Note over iPhone: User speaks
    iPhone->>Backend: {"type": "audio", "data": "base64 PCM16 24kHz"}
    Backend->>Azure: input_audio_buffer.append
    Note over Azure: Semantic VAD detects end of speech
    Azure-->>Backend: response audio chunks
    Backend-->>iPhone: {"type": "audio_wav", "data": "base64..."}
    
    iPhone->>Backend: {"type": "end"}
    Backend->>Azure: close
```

### Proactive Intelligence Flow

```mermaid
flowchart LR
    Scanner["🔄 Background<br/>Scanner<br/>(every 60s)"]
    
    Scanner --> Gmail["📧 Gmail<br/>new emails?"]
    Scanner --> Cal["📅 Calendar<br/>upcoming events?"]
    Scanner --> Patterns["💡 Patterns<br/>time-based habits?"]
    
    Gmail --> Notify["📡 Event Bus"]
    Cal --> Notify
    Patterns --> Notify
    
    Notify --> Chat["💬 Chat<br/>(SSE push)"]
    Notify --> Voice["📞 Voice Call<br/>(TTS speech)"]
    Notify --> DB["💾 Database<br/>(for later)"]
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async), structlog, OTEL
- **Frontend**: SvelteKit 5, Tailwind v4, TypeScript
- **iOS**: SwiftUI, AVAudioEngine, URLSession
- **Database**: PostgreSQL with pgvector
- **Cache**: Redis
- **Observability**: Jaeger (traces), structlog (JSON logs)
- **Voice**: Azure OpenAI Realtime API, Edge TTS, faster-whisper

## Docker Ports

| Service | Port | Description |
|---|---|---|
| Backend | 8001 | FastAPI + WebSocket |
| Frontend | 5173 | SvelteKit dev server |
| PostgreSQL | 5433 | Database |
| Redis | 6380 | Cache |
| Jaeger | 16687 | Trace UI |

## Contributing

1. Fork the repo
2. Create a feature branch
3. Run tests: `cd backend && uv run pytest -m unit`
4. Run lint: `cd backend && uv run ruff check .`
5. Frontend check: `cd frontend && npx svelte-check`
6. Submit a PR

### Code Quality Standards
- **structlog** for all logging (no `print()`)
- **OTEL** spans for LLM and tool calls
- **TDD**: write test → red → implement → green
- **No secrets** in code, logs, or commits
- **Type hints** on all functions

## License

MIT
