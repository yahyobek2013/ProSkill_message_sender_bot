from datetime import datetime

from database.db import get_admins, get_saved_groups, get_schedule_counts, get_total_message_count, get_user_counts

STARTED_AT = datetime.now()


def build_bot_status_text() -> str:
    active_users, stopped_users = get_user_counts()
    groups = get_saved_groups()
    admins = get_admins()
    pending, sent, failed = get_schedule_counts()
    uptime = datetime.now() - STARTED_AT
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    return (
        "📊 Bot statusi\n\n"
        f"🟢 Holat: faol\n"
        f"⏱ Ishlagan vaqt: {hours:02d}:{minutes:02d}:{seconds:02d}\n"
        f"👥 Faol foydalanuvchilar: {active_users}\n"
        f"🛑 To'xtatgan foydalanuvchilar: {stopped_users}\n"
        f"📚 Guruh/Kanallar: {len(groups)}\n"
        f"🛡 Adminlar: {len(admins)}\n"
        f"💬 Yuborilgan xabar yozuvlari: {get_total_message_count()}\n"
        f"⏳ Rejadagi xabarlar: {pending}\n"
        f"✅ Reja bo'yicha yuborilgan: {sent}\n"
        f"⚠️ Rejada xato bo'lgan: {failed}\n\n"
        "✨ Hammasi nazorat ostida. Kerakli bo'limni tugmalardan tanlang."
    )
