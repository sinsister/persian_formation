# database.py
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