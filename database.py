# database.py - نسخه اصلاح شده
import sqlite3
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # جدول لیگ‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                league_id INTEGER,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues (id)
            )
        ''')
        
        # جدول جدید: قهرمانان (تالار افتخارات)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS champions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER UNIQUE NOT NULL,
                champion_username TEXT NOT NULL,
                champion_display_name TEXT,
                set_by_admin_id INTEGER,
                set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues (id)
            )
        ''')
        
        self.conn.commit()
    
    # ---------- توابع لیگ‌ها ----------
    def create_league(self, name, capacity):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO leagues (name, capacity) VALUES (?, ?)",
            (name, capacity)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_leagues(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, capacity, is_active FROM leagues ORDER BY id")
        return cursor.fetchall()
    
    def get_active_leagues(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM leagues WHERE is_active = 1")
        return cursor.fetchall()
    
    def get_league(self, league_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM leagues WHERE id = ?", (league_id,))
        return cursor.fetchone()
    
    def toggle_league_status(self, league_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_active FROM leagues WHERE id = ?", (league_id,))
        league = cursor.fetchone()
        if league:
            new_status = 0 if league[0] == 1 else 1
            cursor.execute(
                "UPDATE leagues SET is_active = ? WHERE id = ?",
                (new_status, league_id)
            )
            self.conn.commit()
            return new_status
        return None
    
    def get_league_users(self, league_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.user_id, u.username 
            FROM users u 
            WHERE u.league_id = ?
            ORDER BY u.registered_at
        ''', (league_id,))
        return cursor.fetchall()
    
    def get_league_user_count(self, league_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE league_id = ?",
            (league_id,)
        )
        return cursor.fetchone()[0]
    
    # ---------- توابع قهرمانان (تالار افتخارات) ----------
    def set_champion(self, league_id, champion_username, champion_display_name, admin_id):
        """تعیین قهرمان برای یک لیگ"""
        cursor = self.conn.cursor()
        try:
            # اگر قبلاً قهرمان داشت، آپدیت کن
            cursor.execute('''
                INSERT OR REPLACE INTO champions 
                (league_id, champion_username, champion_display_name, set_by_admin_id) 
                VALUES (?, ?, ?, ?)
            ''', (league_id, champion_username, champion_display_name, admin_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"خطا در ذخیره قهرمان: {e}")
            return False
    
    def get_champion(self, league_id):
        """دریافت قهرمان یک لیگ"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT c.champion_username, c.champion_display_name, c.set_at
            FROM champions c
            WHERE c.league_id = ?
        ''', (league_id,))
        result = cursor.fetchone()
        
        if result:
            # نام لیگ را هم بگیر
            cursor.execute("SELECT name FROM leagues WHERE id = ?", (league_id,))
            league_name = cursor.fetchone()
            if league_name:
                return (result[0], result[1], result[2], league_name[0])
        
        return None
    
    def get_all_champions(self):
        """دریافت همه قهرمانان"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT l.name, c.champion_username, c.champion_display_name, c.set_at
            FROM champions c
            JOIN leagues l ON c.league_id = l.id
            ORDER BY c.set_at DESC
        ''')
        return cursor.fetchall()
    
    def remove_champion(self, league_id):
        """حذف قهرمان یک لیگ"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM champions WHERE league_id = ?", (league_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_leagues_without_champion(self):
        """لیگ‌هایی که هنوز قهرمان ندارند"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT l.id, l.name 
            FROM leagues l
            LEFT JOIN champions c ON l.id = c.league_id
            WHERE c.league_id IS NULL AND l.is_active = 0
            ORDER BY l.name
        ''')
        return cursor.fetchall()
    
    def get_leagues_with_champion(self):
        """لیگ‌هایی که قهرمان دارند"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT l.id, l.name, c.champion_username, c.champion_display_name
            FROM leagues l
            JOIN champions c ON l.id = c.league_id
            ORDER BY l.name
        ''')
        return cursor.fetchall()
    
    # ---------- توابع کاربران ----------
    def is_user_registered(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchone() is not None
    
    def register_user(self, user_id, username, league_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (user_id, username, league_id) VALUES (?, ?, ?)",
                (user_id, username, league_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def close(self):
        self.conn.close()