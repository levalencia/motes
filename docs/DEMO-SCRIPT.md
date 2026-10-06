# Motes Demo Video Script — LinkedIn (3 minutes)

## HOOK (0:00 - 0:15)
**[Screen: OpenAI Dots pricing page showing $200/month]**

"OpenAI charges $200 a month for Dots — their always-on AI agent.
It only works with GPT-6, it's blocked in Europe, and your data
lives on their servers. I built an open-source alternative that
runs on YOUR Mac, uses ANY model, and costs zero. Let me show you."

**[Cut to: Motes web app, dark theme, mascot visible]**

---

## ACT 1: Chat + Tools + Language Switch (0:15 - 0:50)

**[Web browser — Motes dashboard]**

"This is Motes. One conversation thread — just like Dots.
Let me ask it something."

**Type:** "cuál es el clima en Bruselas?"

**[Agent responds in Spanish paisa with weather data, emoji table]**

"Colombian Spanish — because that's my personality setting.
But watch this..."

**Type:** "now tell me the same in English"

**[Agent switches to English seamlessly]**

**Type:** "et en français?"

**[Agent switches to French]**

"Three languages, one conversation, zero configuration.
It detects your language and adapts instantly.

Now let me show the tools..."

**Type:** "crea un recordatorio para mañana comprar leche"

**[Approval card appears in thread: 🔐 Create a reminder in Apple Reminders]**

"See that? It asks permission before touching my data.
I click Approve..."

**[Click Approve — reminder created]**

"...and it created a real Apple Reminder on my Mac.
Gmail, Calendar, Notes, Reminders — all native Mac tools."

---

## ACT 2: Voice Call (0:45 - 1:15)

**[Switch to iPhone — Motes app with mascot icon]**

"Same app on my iPhone. Same conversation thread.
Let me call it."

**[Tap Call tab — ringing animation — connected]**

**Say:** "Oye Motes, dame las noticias de Colombia de hoy"

**[Agent responds in voice — Colombian Spanish — with news]**

"Real-time voice with sub-second latency. Echo cancellation,
semantic turn detection. And watch — when I ask it to do
something risky..."

**Say:** "Manda un email a mi jefe diciendo que llego tarde"

**[Agent says: "¿Quieres que lo mande? Dime sí o no"]**

"It asks permission — verbally. Same approval system,
adapted for voice. I say no."

**Say:** "No, no lo mandes"

**[Agent: "Entendido, no lo envío"]**

---

## ACT 3: Proactive + Scheduled (1:15 - 1:45)

**[Switch back to web — scroll thread]**

"Now here's where it gets interesting. See these messages
I didn't ask for?"

**[Point to 💡 PROACTIVE messages and ⏰ SCHEDULED TASK messages]**

"The 💡 ones — Motes decided ON ITS OWN to tell me about
a transport strike in Brussels. It checked my context,
saw I asked about weather earlier, and proactively warned me.

The ⏰ ones — those are scheduled tasks I set up.
'Give me Belgium and Colombia news every day at 7pm.'
It runs automatically, results appear right here in the thread.

And I control it all through conversation:
'Stop sending me weather updates' — it stops.
'Only once a day' — it adjusts. No settings page needed."

---

## ACT 4: MCP + Vision (1:45 - 2:15)

**[Settings page — MCP Integrations section]**

"MCP — Model Context Protocol. I connected a filesystem server
and ship.page. Watch the tools it discovered."

**[Click Test on filesystem — shows ✓ 14 tools with examples]**

"14 tools from one server. Any MCP server works — GitHub,
Postgres, Notion, Slack — hundreds available.

Back to chat..."

**Type:** "list the files in the project root"

**[Agent uses MCP filesystem tool, lists files]**

"And vision — I can attach a photo..."

**[Click 📎, pick a receipt photo]**

**Type:** "qué dice este recibo?"

**[Agent analyzes the receipt, extracts items and total]**

---

## ACT 5: The Pitch (2:15 - 2:45)

**[Split screen: Motes web + iPhone side by side]**

"Everything syncs. Chat on web, call on phone, scheduled tasks
run in the background — all in one thread.

Let me show you what's under the hood."

**[Quick flash: terminal showing test output]**

"284 tests. Python FastAPI backend, SvelteKit frontend,
native SwiftUI iOS app. structlog, OpenTelemetry, Jaeger traces.

**[GitHub repo page]**

"Fully open source. Self-hosted. Any model —
OpenAI, Anthropic, Ollama, Azure, whatever you want.
EU and UK friendly. Zero vendor lock-in."

---

## CLOSE (2:45 - 3:00)

**[Back to Motes dashboard, mascot visible]**

"OpenAI Dots: $200/month, GPT-6 only, US only, closed source.
Motes: free, any model, anywhere, open source.

Link in the comments. Star it on GitHub.
And if you build an MCP integration — submit a PR."

**[Screen: github.com/levalencia/motes — Star button]**

---

## RECORDING TIPS

1. **Screen record with OBS** — Mac + iPhone mirrored via QuickTime
2. **Record audio separately** — better quality than screen capture mic
3. **Edit in CapCut or DaVinci** — add captions, they boost engagement 3x
4. **Thumbnail**: split screen Motes vs Dots pricing with "FREE vs $200/mo"
5. **Post timing**: Tuesday or Thursday 8-9am CET
6. **First comment**: link to GitHub repo + "What integrations would you add?"

## PREP CHECKLIST

Before recording:
- [ ] Clear the thread (fresh start)
- [ ] Set personality to Paisa Colombiano
- [ ] Verify weather tool works
- [ ] Verify reminders approval works
- [ ] Verify voice call connects
- [ ] Verify MCP filesystem test shows 14 tools
- [ ] Have a receipt photo ready for vision demo
- [ ] iPhone on Tailscale, logged in, same thread visible
- [ ] Docker services running (postgres, redis, jaeger)
- [ ] Backend running on :8001
- [ ] No email notifications popping up mid-demo
