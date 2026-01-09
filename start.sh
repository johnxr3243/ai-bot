#!/bin/bash

# تشغيل البوت والويب في نفس الوقت
# استخدام nohup لضمان استمرارية التشغيل

# تشغيل البوت في الخلفية
nohup python bot.py > bot.log 2>&1 &

# تشغيل الويب
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}