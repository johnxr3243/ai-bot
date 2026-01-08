#!/bin/bash

# تشغيل البوت في الخلفية مع تفعيل الـ Unbuffered mode للـ Logs
python -u bot.py &

# انتظار بسيط للتأكد من بدء البوت
sleep 2

# تشغيل الموقع (وهو ده اللي Railway هيراقبه)
python -u main.py