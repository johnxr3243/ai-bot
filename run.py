import multiprocessing
import os
import uvicorn

# وظيفة لتشغيل البوت
def run_bot():
    os.system("python bot.py")

# وظيفة لتشغيل الموقع
def run_web():
    from main import app
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    # تشغيل البوت في عملية منفصلة
    p1 = multiprocessing.Process(target=run_bot)
    p1.start()

    # تشغيل الموقع في العملية الرئيسية
    run_web()