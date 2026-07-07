import html
import sqlite3
import zipfile
from pathlib import Path

from openpyxl import Workbook

from config import ADMIN_ID, ADMIN_NAME, DB_PATH, GROUP_MAP

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()


def _column_names(table: str) -> list[str]:
    return [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]


def _ensure_column(table: str, column: str, definition: str):
    if column not in _column_names(table):
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        connection.commit()


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        type TEXT,
        content TEXT,
        meta TEXT,
        caption TEXT,
        targets TEXT,
        group_names TEXT,
        source_chat_id TEXT DEFAULT '',
        source_message_id INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS sent_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        target_chat_id TEXT NOT NULL,
        target_message_id INTEGER NOT NULL,
        target_name TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS scheduled_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        type TEXT,
        content TEXT,
        meta TEXT,
        caption TEXT,
        targets TEXT,
        group_names TEXT,
        source_chat_id TEXT,
        source_message_id INTEGER,
        run_at TEXT,
        status TEXT DEFAULT 'pending',
        result TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS groups (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'group',
        added_by TEXT DEFAULT '',
        added_by_name TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id TEXT PRIMARY KEY,
        first_name TEXT DEFAULT '',
        last_name TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        age INTEGER DEFAULT 0,
        onboarding_step TEXT DEFAULT '',
        started_at DATETIME,
        stopped_at DATETIME,
        start_count INTEGER DEFAULT 0,
        stop_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'stopped'
    )
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS admins (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
)
connection.commit()

for column, definition in {
    "targets": "TEXT DEFAULT ''",
    "group_names": "TEXT DEFAULT ''",
    "source_chat_id": "TEXT DEFAULT ''",
    "source_message_id": "INTEGER DEFAULT 0",
}.items():
    _ensure_column("messages", column, definition)

for column, definition in {
    "added_by": "TEXT DEFAULT ''",
    "added_by_name": "TEXT DEFAULT ''",
    "type": "TEXT DEFAULT 'group'",
}.items():
    _ensure_column("groups", column, definition)

_ensure_column("admins", "role", "TEXT DEFAULT 'admin'")
for column, definition in {
    "first_name": "TEXT DEFAULT ''",
    "last_name": "TEXT DEFAULT ''",
    "phone": "TEXT DEFAULT ''",
    "age": "INTEGER DEFAULT 0",
    "onboarding_step": "TEXT DEFAULT ''",
}.items():
    _ensure_column("user_stats", column, definition)

cursor.execute("INSERT OR IGNORE INTO admins (user_id, name, role) VALUES (?, ?, 'owner')", (str(ADMIN_ID), ADMIN_NAME))
for group_id, group_name in GROUP_MAP.items():
    cursor.execute(
        "INSERT OR IGNORE INTO groups (id, name, type, added_by, added_by_name) VALUES (?, ?, 'group', ?, ?)",
        (group_id, group_name, str(ADMIN_ID), ADMIN_NAME),
    )
connection.commit()


