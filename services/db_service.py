import sqlite3
import os
import random
import string
import re
import bcrypt  # Для безпечного хешування паролів

DB_PATH = "feedback.db"

def validate_institution_code(code: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]{8}", code))

def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt)

def verify_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash)

def create_institutions_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS institutions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            official_name TEXT,
            code TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def generate_random_code(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def add_institution(official_name):
    create_institutions_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    while True:
        code = generate_random_code()
        c.execute("SELECT 1 FROM institutions WHERE code=?", (code,))
        if not c.fetchone():
            break

    c.execute("INSERT INTO institutions (official_name, code) VALUES (?, ?)", (official_name, code))
    conn.commit()
    conn.close()

    create_feedback_table_for_institution(code)
    return code

def get_all_institutions():
    create_institutions_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, official_name, code FROM institutions ORDER BY id")
    institutions = c.fetchall()
    conn.close()
    return institutions

def get_institution_by_code(code):
    create_institutions_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT official_name, code FROM institutions WHERE code=?", (code,))
    row = c.fetchone()
    conn.close()
    return row

def create_feedback_table_for_institution(institution_code):
    if not validate_institution_code(institution_code):
        raise ValueError("Некоректний код інституції")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    table_name = f"feedback_{institution_code}"
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            lang TEXT,
            sentiment TEXT,
            spam INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_feedback_for_institution(institution_code, text, lang, sentiment, spam):
    if not validate_institution_code(institution_code):
        raise ValueError("Некоректний код інституції")
    create_feedback_table_for_institution(institution_code)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    table_name = f"feedback_{institution_code}"
    c.execute(f'''
        INSERT INTO {table_name} (text, lang, sentiment, spam) VALUES (?, ?, ?, ?)
    ''', (text, lang, sentiment, spam))
    conn.commit()
    conn.close()

def load_all_feedback_for_institution(
    institution_code,
    spam_filter='all',
    sentiment_filter='all',
    length_filter='all',
    order='desc'
):
    if not validate_institution_code(institution_code):
        raise ValueError("Некоректний код інституції")
    create_feedback_table_for_institution(institution_code)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    table_name = f"feedback_{institution_code}"

    query = f"SELECT id, text, lang, sentiment, spam FROM {table_name} WHERE 1=1"
    params = []

    if spam_filter == 'spam':
        query += " AND spam=1"
    elif spam_filter == 'ham':
        query += " AND spam=0"

    if sentiment_filter in ('positive', 'negative', 'neutral'):
        query += " AND sentiment=?"
        params.append(sentiment_filter)

    if length_filter == 'short':
        query += " AND LENGTH(text) <= 100"
    elif length_filter == 'long':
        query += " AND LENGTH(text) > 100"

    query += f" ORDER BY id {'ASC' if order == 'asc' else 'DESC'}"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

def create_admin_table_if_not_exists():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash BLOB
        )
    ''')
    conn.commit()
    conn.close()

def add_admin_user(username, password):
    create_admin_table_if_not_exists()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM admin WHERE username=?", (username,))
    if c.fetchone():
        conn.close()
        return
    password_hash = hash_password(password)
    c.execute("INSERT INTO admin (username, password_hash) VALUES (?, ?)", (username, password_hash))
    conn.commit()
    conn.close()

def verify_admin_user(username, password):
    create_admin_table_if_not_exists()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM admin WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        password_hash = row[0]
        return verify_password(password, password_hash)
    return False

def update_admin_password(username, new_password):
    password_hash = hash_password(new_password)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE admin SET password_hash = ? WHERE username = ?", (password_hash, username))
    conn.commit()
    conn.close()

def generate_random_password(length=24):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
