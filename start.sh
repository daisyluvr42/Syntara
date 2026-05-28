#!/bin/bash
# Syntara — Start development servers
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_HOST="${SYNTARA_HOST:-127.0.0.1}"
BACKEND_PORT="${SYNTARA_PORT:-8888}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
export VITE_BACKEND_TARGET="${VITE_BACKEND_TARGET:-http://${BACKEND_HOST}:${BACKEND_PORT}}"

if [ -n "${PYTHON_BIN:-}" ]; then
    PYTHON_CMD="$PYTHON_BIN"
elif command -v python3.12 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3.12)"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="$(command -v python3)"
else
    echo "Python 3 is required but was not found on PATH."
    exit 1
fi

echo "=== Syntara Development Server ==="
echo ""

# Setup Python virtual environment
if [ ! -d ".venv" ]; then
    echo "[0/3] Creating Python 3.12 virtual environment..."
    "$PYTHON_CMD" -m venv .venv
fi
# Ensure Java (required by opendataloader-pdf) is on PATH
if [ -d "/opt/homebrew/opt/openjdk@21/bin" ]; then
    export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
fi

source .venv/bin/activate

# Check Python dependencies
echo "[1/3] Checking Python dependencies..."
pip install -q -r requirements.txt 2>/dev/null || {
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
}

# Check Node dependencies
echo "[2/3] Checking Node dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing Node dependencies..."
    cd frontend && npm install && cd ..
fi

# Start servers
echo "[3/3] Starting servers..."
echo ""
echo "  Backend:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "  Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "  API Docs: http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
echo ""

# Start backend in background
cd "$SCRIPT_DIR"
python -m uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload &
BACKEND_PID=$!

# Start frontend
cd "$SCRIPT_DIR/frontend"
npx vite --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

# Trap to kill both on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM EXIT

echo ""
echo "Press Ctrl+C to stop both servers"
wait
