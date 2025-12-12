# database.py - نسخه کاملاً بازنویسی شده
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="league_bot.db"):
        self.db_path = db_path
        self.conn = None
        self.connect()
        self.create_tables()
    
    def connect(self):
        """اتصال به دیتابیس"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # فعال کردن foreign keys
            self.conn.execute('PRAGMA foreign_keys = ON')
            logger.info(f"✅ اتصال به دیتابیس {self.db_path} برقرار شد")
            return True
        except Exception as e:
            logger.error(f"❌ خطا در اتصال به دیتابیس: {e}")
            return False
    
    def create_tables(self):
        """ایجاد جداول مورد نیاز - ساختار ساده‌تر"""
        try:
            cursor = self.conn.cursor()
            
            # جدول لیگ‌ها
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS leagues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                capacity INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # جدول کاربران - ساختار ساده
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                league_id INTEGER NOT NULL,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE,
                UNIQUE(user_id, league_id)
            )
            ''')
            
            # جدول قهرمانان - ساختار ساده
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS champions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER UNIQUE NOT NULL,
                game_id TEXT NOT NULL,
                display_name TEXT,
                set_by_admin INTEGER,
                set_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE
            )
            ''')
            
            self.conn.commit()
            logger.info("✅ جداول دیتابیس ایجاد/بررسی شدند")
            
            # بررسی ساختار جداول
            self._verify_table_structures()
            
        except Exception as e:
            logger.error(f"❌ خطا در ایجاد جداول: {e}")
            raise
    
    def _verify_table_structures(self):
        """بررسی ساختار جداول"""
        try:
            cursor = self.conn.cursor()
            
            # بررسی جدول leagues
            cursor.execute("PRAGMA table_info(leagues)")
            leagues_cols = {col[1]: col[2] for col in cursor.fetchall()}
            logger.info(f"📊 جدول leagues: {leagues_cols}")
            
            # بررسی جدول users
            cursor.execute("PRAGMA table_info(users)")
            users_cols = {col[1]: col[2] for col in cursor.fetchall()}
            logger.info(f"📊 جدول users: {users_cols}")
            
            # بررسی جدول champions
            cursor.execute("PRAGMA table_info(champions)")
            champions_cols = {col[1]: col[2] for col in cursor.fetchall()}
            logger.info(f"📊 جدول champions: {champions_cols}")
            
            # بررسی foreign keys
            cursor.execute("PRAGMA foreign_key_list(users)")
            fk_users = cursor.fetchall()
            logger.info(f"🔗 Foreign keys در users: {len(fk_users)}")
            
            cursor.execute("PRAGMA foreign_key_list(champions)")
            fk_champions = cursor.fetchall()
            logger.info(f"🔗 Foreign keys در champions: {len(fk_champions)}")
            
        except Exception as e:
            logger.error(f"❌ خطا در بررسی ساختار جداول: {e}")
    
    def _execute_query(self, query, params=(), fetchone=False, fetchall=False, commit=False):
        """تابع کمکی برای اجرای کوئری‌ها"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            
            if commit:
                self.conn.commit()
            
            if fetchone:
                return cursor.fetchone()
            elif fetchall:
                return cursor.fetchall()
            else:
                return cursor.rowcount
            
        except Exception as e:
            logger.error(f"❌ خطا در اجرای کوئری: {query} | پارامترها: {params} | خطا: {e}")
            raise
    
    # ---------- توابع لیگ‌ها ----------
    
    def create_league(self, name: str, capacity: int) -> int:
        """ایجاد لیگ جدید"""
        try:
            query = "INSERT INTO leagues (name, capacity) VALUES (?, ?)"
            cursor = self.conn.cursor()
            cursor.execute(query, (name, capacity))
            self.conn.commit()
            
            league_id = cursor.lastrowid
            logger.info(f"✅ لیگ '{name}' با ظرفیت {capacity} ایجاد شد (ID: {league_id})")
            return league_id
            
        except Exception as e:
            logger.error(f"❌ خطا در ایجاد لیگ '{name}': {e}")
            return -1
    
    def get_all_leagues(self):
        """دریافت تمام لیگ‌ها"""
        try:
            query = "SELECT id, name, capacity, is_active, created_at FROM leagues ORDER BY id DESC"
            return self._execute_query(query, fetchall=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت لیگ‌ها: {e}")
            return []
    
    def get_active_leagues(self):
        """دریافت لیگ‌های فعال"""
        try:
            query = "SELECT id, name FROM leagues WHERE is_active = 1 ORDER BY id DESC"
            return self._execute_query(query, fetchall=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت لیگ‌های فعال: {e}")
            return []
    
    def get_league(self, league_id: int):
        """دریافت اطلاعات یک لیگ"""
        try:
            query = "SELECT id, name, capacity, is_active, created_at FROM leagues WHERE id = ?"
            return self._execute_query(query, (league_id,), fetchone=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت لیگ {league_id}: {e}")
            return None
    
    def toggle_league_status(self, league_id: int):
        """تغییر وضعیت فعال/غیرفعال لیگ"""
        try:
            # دریافت وضعیت فعلی
            current = self._execute_query(
                "SELECT is_active FROM leagues WHERE id = ?", 
                (league_id,), 
                fetchone=True
            )
            
            if not current:
                logger.error(f"❌ لیگ {league_id} پیدا نشد")
                return None
            
            new_status = 0 if current[0] == 1 else 1
            self._execute_query(
                "UPDATE leagues SET is_active = ? WHERE id = ?",
                (new_status, league_id),
                commit=True
            )
            
            status_text = "غیرفعال" if new_status == 0 else "فعال"
            logger.info(f"✅ وضعیت لیگ {league_id} به '{status_text}' تغییر یافت")
            return new_status
            
        except Exception as e:
            logger.error(f"❌ خطا در تغییر وضعیت لیگ {league_id}: {e}")
            return None
    
    def delete_league(self, league_id: int) -> bool:
        """حذف لیگ و تمام داده‌های مرتبط"""
        try:
            # غیرفعال کردن موقت foreign keys
            cursor = self.conn.cursor()
            cursor.execute('PRAGMA foreign_keys = OFF')
            
            try:
                # ابتدا قهرمانان مرتبط را حذف کن
                cursor.execute("DELETE FROM champions WHERE league_id = ?", (league_id,))
                
                # سپس کاربران مرتبط را حذف کن
                cursor.execute("DELETE FROM users WHERE league_id = ?", (league_id,))
                
                # در نهایت لیگ را حذف کن
                cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
                
                self.conn.commit()
                
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"✅ لیگ {league_id} با موفقیت حذف شد")
                else:
                    logger.warning(f"⚠️ لیگ {league_id} پیدا نشد")
                    
            finally:
                # فعال کردن مجدد foreign keys
                cursor.execute('PRAGMA foreign_keys = ON')
            
            return success
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف لیگ {league_id}: {e}")
            self.conn.rollback()
            return False
    
    def get_leagues_without_champion(self):
        """دریافت لیگ‌های غیرفعال بدون قهرمان"""
        try:
            query = '''
                SELECT l.id, l.name 
                FROM leagues l 
                LEFT JOIN champions c ON l.id = c.league_id 
                WHERE l.is_active = 0 AND c.id IS NULL
                ORDER BY l.id DESC
            '''
            return self._execute_query(query, fetchall=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت لیگ‌های بدون قهرمان: {e}")
            return []
    
    def get_league_user_count(self, league_id: int) -> int:
        """دریافت تعداد کاربران یک لیگ"""
        try:
            query = "SELECT COUNT(*) FROM users WHERE league_id = ?"
            result = self._execute_query(query, (league_id,), fetchone=True)
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ خطا در دریافت تعداد کاربران لیگ {league_id}: {e}")
            return 0
    
    # ---------- توابع کاربران ----------
    
    def register_user(self, user_id, username: str, league_id: int) -> bool:
        """ثبت نام کاربر در یک لیگ خاص"""
        try:
            # بررسی لیگ
            league = self.get_league(league_id)
            if not league:
                logger.error(f"❌ لیگ {league_id} پیدا نشد")
                return False
            
            # بررسی فعال بودن لیگ
            if league[3] != 1:  # is_active
                logger.error(f"❌ لیگ {league_id} غیرفعال است")
                return False
            
            # بررسی ظرفیت
            user_count = self.get_league_user_count(league_id)
            if user_count >= league[2]:  # capacity
                logger.error(f"❌ لیگ {league_id} ظرفیت تکمیل دارد")
                return False
            
            # بررسی ثبت‌نام تکراری
            if self.is_user_in_league(user_id, league_id):
                logger.error(f"❌ کاربر {user_id} قبلاً در لیگ {league_id} ثبت‌نام کرده")
                return False
            
            # ثبت نام
            query = "INSERT INTO users (user_id, username, league_id) VALUES (?, ?, ?)"
            self._execute_query(query, (str(user_id), username, league_id), commit=True)
            
            logger.info(f"✅ کاربر {user_id} در لیگ {league_id} ثبت‌نام کرد")
            return True
            
        except sqlite3.IntegrityError as e:
            logger.error(f"❌ خطای یکتایی در ثبت‌نام کاربر {user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ خطا در ثبت‌نام کاربر {user_id} در لیگ {league_id}: {e}")
            return False
    
    def get_league_users(self, league_id: int):
        """دریافت کاربران یک لیگ"""
        try:
            query = "SELECT user_id, username FROM users WHERE league_id = ?"
            return self._execute_query(query, (league_id,), fetchall=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت کاربران لیگ {league_id}: {e}")
            return []
    
    def get_user_info(self, league_id: int, user_id):
        """دریافت اطلاعات کاربر در لیگ"""
        try:
            query = "SELECT user_id, username FROM users WHERE league_id = ? AND user_id = ?"
            return self._execute_query(query, (league_id, str(user_id)), fetchone=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت اطلاعات کاربر {user_id} در لیگ {league_id}: {e}")
            return None
    
    def remove_user_from_league(self, league_id: int, user_id) -> bool:
        """حذف کاربر از لیگ"""
        try:
            query = "DELETE FROM users WHERE league_id = ? AND user_id = ?"
            result = self._execute_query(query, (league_id, str(user_id)), commit=True)
            
            success = result > 0
            if success:
                logger.info(f"✅ کاربر {user_id} از لیگ {league_id} حذف شد")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف کاربر {user_id} از لیگ {league_id}: {e}")
            return False
    
    def update_user_username(self, league_id: int, user_id, new_username: str) -> bool:
        """بروزرسانی نام کاربر در لیگ"""
        try:
            query = "UPDATE users SET username = ? WHERE league_id = ? AND user_id = ?"
            result = self._execute_query(query, (new_username, league_id, str(user_id)), commit=True)
            
            success = result > 0
            if success:
                logger.info(f"✅ نام کاربری {user_id} به '{new_username}' تغییر یافت")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ خطا در بروزرسانی نام کاربر {user_id}: {e}")
            return False
    
    def is_user_in_league(self, user_id, league_id: int) -> bool:
        """بررسی آیا کاربر در یک لیگ خاص ثبت نام کرده"""
        try:
            query = "SELECT COUNT(*) FROM users WHERE user_id = ? AND league_id = ?"
            result = self._execute_query(query, (str(user_id), league_id), fetchone=True)
            return result[0] > 0 if result else False
        except Exception as e:
            logger.error(f"❌ خطا در بررسی حضور کاربر {user_id} در لیگ {league_id}: {e}")
            return False
    
    def get_user_leagues(self, user_id):
        """دریافت لیگ‌هایی که کاربر در آن‌ها ثبت نام کرده"""
        try:
            query = '''
                SELECT l.id, l.name, l.capacity, u.username
                FROM users u
                JOIN leagues l ON u.league_id = l.id
                WHERE u.user_id = ? AND l.is_active = 1
                ORDER BY l.id DESC
            '''
            return self._execute_query(query, (str(user_id),), fetchall=True)
        except Exception as e:
            logger.error(f"❌ خطا در دریافت لیگ‌های کاربر {user_id}: {e}")
            return []
    
    # ---------- توابع قهرمانان ----------
    
    def set_champion(self, league_id: int, game_id: str, display_name: str, admin_id: int) -> bool:
        """ذخیره قهرمان جدید"""
        try:
            # بررسی وجود قهرمان قبلی
            existing = self._execute_query(
                "SELECT id FROM champions WHERE league_id = ?", 
                (league_id,), 
                fetchone=True
            )
            
            if existing:
                # بروزرسانی
                query = '''
                    UPDATE champions 
                    SET game_id = ?, display_name = ?, set_by_admin = ?, set_at = CURRENT_TIMESTAMP
                    WHERE league_id = ?
                '''
                params = (game_id, display_name, admin_id, league_id)
            else:
                # ایجاد جدید
                query = '''
                    INSERT INTO champions (league_id, game_id, display_name, set_by_admin)
                    VALUES (?, ?, ?, ?)
                '''
                params = (league_id, game_id, display_name, admin_id)
            
            self._execute_query(query, params, commit=True)
            logger.info(f"✅ قهرمان لیگ {league_id} ذخیره شد: {game_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در ذخیره قهرمان لیگ {league_id}: {e}")
            return False
    
    def get_champion(self, league_id: int):
        """دریافت قهرمان یک لیگ"""
        try:
            query = '''
                SELECT c.game_id, c.display_name, c.set_at, l.name
                FROM champions c
                JOIN leagues l ON c.league_id = l.id
                WHERE c.league_id = ?
            '''
            return self._execute_query(query, (league_id,), fetchone=True)
        except Exception as e:
            # اگر ستونی وجود ندارد، با ساختار ساده‌تر تلاش کن
            try:
                query = '''
                    SELECT game_id, display_name, set_at, 
                           (SELECT name FROM leagues WHERE id = champions.league_id) as league_name
                    FROM champions 
                    WHERE league_id = ?
                '''
                return self._execute_query(query, (league_id,), fetchone=True)
            except Exception as e2:
                logger.error(f"❌ خطا در دریافت قهرمان لیگ {league_id}: {e2}")
                return None
    
    def get_all_champions(self):
        """دریافت تمام قهرمانان"""
        try:
            query = '''
                SELECT l.name, c.game_id, c.display_name, c.set_at
                FROM champions c
                JOIN leagues l ON c.league_id = l.id
                ORDER BY c.set_at DESC
            '''
            return self._execute_query(query, fetchall=True)
        except Exception as e:
            # اگر مشکل join داریم، با روش ساده‌تر
            try:
                query = '''
                    SELECT 
                        (SELECT name FROM leagues WHERE id = champions.league_id) as league_name,
                        game_id, display_name, set_at
                    FROM champions 
                    ORDER BY set_at DESC
                '''
                return self._execute_query(query, fetchall=True)
            except Exception as e2:
                logger.error(f"❌ خطا در دریافت قهرمانان: {e2}")
                return []
    
    def remove_champion(self, league_id: int) -> bool:
        """حذف قهرمان یک لیگ"""
        try:
            query = "DELETE FROM champions WHERE league_id = ?"
            result = self._execute_query(query, (league_id,), commit=True)
            
            success = result > 0
            if success:
                logger.info(f"✅ قهرمان لیگ {league_id} حذف شد")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ خطا در حذف قهرمان لیگ {league_id}: {e}")
            return False
    
    # ---------- توابع کمکی ----------
    
    def get_total_stats(self):
        """دریافت آمار کلی سیستم"""
        try:
            stats = {}
            
            # تعداد کل لیگ‌ها
            result = self._execute_query("SELECT COUNT(*) FROM leagues", fetchone=True)
            stats['total_leagues'] = result[0] if result else 0
            
            # لیگ‌های فعال
            result = self._execute_query("SELECT COUNT(*) FROM leagues WHERE is_active = 1", fetchone=True)
            stats['active_leagues'] = result[0] if result else 0
            
            # کاربران منحصر به فرد
            result = self._execute_query("SELECT COUNT(DISTINCT user_id) FROM users", fetchone=True)
            stats['total_users'] = result[0] if result else 0
            
            # تعداد قهرمانان
            result = self._execute_query("SELECT COUNT(*) FROM champions", fetchone=True)
            stats['total_champions'] = result[0] if result else 0
            
            # ظرفیت کل فعال
            result = self._execute_query("SELECT SUM(capacity) FROM leagues WHERE is_active = 1", fetchone=True)
            stats['total_capacity'] = result[0] if result else 0
            
            # تعداد کل ثبت‌نام‌ها
            result = self._execute_query("SELECT COUNT(*) FROM users", fetchone=True)
            stats['total_registrations'] = result[0] if result else 0
            
            logger.info(f"📊 آمار سیستم: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ خطا در دریافت آمار: {e}")
            return {}
    
    def check_and_fix_database(self):
        """بررسی و رفع مشکلات دیتابیس"""
        try:
            logger.info("🔧 بررسی و رفع مشکلات دیتابیس...")
            
            cursor = self.conn.cursor()
            
            # 1. بررسی foreign keys
            cursor.execute('PRAGMA foreign_keys')
            fk_status = cursor.fetchone()[0]
            logger.info(f"🔑 وضعیت FOREIGN KEYS: {'فعال ✅' if fk_status == 1 else 'غیرفعال ❌'}")
            
            if fk_status != 1:
                cursor.execute('PRAGMA foreign_keys = ON')
                logger.info("✅ FOREIGN KEYS فعال شدند")
            
            # 2. بررسی جداول
            tables = ['leagues', 'users', 'champions']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='{table}'")
                exists = cursor.fetchone()[0] > 0
                logger.info(f"📋 جدول {table}: {'وجود دارد ✅' if exists else 'وجود ندارد ❌'}")
            
            # 3. بررسی تعداد رکوردها
            cursor.execute("SELECT COUNT(*) FROM leagues")
            leagues_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            users_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM champions")
            champions_count = cursor.fetchone()[0]
            
            logger.info(f"📈 تعداد رکوردها: {leagues_count} لیگ، {users_count} کاربر، {champions_count} قهرمان")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در بررسی دیتابیس: {e}")
            return False
    
    def close(self):
        """بستن اتصال دیتابیس"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("✅ اتصال دیتابیس بسته شد")
            except:
                pass
    
    def __del__(self):
        """بستن اتصال دیتابیس در صورت نابودی آبجکت"""
        self.close()


# تابع کمکی برای بازنشانی دیتابیس
def reset_database():
    """بازنشانی کامل دیتابیس"""
    import os
    
    db_file = "league_bot.db"
    
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"✅ فایل دیتابیس قدیمی حذف شد: {db_file}")
        except Exception as e:
            print(f"❌ خطا در حذف دیتابیس قدیمی: {e}")
            return False
    
    try:
        db = Database()
        print("✅ دیتابیس جدید ایجاد شد")
        
        # بررسی و رفع مشکلات
        db.check_and_fix_database()
        
        # ایجاد داده‌های نمونه برای تست
        test_league_id = db.create_league("لیگ تست", 10)
        print(f"✅ لیگ تست ایجاد شد (ID: {test_league_id})")
        
        db.close()
        print("✅ دیتابیس با موفقیت بازنشانی شد")
        return True
        
    except Exception as e:
        print(f"❌ خطا در بازنشانی دیتابیس: {e}")
        return False


if __name__ == "__main__":
    # اگر مستقیماً اجرا شود، دیتابیس را بررسی کن
    db = Database()
    db.check_and_fix_database()
    db.close()