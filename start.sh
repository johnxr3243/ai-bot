#!/bin/bash

# تشغيل Discord bot في الخلفية
python bot.py &

# تشغيل FastAPI (العملية الرئيسية)
uvicorn main:app --host 0.0.0.0 --port $PORT
