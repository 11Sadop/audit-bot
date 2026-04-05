import sqlite3
import time
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_data.db')

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS admins (tg_id INTEGER PRIMARY KEY, added_at INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS users (tg_id INTEGER PRIMARY KEY, username TEXT, pledged INTEGER DEFAULT 0, joined_at INTEGER)')
    c.execute('''CREATE TABLE IF NOT EXISTS auction_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER,
        requester_username TEXT,
        seller_username TEXT,
        title TEXT,
        description TEXT,
        photo_id TEXT,
        currency TEXT,
        start_price INTEGER,
        min_increment INTEGER,
        status TEXT DEFAULT 'pending',
        created_at INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, description TEXT, photo_id TEXT,
        currency TEXT, start_price INTEGER, min_increment INTEGER,
        current_price INTEGER, highest_bidder INTEGER,
        seller_username TEXT,
        status TEXT DEFAULT 'active',
        group_message_id INTEGER DEFAULT 0,
        request_id INTEGER DEFAULT 0,
        created_at INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auction_id INTEGER, tg_id INTEGER, amount INTEGER, timestamp INTEGER
    )''')
    conn.commit()
    conn.close()

def get_config(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key = ?", (key,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else default

def set_config(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def is_admin(tg_id):
    owner_id = get_config("owner_id", "")
    if str(tg_id) == owner_id:
        return True
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM admins WHERE tg_id = ?", (tg_id,))
    r = c.fetchone()
    conn.close()
    return r is not None

def add_admin(tg_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (tg_id, added_at) VALUES (?, ?)", (tg_id, int(time.time())))
    conn.commit()
    conn.close()

def remove_admin(tg_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def ensure_user(tg_id, username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE tg_id = ?", (tg_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (tg_id, username, pledged, joined_at) VALUES (?, ?, 0, ?)", (tg_id, username, int(time.time())))
    else:
        c.execute("UPDATE users SET username = ? WHERE tg_id = ?", (username, tg_id))
    conn.commit()
    conn.close()

def set_pledged(tg_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET pledged = 1 WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

def create_request(requester_id, requester_username, seller_username, title, desc, photo, currency, start_price, inc):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO auction_requests (requester_id, requester_username, seller_username, title, description, photo_id, currency, start_price, min_increment, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,'pending',?)",
        (requester_id, requester_username, seller_username, title, desc, photo, currency, start_price, inc, int(time.time())))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid

def get_pending_requests():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM auction_requests WHERE status = 'pending' ORDER BY id ASC")
    r = c.fetchall()
    conn.close()
    return [dict(x) for x in r]

def get_request(rid):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM auction_requests WHERE id = ?", (rid,))
    r = c.fetchone()
    conn.close()
    return dict(r) if r else None

def approve_request(rid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE auction_requests SET status = 'approved' WHERE id = ?", (rid,))
    conn.commit()
    conn.close()

def reject_request(rid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE auction_requests SET status = 'rejected' WHERE id = ?", (rid,))
    conn.commit()
    conn.close()

def get_queue_position(rid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM auction_requests WHERE status = 'pending' AND id <= ?", (rid,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def get_pending_count():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM auction_requests WHERE status = 'pending'")
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def create_auction(title, desc, photo, currency, start_price, inc, seller_username, request_id=0):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO auctions (title, description, photo_id, currency, start_price, min_increment, current_price, highest_bidder, seller_username, status, group_message_id, request_id, created_at) VALUES (?,?,?,?,?,?,?,0,?,'active',0,?,?)",
        (title, desc, photo, currency, start_price, inc, start_price, seller_username, request_id, int(time.time())))
    conn.commit()
    aid = c.lastrowid
    conn.close()
    return aid

def get_auction(aid):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM auctions WHERE id = ?", (aid,))
    r = c.fetchone()
    conn.close()
    return dict(r) if r else None

def get_active_auctions():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM auctions WHERE status = 'active' ORDER BY id DESC")
    r = c.fetchall()
    conn.close()
    return [dict(x) for x in r]

def place_bid(aid, tg_id, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO bids (auction_id, tg_id, amount, timestamp) VALUES (?,?,?,?)", (aid, tg_id, amount, int(time.time())))
    c.execute("UPDATE auctions SET current_price = ?, highest_bidder = ? WHERE id = ?", (amount, tg_id, aid))
    conn.commit()
    conn.close()

def end_auction(aid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE auctions SET status = 'ended' WHERE id = ?", (aid,))
    conn.commit()
    conn.close()

def set_auction_group_msg(aid, mid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE auctions SET group_message_id = ? WHERE id = ?", (mid, aid))
    conn.commit()
    conn.close()

def get_bid_count(aid):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM bids WHERE auction_id = ?", (aid,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else 0

def get_last_bids(aid, limit):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM bids WHERE auction_id = ? ORDER BY id DESC LIMIT ?", (aid, limit))
    r = c.fetchall()
    conn.close()
    return [dict(x) for x in r]

def get_username(tg_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE tg_id = ?", (tg_id,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else "unknown"

init_db()