def save_message(
    user_id: int,
    message_type: str,
    content: str,
    meta: str = "",
    caption: str = "",
    targets: str = "",
    group_names: str = "",
    source_chat_id: str = "",
    source_message_id: int = 0,
):
    cursor.execute(
        """
        INSERT INTO messages
        (user_id, type, content, meta, caption, targets, group_names, source_chat_id, source_message_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (str(user_id), message_type, content, meta, caption, targets, group_names, str(source_chat_id), source_message_id),
    )
    connection.commit()
    return cursor.lastrowid


def add_sent_message(message_id: int, target_chat_id: str, target_message_id: int, target_name: str = ""):
    cursor.execute(
        "INSERT INTO sent_messages (message_id, target_chat_id, target_message_id, target_name) VALUES (?, ?, ?, ?)",
        (message_id, str(target_chat_id), int(target_message_id), target_name),
    )
    connection.commit()


def get_sent_messages(message_id: int):
    cursor.execute("SELECT * FROM sent_messages WHERE message_id = ? ORDER BY id", (message_id,))
    return cursor.fetchall()


def get_saved_groups():
    cursor.execute("SELECT id, name, type, added_by, added_by_name FROM groups ORDER BY created_at, rowid")
    return cursor.fetchall()


def group_exists(group_id: str) -> bool:
    cursor.execute("SELECT 1 FROM groups WHERE id = ?", (group_id,))
    return cursor.fetchone() is not None


def get_admins():
    cursor.execute("SELECT user_id, name, role, created_at FROM admins ORDER BY role DESC, created_at")
    return cursor.fetchall()


def delete_admin(user_id: str):
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    connection.commit()
    return cursor.rowcount


def update_admin_name(user_id: str, new_name: str):
    cursor.execute("UPDATE admins SET name = ? WHERE user_id = ?", (new_name, user_id))
    connection.commit()
    return cursor.rowcount


def is_admin(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone() is not None


def add_admin(user_id: str, name: str, role: str = "admin"):
    cursor.execute(
        "INSERT OR REPLACE INTO admins (user_id, name, role) VALUES (?, ?, ?)",
        (str(user_id), name, role),
    )
    connection.commit()
    return cursor.lastrowid


def get_admin_name(user_id: str) -> str | None:
    cursor.execute("SELECT name FROM admins WHERE user_id = ?", (str(user_id),))
    row = cursor.fetchone()
    return row["name"] if row else None


def add_group(group_id: str, name: str, added_by: str = "", added_by_name: str = "", group_type: str = "group"):
    cursor.execute(
        "INSERT OR REPLACE INTO groups (id, name, type, added_by, added_by_name) VALUES (?, ?, ?, ?, ?)",
        (str(group_id), name, group_type, str(added_by), added_by_name),
    )
    connection.commit()
    return cursor.lastrowid


def delete_group(group_id: str):
    cursor.execute("DELETE FROM groups WHERE id = ?", (str(group_id),))
    connection.commit()
    return cursor.rowcount


def update_group_name(group_id: str, new_name: str):
    cursor.execute("UPDATE groups SET name = ? WHERE id = ?", (new_name, str(group_id)))
    connection.commit()
    return cursor.rowcount


def get_group_name(group_id: str) -> str | None:
    cursor.execute("SELECT name FROM groups WHERE id = ?", (str(group_id),))
    row = cursor.fetchone()
    return row["name"] if row else None


def get_group_names(group_ids: list[str]) -> list[str]:
    return [get_group_name(group_id) or str(group_id) for group_id in group_ids]


def register_user_start(user_id: int):
    user_id = str(user_id)
    row = cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        cursor.execute(
            "UPDATE user_stats SET started_at = CURRENT_TIMESTAMP, start_count = start_count + 1, status = 'started' WHERE user_id = ?",
            (user_id,),
        )
    else:
        cursor.execute(
            "INSERT INTO user_stats (user_id, started_at, start_count, status) VALUES (?, CURRENT_TIMESTAMP, 1, 'started')",
            (user_id,),
        )
    connection.commit()


def start_user_onboarding(user_id: int):
    user_id = str(user_id)
    register_user_start(int(user_id))
    cursor.execute(
        "UPDATE user_stats SET onboarding_step = 'first_name' WHERE user_id = ?",
        (user_id,),
    )
    connection.commit()


def get_user_profile(user_id: int):
    cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (str(user_id),))
    return cursor.fetchone()


def set_user_onboarding_step(user_id: int, step: str):
    cursor.execute("UPDATE user_stats SET onboarding_step = ? WHERE user_id = ?", (step, str(user_id)))
    connection.commit()


def update_user_profile_field(user_id: int, field: str, value):
    allowed = {"first_name", "last_name", "phone", "age", "onboarding_step"}
    if field not in allowed:
        raise ValueError(f"Unsupported profile field: {field}")
    cursor.execute(f"UPDATE user_stats SET {field} = ? WHERE user_id = ?", (value, str(user_id)))
    connection.commit()


def complete_user_onboarding(user_id: int):
    set_user_onboarding_step(user_id, "done")


def register_user_stop(user_id: int):
    user_id = str(user_id)
    row = cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        cursor.execute(
            "UPDATE user_stats SET stopped_at = CURRENT_TIMESTAMP, stop_count = stop_count + 1, status = 'stopped' WHERE user_id = ?",
            (user_id,),
        )
    else:
        cursor.execute(
            "INSERT INTO user_stats (user_id, stopped_at, stop_count, status) VALUES (?, CURRENT_TIMESTAMP, 1, 'stopped')",
            (user_id,),
        )
    connection.commit()


def get_user_counts() -> tuple[int, int]:
    row = cursor.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'started' THEN 1 ELSE 0 END) AS active_users,
            SUM(CASE WHEN status = 'stopped' THEN 1 ELSE 0 END) AS stopped_users
        FROM user_stats
        """
    ).fetchone()
    return int(row["active_users"] or 0), int(row["stopped_users"] or 0)


