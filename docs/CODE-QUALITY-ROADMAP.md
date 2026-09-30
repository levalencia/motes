# Code Quality Roadmap — Motes

## Current State (audit results)

| Metric | Value | Target |
|--------|-------|--------|
| print() statements | 18 | 0 |
| Files using structlog | 4/42 | 42/42 |
| Test coverage (files) | 10/42 (24%) | 42/42 (100%) |
| OTEL spans instrumented | 0 | All routes + LLM + tools |
| Inline imports in handlers | 63 | 0 (use DI) |
| Security findings | 8 | 0 |

## Phase Q1: Observability (logging + tracing)

### 1. Replace all print() with structlog
- Module-level `logger = structlog.get_logger()` in every file
- Event-style: `logger.info("realtime_call_connected", user_id=uid, url=url[:50])`
- Never string interpolation in log messages

### 2. Logging pipeline (from Archon)
- ContextVar-based correlation IDs
- CorrelationIdMiddleware on every request
- Redaction processor (passwords, tokens, PII)
- JSON renderer in prod, colored console in dev

### 3. OTEL instrumentation
- FastAPI auto-instrumentation (`opentelemetry-instrumentation-fastapi`)
- SQLAlchemy instrumentation
- Custom spans: `trace_llm_call()`, `trace_tool_call()`, `trace_agent_run()`
- GenAI semantic conventions for LLM calls

## Phase Q2: Dependency Injection

### 1. Tool registry as DI
- `ToolRegistry` built in lifespan, stored on `app.state.tools`
- Route handlers get it via `Depends(get_tool_registry)`
- No more inline tool construction in chat/voice routes

### 2. Service layer
- `get_google_tools(session, user_id)` → returns list of tools
- `get_voice_config(session)` → returns realtime URL/key
- All injected via `Depends()`, not inline imports

### 3. Provider factory as DI
- LLM provider selection via `Depends(get_llm_provider)`
- Voice provider via `Depends(get_voice_provider)`

## Phase Q3: Testing

### 1. Priority test targets (by risk)
- routes/chat.py — core feature
- routes/realtime_call.py — complex WebSocket
- agent_loop.py + agent_loop_anthropic.py — LLM integration
- proactive.py — pattern extraction
- google_tools.py — external API
- file_tools.py — filesystem access (security-sensitive)

### 2. Test patterns (from Archon)
- Minimal FastAPI app per test file
- Only set required `app.state` attributes
- Mock external services (httpx, WebSocket)
- `@pytest.mark.unit` / `@pytest.mark.integration`

## Phase Q4: Security

### 1. Critical
- [ ] Remove hardcoded JWT secret default (require MOTES_SECRET_KEY env)
- [ ] Auth on /api/providers/test endpoint
- [ ] Rate limiting middleware (login, API endpoints)

### 2. Important
- [ ] Symlink-safe path validation for file tools
- [ ] WebSocket auth before accept (not after)
- [ ] SecretStr for sensitive config fields

### 3. Nice to have
- [ ] CSRF protection
- [ ] API key rotation support
- [ ] Audit log for security events
