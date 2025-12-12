# migrate_database.py
import sqlite3
import os

def migrate_database():
    """مهاجرت دستی دیتابیس"""
    
    if not os.path.exists("football_league.db"):
        print("⚠️ فایل دیتابیس پیدا نشد!")
        return
    
    # اتصال به دیتابیس
    conn = sqlite3.connect("football_league.db")
    cursor = conn.cursor()
    
    try:
        print("🔄 در حال مهاجرت دیتابیس...")
        
        # 1. ذخیره داده‌های فعلی
        cursor.execute("SELECT * FROM users")
        users_data = cursor.fetchall()
        
        cursor.execute("SELECT * FROM leagues")
        leagues_data = cursor.fetchall()
        
        cursor.execute("SELECT * FROM champions")
        champions_data = cursor.fetchall()
        
        print(f"📊 اطلاعات ذخیره شده: {len(users_data)} کاربر، {len(leagues_data)} لیگ، {len(champions_data)} قهرمان")
        
        # 2. حذف جدول‌های قدیمی
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS leagues")
        cursor.execute("DROP TABLE IF EXISTS champions")
        
        # 3. ایجاد جدول‌های جدید با ساختار به‌روز
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT,
            league_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues (id),
            UNIQUE(user_id, league_id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS champions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            league_id INTEGER NOT NULL,
            game_id TEXT NOT NULL,
            display_name TEXT,
            set_by_admin INTEGER,
            set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues (id),
            UNIQUE(league_id)
        )
        ''')
        
        # 4. بازگردانی داده‌های leagues
        for league in leagues_data:
            cursor.execute(
                "INSERT INTO leagues (id, name, capacity, is_active, created_at) VALUES (?, ?, ?, ?, ?)",
                league
            )
        
        # 5. بازگردانی داده‌های users با تبدیل user_id به string
        for user in users_data:
            cursor.execute(
                "INSERT INTO users (id, user_id, username, league_id, joined_at) VALUES (?, ?, ?, ?, ?)",
                (user[0], str(user[1]), user[2], user[3], user[4])
            )
        
        # 6. بازگردانی داده‌های champions
        for champion in champions_data:
            cursor.execute(
                "INSERT INTO champions (id, league_id, game_id, display_name, set_by_admin, set_at) VALUES (?, ?, ?, ?, ?, ?)",
                champion
            )
        
        conn.commit()
        print("✅ مهاجرت دیتابیس با موفقیت انجام شد!")
        
    except Exception as e:
        print(f"❌ خطا در مهاجرت: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()