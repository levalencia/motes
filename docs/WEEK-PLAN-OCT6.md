# Motes — Week Plan (Oct 6-10, 2026)

## Monday: Finish testing today's features
- [ ] Scheduled tasks: verify both tasks run on time, results in thread
- [ ] Approval: test deny flow on web ("manda un email a test@test.com" → Deny)
- [ ] Approval: test on iPhone (create reminder → card appears → approve/deny)
- [ ] iOS: verify pull-to-refresh, refresh button, scroll-to-bottom
- [ ] iOS voice call: test with Gemini echo cancellation fixes
- [ ] Proactive: verify it respects "solo una vez al dia" instruction
- [ ] Fix any bugs found during testing

## Tuesday: Quality & polish
- [ ] Auto-refresh every 30s on web + iOS (keep in sync)
- [ ] SSE proactive push working live (no manual refresh needed)
- [ ] Fix any remaining settings page issues
- [ ] Add vitest smoke tests for dashboard page
- [ ] Run full test suite: 211 pytest + 32 vitest + iOS build

## Wednesday: Close gaps — MCP + integrations
- [ ] Install and test a real MCP server (e.g. @modelcontextprotocol/server-filesystem)
- [ ] Test MCP UI: add server, test connection, see discovered tools
- [ ] Rate limiting on API endpoints
- [ ] Activity view: show agent background work in UI (what's running, recent tool calls)

## Thursday: Close gaps — channels + vision
- [ ] Test incoming Telegram: create bot, set webhook, send message
- [ ] Test incoming Slack: create app, set webhook, send message
- [ ] Image/vision understanding: add GPT-4V/Claude Vision tool
- [ ] File upload endpoint for document analysis

## Friday: Multiple agents + docs + release prep
- [ ] Multiple agents support (work agent, personal agent)
- [ ] Update README with all new features
- [ ] Update COMPETITIVE-ANALYSIS.md with new score (target: 35/45)
- [ ] Tag v0.2.0 release on GitHub
- [ ] Write a launch post for Reddit/HN

## Current score: 28/45 features → Target: 35/45 by Friday
