#!/usr/bin/env bash

# Start script for AI Agent Design Patterns Demo
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================="
echo "   AI Agent Design Patterns Playground - Launcher"
echo "========================================================="

# Check virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    ~/.local/bin/uv venv --python python3.10 .venv
    ~/.local/bin/uv pip install -r backend/requirements.txt
fi

# Function to stop background processes on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $(jobs -p) 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM EXIT

echo "Starting FastAPI Backend on http://localhost:8000 ..."
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Starting React Frontend on http://localhost:5173 ..."
cd frontend && npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

cd "$DIR"
echo ""
echo "Playground is ready:"
echo "  Frontend : http://localhost:5173"
echo "  Backend  : http://localhost:8000"
echo "  API Docs : http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

wait

