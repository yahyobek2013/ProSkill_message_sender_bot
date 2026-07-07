from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot_state import state
from config import ADMIN_ID
from database.db import get_admins, get_saved_groups


def build_admin_panel(user_id: int) -> InlineKeyboardMarkup:
    is_owner = int(user_id) == int(ADMIN_ID)
    buttons = [
        [InlineKeyboardButton(text="📤 Xabar yuborish", callback_data="start_broadcast")],
        [
            InlineKeyboardButton(text="📊 Bot statusi", callback_data="bot_status"),
            InlineKeyboardButton(text="💬 Xabarlar", callback_data="list_messages"),
        ],
        [
            InlineKeyboardButton(text="📚 Guruh/Kanallar", callback_data="list_groups"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="user_stats"),
        ],
        [
            InlineKeyboardButton(text="📄 Word: users", callback_data="export_users_docx"),
            InlineKeyboardButton(text="🗂 Word: xabarlar", callback_data="export_messages_docx"),
        ],
    ]

    if is_owner:
        buttons.extend(
            [
                [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")],
                [
                    InlineKeyboardButton(text="🛡 Adminlar", callback_data="list_admins"),
                    InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin"),
                ],
                [
                    InlineKeyboardButton(text="➕ Guruh qo'shish", callback_data="add_group"),
                    InlineKeyboardButton(text="📡 Kanal qo'shish", callback_data="add_channel"),
                ],
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_settings_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛡 Adminlarni ko'rish", callback_data="list_admins"),
                InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin"),
            ],
            [
                InlineKeyboardButton(text="📚 Guruh/Kanallar", callback_data="list_groups"),
                InlineKeyboardButton(text="➕ Guruh qo'shish", callback_data="add_group"),
            ],
            [
                InlineKeyboardButton(text="📩 Adminga xabar", callback_data="message_admin"),
                InlineKeyboardButton(text="📊 Bot statusi", callback_data="bot_status"),
            ],
            [InlineKeyboardButton(text="⬅️ Ortga", callback_data="back_admin_panel")],
        ]
    )


def build_target_selection() -> InlineKeyboardMarkup:
    groups = get_saved_groups()
    selected = state.get("selected_targets", set())
    buttons = []

    all_selected = bool(groups) and len(selected) == len(groups)
    buttons.append(
        [
            InlineKeyboardButton(
                text=("✅ Barchasini tanlash" if all_selected else "☐ Barchasini tanlash"),
                callback_data="toggle_target:all",
            )
        ]
    )

    for row in groups:
        group_id = str(row["id"])
        marker = "✅" if group_id in selected else "☐"
        kind = "📡 Kanal" if row["type"] == "channel" else "👥 Guruh"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{marker} {kind}: {row['name']}",
                    callback_data=f"toggle_target:{group_id}",
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(text="🚀 Hozir yuborish", callback_data="send_broadcast"),
                InlineKeyboardButton(text="⏰ Vaqt belgilash", callback_data="schedule_broadcast"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_flow")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_groups_panel() -> InlineKeyboardMarkup:
    buttons = []
    for row in get_saved_groups():
        buttons.append(
            [
                InlineKeyboardButton(text=row["name"], callback_data=f"meta_group:{row['id']}"),
                InlineKeyboardButton(text="✏️", callback_data=f"edit_group:{row['id']}"),
                InlineKeyboardButton(text="🗑", callback_data=f"delete_group:{row['id']}"),
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(text="➕ Guruh", callback_data="add_group"),
                InlineKeyboardButton(text="📡 Kanal", callback_data="add_channel"),
            ],
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="list_groups")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_admins_panel() -> InlineKeyboardMarkup:
    buttons = []
    for row in get_admins():
        row_buttons = [
            InlineKeyboardButton(text=row["name"], callback_data=f"admin_meta:{row['user_id']}"),
            InlineKeyboardButton(text="✏️", callback_data=f"edit_admin:{row['user_id']}"),
        ]
        if str(row["user_id"]) != str(ADMIN_ID):
            row_buttons.append(InlineKeyboardButton(text="🗑", callback_data=f"delete_admin:{row['user_id']}"))
        buttons.append(row_buttons)

    buttons.extend(
        [
            [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="add_admin")],
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="list_admins")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_messages_panel(rows) -> InlineKeyboardMarkup:
    buttons = []
    for row in rows:
        buttons.append(
            [
                InlineKeyboardButton(text=f"✏️ #{row['id']}", callback_data=f"edit_sent:{row['id']}"),
                InlineKeyboardButton(text="🗑", callback_data=f"delete_message:{row['id']}"),
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔄 Yangilash", callback_data="list_messages")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_year_keyboard() -> InlineKeyboardMarkup:
    current = datetime.now().year
    years = list(range(current, 2051))
    rows = [
        [InlineKeyboardButton(text=str(year), callback_data=f"s_year:{year}") for year in years[index : index + 5]]
        for index in range(0, len(years), 5)
    ]
    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_flow")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_month_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for start in (1, 5, 9):
        rows.append(
            [InlineKeyboardButton(text=f"{month:02d}", callback_data=f"s_month:{month}") for month in range(start, start + 4)]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="s_back_year")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_day_keyboard(year: int, month: int) -> InlineKeyboardMarkup:
    import calendar

    days = calendar.monthrange(year, month)[1]
    rows = []
    for start in range(1, days + 1, 7):
        rows.append(
            [InlineKeyboardButton(text=str(day), callback_data=f"s_day:{day}") for day in range(start, min(start + 7, days + 1))]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="s_back_month")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_hour_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for start in range(0, 24, 6):
        rows.append(
            [InlineKeyboardButton(text=f"{hour:02d}", callback_data=f"s_hour:{hour}") for hour in range(start, start + 6)]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="s_back_day")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_minute_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for start in range(0, 60, 15):
        rows.append(
            [
                InlineKeyboardButton(text=f"{minute:02d}", callback_data=f"s_minute:{minute}")
                for minute in range(start, start + 15, 5)
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Ortga", callback_data="s_back_hour")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard(yes_data: str, no_data: str = "cancel_flow") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=yes_data),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=no_data),
            ]
        ]
    )
