import sqlite3
import json
import os
from typing import Optional

# Allow overriding DB path for platforms like Railway with ephemeral filesystems
DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bot_database.db'))
DB_PATH = os.path.normpath(DB_PATH)

def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn


def _has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Return True if the given column exists on table."""
    cursor.execute(f"PRAGMA table_info({table})")
    cols = cursor.fetchall()
    # PRAGMA table_info returns rows where index 1 is the column name.
    return any(row[1] == column for row in cols)

def init_db():
    conn = _get_conn()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            template TEXT,
            data TEXT,
            paid BOOLEAN DEFAULT 0,
            site_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            tx_hash TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            verified BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    # Activity log — tracks user funnel steps
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            step TEXT NOT NULL,
            meta TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Broadcast log — keeps history of sent broadcasts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            message TEXT,
            total_sent INTEGER DEFAULT 0,
            total_failed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()

    # ── Migrations: safely add new columns to existing tables ─────────────────
    # SQLite does not support IF NOT EXISTS on ALTER TABLE, so we catch the error.
    migrations = [
        "ALTER TABLE users ADD COLUMN username TEXT",
        "ALTER TABLE users ADD COLUMN first_name TEXT",
        # SQLite ALTER TABLE cannot reliably add non-constant defaults like CURRENT_TIMESTAMP.
        "ALTER TABLE users ADD COLUMN created_at TIMESTAMP",
        "ALTER TABLE projects ADD COLUMN created_at TIMESTAMP",
        "ALTER TABLE transactions ADD COLUMN created_at TIMESTAMP",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists — skip silently

    # Backfill newly added timestamp columns where possible.
    for table in ("users", "projects", "transactions"):
        if _has_column(cursor, table, "created_at"):
            cursor.execute(
                f"UPDATE {table} SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
            )
            conn.commit()

    conn.close()

def add_user(user_id, username=None, first_name=None):
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
        (user_id, username, first_name)
    )
    # Update username/first_name on subsequent visits
    cursor.execute(
        'UPDATE users SET username=?, first_name=? WHERE user_id=?',
        (username, first_name, user_id)
    )
    conn.commit()
    conn.close()

def create_project(user_id, template, data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO projects (user_id, template, data) VALUES (?, ?, ?)',
        (user_id, template, json.dumps(data))
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id

def get_project(project_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_project_status(project_id, paid=True, site_url=None):
    conn = _get_conn()
    cursor = conn.cursor()
    if site_url:
        cursor.execute(
            'UPDATE projects SET paid = ?, site_url = ? WHERE id = ?',
            (paid, site_url, project_id)
        )
    else:
        cursor.execute(
            'UPDATE projects SET paid = ? WHERE id = ?',
            (paid, project_id)
        )
    conn.commit()
    conn.close()

def add_transaction(tx_hash, user_id, amount, verified=True):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO transactions (tx_hash, user_id, amount, verified) VALUES (?, ?, ?, ?)',
            (tx_hash, user_id, amount, verified)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def tx_exists(tx_hash):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM transactions WHERE tx_hash = ?', (tx_hash,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


# ─── Activity Logging ────────────────────────────────────────────────────────

def log_activity(user_id: int, step: str, meta: Optional[str] = None):
    """Record a funnel step for a user (e.g. 'started_build', 'paid')."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO activity_log (user_id, step, meta) VALUES (?, ?, ?)',
        (user_id, step, meta)
    )
    conn.commit()
    conn.close()


# ─── Admin Analytics Queries ─────────────────────────────────────────────────

