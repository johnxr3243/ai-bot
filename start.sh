#!/bin/bash

echo "===================="
echo "🚀 Starting AI Bot Services"
echo "===================="

# Start bot (with or without token)
echo "🤖 Starting Discord Bot..."
python bot.py &
BOT_PID=$!
echo "   Bot PID: $BOT_PID"

echo "🤖 Starting luxury_tickets..."
python luxury_tickets.py &
BOT_PID=$!
echo "   Bot PID: $BOT_PID"

# Start web server
echo "🌐 Starting FastAPI Web Server..."
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &
WEB_PID=$!
echo "   Web PID: $WEB_PID"

echo "===================="
echo "✅ Services started"
echo "===================="

# Wait for all background processes
wait