# run.py
import threading
import main
import admin_bot

def run_main_bot():
    main.main()

def run_admin_bot():
    admin_bot.main()

if __name__ == '__main__':
    print("🚀 در حال راه‌اندازی ربات‌ها...")
    
    # اجرای ربات اصلی در یک رشته جداگانه
    main_thread = threading.Thread(target=run_main_bot)
    main_thread.daemon = True
    main_thread.start()
    
    # اجرای ربات ادمین در رشته اصلی
    run_admin_bot()