def get_all_users():
    cursor.execute("SELECT * FROM user_stats ORDER BY started_at DESC")
    return cursor.fetchall()


def delete_message(message_id: int):
    cursor.execute("DELETE FROM sent_messages WHERE message_id = ?", (message_id,))
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    connection.commit()
    return cursor.rowcount


def get_latest_messages(limit: int = 10):
    cursor.execute(
        "SELECT * FROM messages ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return cursor.fetchall()


def get_message(message_id: int):
    cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    return cursor.fetchone()


def update_message_content(message_id: int, new_content: str, new_caption: str = ""):
    cursor.execute("UPDATE messages SET content = ?, caption = ? WHERE id = ?", (new_content, new_caption, message_id))
    connection.commit()
    return cursor.rowcount


def create_schedule(payload: dict, targets: list[str], group_names: list[str], run_at: str, user_id: int):
    cursor.execute(
        """
        INSERT INTO scheduled_messages
        (user_id, type, content, meta, caption, targets, group_names, source_chat_id, source_message_id, run_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(user_id),
            payload["type"],
            payload.get("content", ""),
            payload.get("meta", ""),
            payload.get("caption", ""),
            ",".join(targets),
            ", ".join(group_names),
            str(payload.get("source_chat_id", "")),
            int(payload.get("source_message_id") or 0),
            run_at,
        ),
    )
    connection.commit()
    return cursor.lastrowid


def get_due_schedules(now_iso: str):
    cursor.execute("SELECT * FROM scheduled_messages WHERE status = 'pending' AND run_at <= ? ORDER BY run_at", (now_iso,))
    return cursor.fetchall()


def update_schedule_status(schedule_id: int, status: str, result: str = ""):
    cursor.execute("UPDATE scheduled_messages SET status = ?, result = ? WHERE id = ?", (status, result, schedule_id))
    connection.commit()


def get_schedule_counts() -> tuple[int, int, int]:
    row = cursor.execute(
        """
        SELECT
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
            SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent_count,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count
        FROM scheduled_messages
        """
    ).fetchone()
    return int(row["pending_count"] or 0), int(row["sent_count"] or 0), int(row["failed_count"] or 0)


def get_total_message_count() -> int:
    row = cursor.execute("SELECT COUNT(*) AS total FROM messages").fetchone()
    return int(row["total"] or 0)


def _write_docx(file_path: str, title: str, headers: list[str], rows: list[list[str]]):
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    paragraphs = [f"<w:p><w:r><w:t>{html.escape(title)}</w:t></w:r></w:p>"]
    paragraphs.append(f"<w:p><w:r><w:t>{html.escape(' | '.join(headers))}</w:t></w:r></w:p>")
    for row in rows:
        paragraphs.append(f"<w:p><w:r><w:t>{html.escape(' | '.join(str(value or '') for value in row))}</w:t></w:r></w:p>")

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(paragraphs)}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", document_xml)
    return file_path


def export_users_docx(file_path: str):
    rows = get_all_users()
    return _write_docx(
        file_path,
        "Bot foydalanuvchilari",
        ["user_id", "ism", "familiya", "telefon", "yosh", "status", "start_count", "stop_count", "started_at", "stopped_at"],
        [
            [
                r["user_id"],
                r["first_name"],
                r["last_name"],
                r["phone"],
                r["age"],
                r["status"],
                r["start_count"],
                r["stop_count"],
                r["started_at"],
                r["stopped_at"],
            ]
            for r in rows
        ],
    )


def export_messages_docx(file_path: str):
    rows = get_latest_messages(limit=5000)
    return _write_docx(
        file_path,
        "Bot xabarlari",
        ["id", "type", "targets", "group_names", "content", "caption", "created_at"],
        [[r["id"], r["type"], r["targets"], r["group_names"], r["content"], r["caption"], r["created_at"]] for r in rows],
    )


def export_excel(file_path: str):
    rows = get_latest_messages(limit=1000)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Messages"
    sheet.append(["id", "user_id", "type", "content", "meta", "caption", "targets", "group_names", "created_at"])
    for row in rows:
        sheet.append(
            [
                row["id"],
                row["user_id"],
                row["type"],
                row["content"],
                row["meta"],
                row["caption"],
                row["targets"],
                row["group_names"],
                row["created_at"],
            ]
        )
    workbook.save(file_path)
    return file_path
