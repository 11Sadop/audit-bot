import sqlite3

DB_NAME = "audit_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Users table: ID, username, remaining_scans, is_vip, join_date
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            remaining_scans INTEGER DEFAULT 3,
            is_vip BOOLEAN DEFAULT 0,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_or_create_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT remaining_scans, is_vip FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        # User gets 3 free scans initially
        cursor.execute("INSERT INTO users (user_id, username, remaining_scans, is_vip) VALUES (?, ?, 3, 0)", (user_id, username))
        conn.commit()
        conn.close()
        return {"remaining_scans": 3, "is_vip": False}
    else:
        conn.close()
        return {"remaining_scans": row[0], "is_vip": bool(row[1])}

def consume_scan(user_id):
    """
    سحب نقطة فحص واحدة من المستخدم العادي
    إذا كان VIP لا تسحب أي نقطة
    """
    user = get_or_create_user(user_id, "")
    if user["is_vip"]:
        return True # VIP has unlimited scans

    if user["remaining_scans"] > 0:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET remaining_scans = remaining_scans - 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    return False

def check_can_scan(user_id):
    user = get_or_create_user(user_id, "")
    return user["is_vip"] or user["remaining_scans"] > 0

def add_vip(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_vip = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
