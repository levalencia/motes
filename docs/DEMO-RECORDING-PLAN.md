# Motes Demo — Complete Recording Plan

## SETUP (do once, before any recording)

```
1. Clear the thread: Settings → Reset Everything
2. Docker: docker compose up -d (postgres, redis, jaeger)
3. Backend: cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
4. Frontend: cd frontend && npm run dev
5. Tailscale: tailscale serve --bg --https 443 http://localhost:8001
6. iPhone: logged in, same thread, Tailscale connected
7. Set personality: Paisa Colombiano
8. Have ready: a receipt photo on your phone, a grocery list idea
9. OBS: screen capture web browser + iPhone mirrored via QuickTime
10. Close Slack, email, notifications — clean desktop
```

---

## RECORDING SESSION 1: The main demo (record in one take, ~4 min raw)

Everything below is ONE continuous recording. No cuts needed.

```
SCENE 1: Hook (30 sec)
─────────────────────
[Show browser with OpenAI Dots pricing, or just say it]

SAY: "OpenAI charges $200 a month for Dots. GPT-6 only,
      blocked in Europe. I built an open-source alternative
      that runs on my Mac. Let me show you."

[Open Motes at localhost:5173 — clean empty thread]


SCENE 2: Email + Calendar (30 sec)
──────────────────────────────────
TYPE: "qué emails nuevos tengo?"
[Wait for response — shows real Gmail summary]

TYPE: "qué tengo en mi calendario esta semana?"
[Wait for response — shows real calendar events]

SAY: "Real Gmail. Real Google Calendar. Not fake data."


SCENE 3: Language switch (20 sec)
─────────────────────────────────
TYPE: "what's the weather in Brussels?"
[Agent responds in English]

TYPE: "et en français?"
[Agent responds in French]

SAY: "Three languages. Zero configuration."


SCENE 4: Approval + Mac tools (30 sec)
──────────────────────────────────────
TYPE: "crea un recordatorio para mañana comprar leche"
[Approval card appears: 🔐 Apple Reminders]

SAY: "It asks permission before touching my data."
[Click Approve]

SAY: "Real Apple Reminder. On my Mac. Synced to my iPhone."
[Optional: show Reminders app on Mac with the new reminder]


SCENE 5: Memory (30 sec)
────────────────────────
TYPE: "vivo en Bruselas con mi esposa Margot y mi hija Victoria que le encanta Paw Patrol"
[Agent responds warmly, calls memory_save]

TYPE: "qué clima hace hoy?"
[Agent responds with Brussels weather WITHOUT you saying Brussels]

SAY: "I didn't say Brussels. It remembered. Persistent memory,
      not just context window."


SCENE 6: Vision (20 sec)
───────────────────────
[Click 📎 attach button, pick receipt photo]
TYPE: "qué dice este recibo?"
[Agent analyzes receipt, extracts items and total]

SAY: "Photo analysis. Receipts, documents, screenshots — anything."


SCENE 7: MCP (20 sec)
────────────────────
TYPE: "list the files in the project root"
[Agent uses MCP filesystem, lists files]

SAY: "That's MCP — Model Context Protocol. I connected a
      filesystem server, it discovered 14 tools automatically.
      GitHub, Postgres, Notion — hundreds of MCP servers work."


SCENE 8: iPhone (30 sec)
───────────────────────
[Hold up iPhone or show QuickTime mirror]

SAY: "Same app on iPhone. Same thread. Watch..."
[Show thread on iPhone — same messages visible]

[Tap Call tab — ringing — connected]
SAY INTO PHONE: "Oye Motes, cuéntale un cuento a Victoria sobre Paw Patrol"
[Agent tells a Paw Patrol story IN VOICE — uses memory!]

SAY: "It remembered Victoria likes Paw Patrol. Voice call,
      real-time, sub-second latency."

[Hang up]


SCENE 9: Scheduled tasks (15 sec)
─────────────────────────────────
TYPE: "programa una tarea: dame las noticias de Colombia y Bélgica todos los días a las 7pm"
[Agent creates scheduled task]

SAY: "Every day at 7pm, it'll check the news and send me a summary.
      No settings page — I just told it what I want."


SCENE 10: Close (30 sec)
───────────────────────
SAY: "Let me recap what just happened in 3 minutes:
      - Read my real email and calendar
      - Three languages in one conversation
      - Created a real Apple Reminder with permission
      - Remembered personal facts across sessions
      - Analyzed a photo
      - Connected external tools via MCP
      - Voice call on iPhone with memory
      - Scheduled a daily task through conversation

      OpenAI Dots: $200 a month, GPT-6 only, US only.
      Motes: free, any model, anywhere, open source.

      Link in the comments. Star it on GitHub."

[Show github.com/levalencia/motes]
```

Total raw recording: ~4 minutes. Edit down to 3 by tightening waits.

---

## RECORDING SESSION 2: B-roll for proactive (record separately, 2 min)

This is the ONLY part that needs a separate recording,
because proactive messages take time to appear.

```
SETUP: Send a few messages first (weather, news) to give
       the proactive LLM context. Set proactive interval to
       5 minutes for recording.

THEN: Leave the app open for 5-10 minutes. Do something else.

RECORD: When the 💡 PROACTIVE message appears in the thread,
        start recording:
        - Show the thread with the proactive message visible
        - Scroll to show the 💡 message with timestamp

SAY: "I didn't ask for this. Motes saw I live in Brussels,
      checked the weather, and noticed a transport strike.
      It warned me on its own. That's proactive intelligence."

Also capture a ⏰ SCHEDULED TASK result if one runs during recording.
```

---

## EDITING PLAN (CapCut or DaVinci Resolve)

```
Timeline:

0:00-0:10  Hook (from Session 1, Scene 1)
0:10-0:35  Email + Calendar (Scene 2)
0:35-0:50  Language switch (Scene 3)
0:50-1:10  Approval + Mac tools (Scene 4)
1:10-1:30  Memory (Scene 5)
1:30-1:45  Vision (Scene 6)
1:45-2:00  MCP (Scene 7)
2:00-2:10  Proactive INSERT (from Session 2 B-roll)
2:10-2:30  iPhone + Voice call (Scene 8)
2:30-2:40  Scheduled tasks (Scene 9)
2:40-3:00  Close + GitHub (Scene 10)

ADD:
- Captions on every scene (3x engagement)
- Zoom effects on approval card, memory recall, proactive message
- Lower-third labels: "Gmail Integration", "Apple Reminders",
  "Persistent Memory", "MCP Protocol", "Proactive AI"
- Background music: lo-fi or tech ambient, very low
```

---

## PREP CHECKLIST (day of recording)

```
- [ ] Thread cleared (Reset Everything)
- [ ] Docker services running
- [ ] Backend running, no errors in logs
- [ ] Frontend running at localhost:5173
- [ ] iPhone on Tailscale, logged in
- [ ] Gmail OAuth token valid (send a test "qué emails tengo?")
- [ ] Calendar has real events this week
- [ ] Personality set to Paisa Colombiano
- [ ] MCP filesystem connected (check Settings → Test → ✓ 14 tools)
- [ ] Receipt photo ready on Mac (for vision demo)
- [ ] Proactive interval set to 5 min (for B-roll recording)
- [ ] OBS configured: browser + QuickTime iPhone mirror
- [ ] Desktop clean, dark mode, no notifications
- [ ] Mic tested (AirPods or external mic, not laptop mic)
- [ ] Practice the script once without recording
```
