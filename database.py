import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="football_league.db"):
        self.db_path = db_path
        self.conn = self.connect()
        self.create_tables()
    
    def connect(self):
        """اتصال به دیتابیس"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def create_tables(self):
        """ایجاد جداول مورد نیاز"""
        cursor = self.conn.cursor()
        
        # جدول لیگ‌ها
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS leagues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # جدول کاربران
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            league_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues (id),
            UNIQUE(user_id, league_id)
        )
        ''')
        
        # جدول قهرمانان
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
        
        self.conn.commit()
    
    # ---------- توابع لیگ‌ها ----------
    
    def create_league(self, name: str, capacity: int) -> int:
        """ایجاد لیگ جدید"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO leagues (name, capacity) VALUES (?, ?)",
                (name, capacity)
            )
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"خطا در ایجاد لیگ: {e}")
            return -1
    
    def get_all_leagues(self):
        """دریافت تمام لیگ‌ها"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, capacity, is_active FROM leagues ORDER BY id DESC")
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت لیگ‌ها: {e}")
            return []
    
    def get_league(self, league_id: int):
        """دریافت اطلاعات یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, capacity, is_active, created_at FROM leagues WHERE id = ?",
                (league_id,)
            )
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"خطا در دریافت لیگ: {e}")
            return None
    
    def toggle_league_status(self, league_id: int):
        """تغییر وضعیت فعال/غیرفعال لیگ"""
        try:
            cursor = self.conn.cursor()
            # دریافت وضعیت فعلی
            cursor.execute("SELECT is_active FROM leagues WHERE id = ?", (league_id,))
            current_status = cursor.fetchone()
            
            if not current_status:
                return None
            
            new_status = 0 if current_status[0] == 1 else 1
            cursor.execute(
                "UPDATE leagues SET is_active = ? WHERE id = ?",
                (new_status, league_id)
            )
            self.conn.commit()
            return new_status
        except Exception as e:
            logger.error(f"خطا در تغییر وضعیت لیگ: {e}")
            return None
    
    def delete_league(self, league_id: int) -> bool:
        """حذف لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف لیگ: {e}")
            return False
    
    def get_leagues_without_champion(self):
        """دریافت لیگ‌های غیرفعال بدون قهرمان"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT l.id, l.name 
                FROM leagues l 
                LEFT JOIN champions c ON l.id = c.league_id 
                WHERE l.is_active = 0 AND c.id IS NULL
                ORDER BY l.id DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت لیگ‌های بدون قهرمان: {e}")
            return []
    
    # ---------- توابع کاربران ----------
    
    def add_user_to_league(self, user_id: int, username: str, league_id: int) -> bool:
        """افزودن کاربر به لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO users (user_id, username, league_id) VALUES (?, ?, ?)",
                (user_id, username, league_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطا در افزودن کاربر به لیگ: {e}")
            return False
    
    def get_league_users(self, league_id: int):
        """دریافت کاربران یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, username FROM users WHERE league_id = ? ORDER BY id DESC",
                (league_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت کاربران لیگ: {e}")
            return []
    
    def get_league_user_count(self, league_id: int) -> int:
        """دریافت تعداد کاربران یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE league_id = ?",
                (league_id,)
            )
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"خطا در دریافت تعداد کاربران: {e}")
            return 0
    
    def get_user_info(self, league_id: int, user_id: int):
        """دریافت اطلاعات کاربر در لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, username FROM users WHERE league_id = ? AND user_id = ?",
                (league_id, user_id)
            )
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات کاربر: {e}")
            return None
    
    def remove_user_from_league(self, league_id: int, user_id: int) -> bool:
        """حذف کاربر از لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM users WHERE league_id = ? AND user_id = ?",
                (league_id, user_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف کاربر از لیگ: {e}")
            return False
    
    def update_user_username(self, league_id: int, user_id: int, new_username: str) -> bool:
        """بروزرسانی نام کاربر در لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE users SET username = ? WHERE league_id = ? AND user_id = ?",
                (new_username, league_id, user_id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در بروزرسانی نام کاربر: {e}")
            return False
    
    # ---------- توابع قهرمانان ----------
    
    def set_champion(self, league_id: int, game_id: str, display_name: str, admin_id: int) -> bool:
        """ذخیره قهرمان جدید"""
        try:
            cursor = self.conn.cursor()
            
            # بررسی وجود قهرمان قبلی
            cursor.execute("SELECT id FROM champions WHERE league_id = ?", (league_id,))
            existing = cursor.fetchone()
            
            if existing:
                # بروزرسانی قهرمان موجود
                cursor.execute('''
                    UPDATE champions 
                    SET game_id = ?, display_name = ?, set_by_admin = ?, set_at = CURRENT_TIMESTAMP
                    WHERE league_id = ?
                ''', (game_id, display_name, admin_id, league_id))
            else:
                # ایجاد قهرمان جدید
                cursor.execute('''
                    INSERT INTO champions (league_id, game_id, display_name, set_by_admin)
                    VALUES (?, ?, ?, ?)
                ''', (league_id, game_id, display_name, admin_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره قهرمان: {e}")
            return False
    
    def get_champion(self, league_id: int):
        """دریافت قهرمان یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT c.game_id, c.display_name, c.set_at, l.name
                FROM champions c
                JOIN leagues l ON c.league_id = l.id
                WHERE c.league_id = ?
            ''', (league_id,))
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"خطا در دریافت قهرمان: {e}")
            return None
    
    def get_all_champions(self):
        """دریافت تمام قهرمانان"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT l.name, c.game_id, c.display_name, c.set_at
                FROM champions c
                JOIN leagues l ON c.league_id = l.id
                ORDER BY c.set_at DESC
            ''')
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت قهرمانان: {e}")
            return []
    
    def remove_champion(self, league_id: int) -> bool:
        """حذف قهرمان یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM champions WHERE league_id = ?", (league_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف قهرمان: {e}")
            return False
    
    def __del__(self):
        """بستن اتصال دیتابیس"""
        if hasattr(self, 'conn'):
            self.conn.close()