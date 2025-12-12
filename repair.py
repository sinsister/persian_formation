# repair_database.py
import sqlite3
import os
from datetime import datetime

def backup_database():
    """ایجاد پشتیبان از دیتابیس"""
    if os.path.exists("league_bot.db"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"league_bot_backup_{timestamp}.db"
        
        import shutil
        shutil.copy2("league_bot.db", backup_name)
        print(f"✅ پشتیبان ایجاد شد: {backup_name}")
        return backup_name
    return None

def repair_database():
    """تعمیر کامل دیتابیس"""
    
    print("🔧 شروع تعمیر دیتابیس...")
    
    # 1. ایجاد پشتیبان
    backup_file = backup_database()
    
    # 2. خواندن داده‌های فعلی
    old_conn = sqlite3.connect("league_bot.db")
    old_cursor = old_conn.cursor()
    
    try:
        # خواندن لیگ‌ها
        old_cursor.execute("SELECT id, name, capacity, is_active, created_at FROM leagues")
        leagues_data = old_cursor.fetchall()
        print(f"📊 خواندن {len(leagues_data)} لیگ")
        
        # خواندن کاربران
        old_cursor.execute("SELECT id, user_id, username, league_id, joined_at FROM users")
        users_data = old_cursor.fetchall()
        print(f"📊 خواندن {len(users_data)} کاربر")
        
        # خواندن قهرمانان
        old_cursor.execute("SELECT id, league_id, game_id, display_name, set_by_admin, set_at FROM champions")
        champions_data = old_cursor.fetchall()
        print(f"📊 خواندن {len(champions_data)} قهرمان")
        
        old_conn.close()
        
        # 3. حذف فایل قدیمی
        os.remove("league_bot.db")
        print("🗑️ فایل دیتابیس قدیمی حذف شد")
        
        # 4. ایجاد دیتابیس جدید
        from database import Database
        db = Database()
        
        # 5. بازگردانی لیگ‌ها
        print("🔄 بازگردانی لیگ‌ها...")
        for league in leagues_data:
            try:
                db._execute_query(
                    "INSERT INTO leagues (id, name, capacity, is_active, created_at) VALUES (?, ?, ?, ?, ?)",
                    league,
                    commit=True
                )
            except:
                # اگر مشکل با ID داشت، بدون ID وارد کن
                db._execute_query(
                    "INSERT INTO leagues (name, capacity, is_active, created_at) VALUES (?, ?, ?, ?)",
                    league[1:],
                    commit=True
                )
        
        # 6. بازگردانی کاربران
        print("🔄 بازگردانی کاربران...")
        for user in users_data:
            try:
                db._execute_query(
                    "INSERT INTO users (id, user_id, username, league_id, joined_at) VALUES (?, ?, ?, ?, ?)",
                    user,
                    commit=True
                )
            except:
                db._execute_query(
                    "INSERT INTO users (user_id, username, league_id, joined_at) VALUES (?, ?, ?, ?)",
                    user[1:],
                    commit=True
                )
        
        # 7. بازگردانی قهرمانان
        print("🔄 بازگردانی قهرمانان...")
        for champ in champions_data:
            try:
                db._execute_query(
                    "INSERT INTO champions (id, league_id, game_id, display_name, set_by_admin, set_at) VALUES (?, ?, ?, ?, ?, ?)",
                    champ,
                    commit=True
                )
            except:
                db._execute_query(
                    "INSERT INTO champions (league_id, game_id, display_name, set_by_admin, set_at) VALUES (?, ?, ?, ?, ?)",
                    champ[1:],
                    commit=True
                )
        
        print("✅ دیتابیس با موفقیت تعمیر شد!")
        
        # بررسی نهایی
        db.check_and_fix_database()
        db.close()
        
        if backup_file:
            print(f"📁 پشتیبان در فایل: {backup_file}")
        
    except Exception as e:
        print(f"❌ خطا در تعمیر دیتابیس: {e}")
        
        # بازگردانی از پشتیبان
        if backup_file and os.path.exists(backup_file):
            print("🔄 بازگردانی از پشتیبان...")
            import shutil
            shutil.copy2(backup_file, "league_bot.db")
            print("✅ دیتابیس به حالت قبل بازگردانی شد")

if __name__ == "__main__":
    repair_database()