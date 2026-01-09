#!/bin/bash

# دالة لقتل العمليات عند الخروج
cleanup() {
    echo "Stopping processes..."
    kill $BOT_PID 2>/dev/null
    exit 0
}

# تسجيل دالة التنظيف للإشارات
trap cleanup SIGINT SIGTERM

# تشغيل البوت في الخلفية
python bot.py &
BOT_PID=$!

# تشغيل الويب
python -m uvicorn main:app --host 0.0.0.0 --port $PORT

# تنظيف عند الخروج
cleanup