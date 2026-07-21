#!/bin/bash

# Check if user provided a port, otherwise default to 5137
BACKEND_PORT=${1:-5137}

echo "🚀 Building and Deploying KNWLDGBox in Production Mode..."

# 1. Build the frontend static assets
echo "📦 Building Frontend (API Port: $BACKEND_PORT)..."
cd app
npm install
VITE_API_PORT=$BACKEND_PORT npm run build
cd ..

# 2. Kill any old instances using npx pm2
npx pm2 delete knwldgbox-backend knwldgbox-frontend 2>/dev/null

# 3. Start Backend via npx pm2
echo "📡 Launching Backend on port $BACKEND_PORT..."
npx pm2 start /home/altair/miniconda3/envs/knwldgbox/bin/python \
  --name "knwldgbox-backend" \
  --cwd "$(pwd)/backend" \
  -- -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT

echo "💻 Launching Frontend on port 5173..."
npx pm2 start npx --name "knwldgbox-frontend" -- serve -s app/dist -l 5173

echo "✅ Deployment complete! Both apps are running safely in the background."
echo "👉 Type 'npx pm2 status' to see them, or 'npx pm2 logs' to view terminal outputs."
