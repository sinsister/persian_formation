# migrate_database.py
import sqlite3
import os

def migrate_database():
    """مهاجرت دیتابیس برای تغییر نوع فیلد user_id از INTEGER به TEXT"""
    
    if not os.path.exists("football_league.db"):
        print("⚠️ فایل دیتابیس پیدا نشد!")
        return
    
    print("🔄 در حال مهاجرت دیتابیس...")
    
    # اتصال به دیتابیس
    conn = sqlite3.connect("football_league.db")
    cursor = conn.cursor()
    
    try:
        # 1. بررسی ساختار فعلی
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print(f"📊 ساختار فعلی جدول users: {columns}")
        
        # 2. ایجاد جدول موقت با ساختار جدید
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT,
            league_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues (id),
            UNIQUE(user_id, league_id)
        )
        ''')
        
        # 3. کپی داده‌ها با تبدیل user_id به TEXT
        cursor.execute('''
        INSERT INTO users_new (id, user_id, username, league_id, joined_at)
        SELECT id, CAST(user_id AS TEXT), username, league_id, joined_at 
        FROM users
        ''')
        
        # 4. حذف جدول قدیمی
        cursor.execute("DROP TABLE users")
        
        # 5. تغییر نام جدول جدید
        cursor.execute("ALTER TABLE users_new RENAME TO users")
        
        conn.commit()
        print("✅ مهاجرت دیتابیس با موفقیت انجام شد!")
        
    except Exception as e:
        print(f"❌ خطا در مهاجرت دیتابیس: {e}")
        conn.rollback()
        
        # تلاش روش جایگزین
        print("🔄 تلاش روش جایگزین...")
        try:
            # روش جایگزین: ایجاد جدول جدید و کپی داده‌ها
            cursor.execute("SELECT * FROM users")
            users_data = cursor.fetchall()
            print(f"📊 تعداد کاربران: {len(users_data)}")
            
            # حذف و ایجاد مجدد جدول
            cursor.execute("DROP TABLE IF EXISTS users")
            cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                league_id INTEGER NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues (id),
                UNIQUE(user_id, league_id)
            )
            ''')
            
            # وارد کردن داده‌ها
            for user in users_data:
                cursor.execute(
                    "INSERT INTO users (id, user_id, username, league_id, joined_at) VALUES (?, ?, ?, ?, ?)",
                    (user[0], str(user[1]), user[2], user[3], user[4])
                )
            
            conn.commit()
            print("✅ مهاجرت با روش جایگزین موفق بود!")
            
        except Exception as e2:
            print(f"❌ خطا در روش جایگزین: {e2}")
            conn.rollback()
            
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()