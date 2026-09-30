#!/usr/bin/env bash
# init.sh — Verify Motes development environment is healthy
set -euo pipefail

GREEN='[0;32m'
RED='[0;31m'
NC='[0m'

pass() { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo "=== Motes Environment Check ==="
echo

# 1. Python
python3 --version >/dev/null 2>&1 && pass "Python: $(python3 --version)" || fail "Python 3 not found"

# 2. uv
uv --version >/dev/null 2>&1 && pass "uv: $(uv --version)" || fail "uv not found (install: curl -LsSf https://astral.sh/uv/install.sh | sh)"

# 3. Node.js
node --version >/dev/null 2>&1 && pass "Node.js: $(node --version)" || fail "Node.js not found"

# 4. npm
npm --version >/dev/null 2>&1 && pass "npm: $(npm --version)" || fail "npm not found"

# 5. Docker
docker --version >/dev/null 2>&1 && pass "Docker: $(docker --version | head -1)" || fail "Docker not found"

# 6. Backend venv
if [ -d backend/.venv ]; then
    pass "Backend venv exists"
else
    echo "  Creating backend venv..."
    cd backend && uv venv --python python3.12 && uv sync --extra dev && cd ..
    pass "Backend venv created"
fi

# 7. Frontend node_modules
if [ -d frontend/node_modules ]; then
    pass "Frontend node_modules exists"
else
    echo "  Installing frontend deps..."
    cd frontend && npm install && cd ..
    pass "Frontend deps installed"
fi

# 8. Backend lint
echo
echo "--- Backend Lint ---"
cd backend && uv run ruff check . && cd .. && pass "Backend lint clean" || fail "Backend lint failed"

# 9. Backend tests
echo
echo "--- Backend Tests ---"
cd backend && uv run pytest -m unit -v && cd .. && pass "Backend tests passed" || fail "Backend tests failed"

# 10. Frontend check
echo
echo "--- Frontend Check ---"
cd frontend && npx svelte-kit sync && npx svelte-check --tsconfig ./tsconfig.json && cd .. && pass "Frontend check passed" || fail "Frontend check failed"

echo
echo "=== All checks passed! ==="
echo "Run 'make docker-up' to start services, then 'make dev' for the backend."
