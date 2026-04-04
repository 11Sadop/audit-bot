import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_data.db')

def get_connection():
        return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS admins (tg_id INTEGER PRIMARY KEY, added_at INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, username TEXT, pledged INTEGER DEFAULT 0, joined_at INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS auctions (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, photo_id TEXT, currency TEXT, start_price INTEGER, min_increment INTEGER, current_price INTEGER, highest_bidder INTEGER, status TEXT DEFAULT 'active', created_at INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS bids (id INTEGER PRIMARY KEY AUTOINCREMENT, auction_id INTEGER, tg_id INTEGER, amount INTEGER, timestamp INTEGER)''')
        conn.commit()
        conn.close()

def get_config(key, default=None):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else default

def set_config(key, value):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()

def is_admin(tg_id):
        owner_id = get_config("owner_id", "")
        if str(tg_id) == owner_id:
                    return True
                conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE tg_id = ?", (tg_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def add_admin(tg_id):
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (tg_id, added_at) VALUES (?, ?)", (tg_id, int(time.time())))
    conn.commit()
    conn.close()

def remove_admin(tg_id):
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def ensure_user(tg_id, username):
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE tg_id = ?", (tg_id,))
    if not cursor.fetchone():
                cursor.execute("INSERT INTO users (tg_id, username, pledged, joined_at) VALUES (?, ?, 0, ?)", (tg_id, username, int(time.time())))
                conn.commit()
else:
        cursor.execute("UPDATE users SET username = ? WHERE tg_id = ?", (username, tg_id))
        conn.commit()
    conn.close()

def has_pledged(tg_id):
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT pledged FROM users WHERE tg_id = ?", (tg_id,))
    res = cursor.fetchone()
    conn.close()
    return True if res and res[0] == 1 else False

def set_pledged(tg_id):
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET pledged = 1 WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def create_auction(title, desc, photo, currency, start_price, inc):
        conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO auctions (title, description, photo_id, currency, start_price, min_increment, current_price, highest_bidder, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'active', ?)", (title, desc, photo, currency, start_price, inc, start_price, int(time.time())))
    conn.commit()
    auction_id = cursor.lastrowid
    conn.close()
    return auction_id

def get_auction(auction_id):
        conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None

def get_active_auctions():
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM auctions WHERE status = 'active' ORDER BY id DESC")
        results = cursor.fetchall()
        conn.close()
        return [dict(r) for r in results]

def place_bid(auction_id, tg_id, amount):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bids (auction_id, tg_id, amount, timestamp) VALUES (?, ?, ?, ?)", (auction_id, tg_id, amount, int(time.time())))
        cursor.execute("UPDATE auctions SET current_price = ?, highest_bidder = ? WHERE id = ?", (amount, tg_id, auction_id))
        conn.commit()
        conn.close()

def end_auction(auction_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE auctions SET status = 'ended' WHERE id = ?", (auction_id,))
        conn.commit()
        conn.close()

def get_username(tg_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE tg_id = ?", (tg_id,))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else "unknown"

init_db()
