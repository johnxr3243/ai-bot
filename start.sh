#!/bin/bash

# تشغيل البوت
python bot.py &

# تشغيل الويب
python -m uvicorn main:app --host 0.0.0.0 --port $PORT