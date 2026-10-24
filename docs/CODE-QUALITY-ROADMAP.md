# Code Quality Roadmap — Motes

## Engineering Standards

Motes follows production-grade engineering practices inherited from our Cogentrex architecture:

### Observability
- **Structured logging** via structlog — JSON format with correlation IDs, no `print()`
- **Distributed tracing** via OpenTelemetry — every LLM call, tool execution, and API request is traced
- **Jaeger integration** for trace visualization and performance analysis
- **Redaction processor** — automatic PII and token scrubbing in logs

### Architecture Patterns
- **Dependency Injection** — tool registry, LLM provider, and service layer injected via FastAPI `Depends()`
- **Event-driven** — SSE event bus for real-time proactive notifications
- **Async-first** — SQLAlchemy async sessions, httpx async clients, asyncio throughout
- **ContextVar correlation IDs** — trace a request across service boundaries

### Testing Strategy

| Layer | Framework | Focus |
|-------|-----------|-------|
| Backend unit | pytest (`@pytest.mark.unit`) | Business logic, tool execution |
| Backend integration | pytest + httpx | API endpoints, database |
| Frontend | vitest + @testing-library/svelte | Component rendering, API mocking |
| iOS | XCTest | ViewModel logic, URL consistency |

Test patterns:
- Minimal FastAPI app per test file — only required `app.state` attributes
- External services mocked (httpx, WebSocket, LLM providers)
- TDD cycle: write test → red → implement → green → refactor

### Security Practices
- JWT authentication with configurable secret key
- OAuth2 flows with automatic token refresh
- No secrets in code, logs, or commits
- Path validation for file system access tools
- CORS configuration per deployment environment

## Improvement Roadmap

### Done
- [x] structlog migration (all modules)
- [x] OTEL instrumentation (FastAPI, SQLAlchemy, custom spans)
- [x] Correlation ID middleware
- [x] DI-based tool registry

### In Progress
- [ ] Increase backend test coverage to 80%+
- [ ] CSRF protection for web frontend
- [ ] API key rotation support
- [ ] Audit log for security-sensitive events
