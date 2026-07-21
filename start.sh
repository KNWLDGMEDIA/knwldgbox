#!/bin/bash

echo "🚀 Starting KNWLDGBox..."

# Cleanup function to kill all background processes when the script stops (Ctrl+C)
cleanup() {
    echo -e "\n🛑 Stopping servers..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM and call the cleanup function
trap cleanup SIGINT SIGTERM

# Start the Backend using the knwldg virtual environment
echo "📡 Starting Backend (FastAPI)..."
bash -c "source knwldg/bin/activate && cd backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000" &

# Start the Frontend
echo "💻 Starting Frontend (Vue/Vite)..."
cd app && npm run dev
