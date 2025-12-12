# database.py - نسخه اصلاح شده
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
        
        # جدول کاربران - user_id به TEXT برای پشتیبانی از هر نوع داده
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            username TEXT,
            league_id INTEGER NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (league_id) REFERENCES leagues (id) ON DELETE CASCADE,
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
            FOREIGN KEY (league_id) REFERENCES leagues (id) ON DELETE CASCADE,
            UNIQUE(league_id)
        )
        ''')
        
        # فعال کردن کلیدهای خارجی
        cursor.execute('PRAGMA foreign_keys = ON')
        
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
            cursor.execute("SELECT id, name, capacity, is_active, created_at FROM leagues ORDER BY id DESC")
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت لیگ‌ها: {e}")
            return []
    
    def get_active_leagues(self):
        """دریافت لیگ‌های فعال"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name FROM leagues WHERE is_active = 1 ORDER BY id DESC")
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت لیگ‌های فعال: {e}")
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
            current = cursor.fetchone()
            
            if not current:
                return None
            
            new_status = 0 if current[0] == 1 else 1
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
        """حذف لیگ و تمام داده‌های مرتبط"""
        try:
            cursor = self.conn.cursor()
            
            # حذف کاربران مرتبط (به دلیل FOREIGN KEY با CASCADE خودکار حذف می‌شوند)
            cursor.execute("DELETE FROM champions WHERE league_id = ?", (league_id,))
            
            # حذف لیگ
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
    
    def get_league_user_count(self, league_id: int) -> int:
        """دریافت تعداد کاربران یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE league_id = ?",
                (league_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"خطا در دریافت تعداد کاربران: {e}")
            return 0
    
    # ---------- توابع کاربران ----------
    
    def register_user(self, user_id, username: str, league_id: int) -> bool:
        """ثبت نام کاربر در یک لیگ خاص"""
        try:
            cursor = self.conn.cursor()
            
            # بررسی آیا لیگ فعال است
            cursor.execute("SELECT is_active FROM leagues WHERE id = ?", (league_id,))
            league = cursor.fetchone()
            
            if not league or league[0] != 1:
                return False
            
            # بررسی ظرفیت لیگ
            user_count = self.get_league_user_count(league_id)
            cursor.execute("SELECT capacity FROM leagues WHERE id = ?", (league_id,))
            capacity_result = cursor.fetchone()
            
            if not capacity_result:
                return False
            
            if user_count >= capacity_result[0]:
                return False
            
            # بررسی آیا کاربر قبلاً در این لیگ ثبت نام کرده
            cursor.execute(
                "SELECT id FROM users WHERE user_id = ? AND league_id = ?",
                (str(user_id), league_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                return False
            
            # ثبت نام کاربر
            cursor.execute(
                "INSERT INTO users (user_id, username, league_id) VALUES (?, ?, ?)",
                (str(user_id), username, league_id)
            )
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"خطا در ثبت نام کاربر: {e}")
            return False
    
    def get_league_users(self, league_id: int):
        """دریافت کاربران یک لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, username FROM users WHERE league_id = ? ORDER BY joined_at DESC",
                (league_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت کاربران لیگ: {e}")
            return []
    
    def get_user_info(self, league_id: int, user_id):
        """دریافت اطلاعات کاربر در لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, username FROM users WHERE league_id = ? AND user_id = ?",
                (league_id, str(user_id))
            )
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات کاربر: {e}")
            return None
    
    def remove_user_from_league(self, league_id: int, user_id) -> bool:
        """حذف کاربر از لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM users WHERE league_id = ? AND user_id = ?",
                (league_id, str(user_id))
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در حذف کاربر از لیگ: {e}")
            return False
    
    def update_user_username(self, league_id: int, user_id, new_username: str) -> bool:
        """بروزرسانی نام کاربر در لیگ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE users SET username = ? WHERE league_id = ? AND user_id = ?",
                (new_username, league_id, str(user_id))
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"خطا در بروزرسانی نام کاربر: {e}")
            return False
    
    def is_user_in_league(self, user_id, league_id: int) -> bool:
        """بررسی آیا کاربر در یک لیگ خاص ثبت نام کرده"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE user_id = ? AND league_id = ?",
                (str(user_id), league_id)
            )
            result = cursor.fetchone()
            return result[0] > 0 if result else False
        except Exception as e:
            logger.error(f"خطا در بررسی حضور کاربر در لیگ: {e}")
            return False
    
    def get_user_leagues(self, user_id):
        """دریافت لیگ‌هایی که کاربر در آن‌ها ثبت نام کرده"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT l.id, l.name, l.capacity, u.username
                FROM users u
                JOIN leagues l ON u.league_id = l.id
                WHERE u.user_id = ? AND l.is_active = 1
            ''', (str(user_id),))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت لیگ‌های کاربر: {e}")
            return []
    
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
    
    # ---------- توابع کمکی ----------
    
    def get_total_stats(self):
        """دریافت آمار کلی سیستم"""
        try:
            cursor = self.conn.cursor()
            
            stats = {}
            
            # تعداد کل لیگ‌ها
            cursor.execute("SELECT COUNT(*) FROM leagues")
            stats['total_leagues'] = cursor.fetchone()[0]
            
            # لیگ‌های فعال
            cursor.execute("SELECT COUNT(*) FROM leagues WHERE is_active = 1")
            stats['active_leagues'] = cursor.fetchone()[0]
            
            # تعداد کل کاربران (کاربران منحصر به فرد)
            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM users")
            stats['total_users'] = cursor.fetchone()[0]
            
            # تعداد قهرمانان
            cursor.execute("SELECT COUNT(*) FROM champions")
            stats['total_champions'] = cursor.fetchone()[0]
            
            # ظرفیت کل فعال
            cursor.execute("SELECT SUM(capacity) FROM leagues WHERE is_active = 1")
            result = cursor.fetchone()[0]
            stats['total_capacity'] = result if result else 0
            
            # تعداد کل ثبت‌نام‌ها
            cursor.execute("SELECT COUNT(*) FROM users")
            stats['total_registrations'] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"خطا در دریافت آمار: {e}")
            return {}
    
    def close(self):
        """بستن اتصال دیتابیس"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """بستن اتصال دیتابیس در صورت نابودی آبجکت"""
        self.close()