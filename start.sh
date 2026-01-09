#!/bin/bash

# Start both bot and web server
python bot.py &
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} &

# Wait for all background processes
wait