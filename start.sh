#!/bin/bash

# تشغيل البوت في الخلفية مع تفعيل الـ Unbuffered mode للـ Logs
python -u bot.py 


# تشغيل الموقع (وهو ده اللي Railway هيراقبه)
python -u main.py