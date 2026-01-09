#!/bin/bash

# تشغيل البوت والويب معاً بشكل متزامن
python bot.py &
BOT_PID=$!

# تشغيل الويب
python -m uvicorn main:app --host 0.0.0.0 --port $PORT &
WEB_PID=$!

# الانتظار حتى يتوقف أحد العمليات
wait -n
EXIT_CODE=$?

# قتل العملية الأخرى عند توقف إحداهما
kill $BOT_PID $WEB_PID 2>/dev/null

exit $EXIT_CODE