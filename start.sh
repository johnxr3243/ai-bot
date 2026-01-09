#!/bin/bash

# Start both bot and web server
echo "🤖 Starting Discord Bot..."
python bot.py &
BOT_PID=$!

echo "🌐 Starting FastAPI Web Server..."
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &
WEB_PID=$!

echo "⏳ Both services started (Bot PID: $BOT_PID, Web PID: $WEB_PID)"

# Wait for all background processes
wait