def get_admin_stats() -> dict:
    """Return a rich stats dict for the admin dashboard."""
    conn = _get_conn()
    cursor = conn.cursor()

    # Total users
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    users_has_created_at = _has_column(cursor, "users", "created_at")
    projects_has_created_at = _has_column(cursor, "projects", "created_at")

    # New users this week/today (fallback to 0 if legacy schema has no timestamp).
    if users_has_created_at:
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', '-7 days')"
        )
        new_users_week = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= datetime('now', 'start of day')"
        )
        new_users_today = cursor.fetchone()[0]
    else:
        new_users_week = 0
        new_users_today = 0

    # Total sites created
    cursor.execute('SELECT COUNT(*) FROM projects')
    total_sites = cursor.fetchone()[0]

    # Sites created this week/today (fallback to 0 on legacy schema).
    if projects_has_created_at:
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE created_at >= datetime('now', '-7 days')"
        )
        sites_week = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE created_at >= datetime('now', 'start of day')"
        )
        sites_today = cursor.fetchone()[0]
    else:
        sites_week = 0
        sites_today = 0

    # Paid sites (revenue)
    cursor.execute('SELECT COUNT(*) FROM projects WHERE paid = 1')
    paid_sites = cursor.fetchone()[0]

    # Paid this week (fallback to 0 on legacy schema).
    if projects_has_created_at:
        cursor.execute(
            "SELECT COUNT(*) FROM projects WHERE paid = 1 AND created_at >= datetime('now', '-7 days')"
        )
        paid_week = cursor.fetchone()[0]
    else:
        paid_week = 0

    # Revenue (total & week) — 15 USDT each
    price = 15
    revenue_total = paid_sites * price
    revenue_week = paid_week * price

    # Most popular template
    cursor.execute(
        'SELECT template, COUNT(*) as cnt FROM projects GROUP BY template ORDER BY cnt DESC LIMIT 1'
    )
    row = cursor.fetchone()
    top_template = row[0] if row else 'N/A'

    # Conversion rate (paid / total projects)
    conversion = round((paid_sites / total_sites * 100), 1) if total_sites > 0 else 0.0

    # Drop-off analysis — count users per funnel step
    cursor.execute(
        "SELECT step, COUNT(DISTINCT user_id) as cnt FROM activity_log GROUP BY step ORDER BY cnt DESC"
    )
    funnel_rows = cursor.fetchall()
    funnel = [(r[0], r[1]) for r in funnel_rows]

    conn.close()
    return {
        'total_users': total_users,
        'new_users_week': new_users_week,
        'new_users_today': new_users_today,
        'total_sites': total_sites,
        'sites_week': sites_week,
        'sites_today': sites_today,
        'paid_sites': paid_sites,
        'paid_week': paid_week,
        'revenue_total': revenue_total,
        'revenue_week': revenue_week,
        'top_template': top_template,
        'conversion': conversion,
        'funnel': funnel,
    }


def get_all_user_ids() -> list:
    """Return list of all user_ids for broadcast."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids


def get_all_users() -> list:
    """Return list of (user_id, username, created_at) for all users, newest first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if _has_column(cursor, "users", "created_at"):
        cursor.execute(
            'SELECT user_id, username, created_at FROM users ORDER BY created_at DESC'
        )
    else:
        cursor.execute(
            "SELECT user_id, username, NULL as created_at FROM users ORDER BY user_id DESC"
        )
    rows = cursor.fetchall()
    conn.close()
    return rows  # list of (user_id, username, created_at)


def get_funnel_report() -> list:
    """Return per-step drop-off data for the activity log."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT step,
               COUNT(*) as total_events,
               COUNT(DISTINCT user_id) as unique_users
        FROM activity_log
        GROUP BY step
        ORDER BY unique_users DESC
        '''
    )
    rows = cursor.fetchall()
    conn.close()
    return rows  # list of (step, total_events, unique_users)


def save_broadcast(admin_id: int, message: str, sent: int, failed: int):
    """Persist a broadcast record."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO broadcasts (admin_id, message, total_sent, total_failed) VALUES (?, ?, ?, ?)',
        (admin_id, message, sent, failed)
    )
    conn.commit()
    conn.close()


def get_broadcast_history(limit: int = 5) -> list:
    """Return the last N broadcasts."""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, message, total_sent, total_failed, created_at FROM broadcasts ORDER BY created_at DESC LIMIT ?',
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows  # (id, message, sent, failed, created_at)
