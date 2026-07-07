from pathlib import Path

from aiogram import Router
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from bot_state import reset_state, state
from bot_status import build_bot_status_text
from config import ADMIN_ID
from database.db import (
    delete_admin,
    delete_group,
    delete_message,
    export_messages_docx,
    export_users_docx,
    get_admins,
    get_admin_name,
    get_latest_messages,
    get_saved_groups,
    get_sent_messages,
    get_user_counts,
    is_admin,
)
from keyboards import (
    build_admin_panel,
    build_admins_panel,
    build_groups_panel,
    build_messages_panel,
    build_settings_panel,
    confirm_keyboard,
)

router = Router()


def _is_owner(user_id: int) -> bool:
    return int(user_id) == int(ADMIN_ID)


def _owner_only(callback: CallbackQuery) -> bool:
    return _is_owner(callback.from_user.id)


@router.callback_query(
    lambda c: c.data
    in {
        "start_broadcast",
        "admin_settings",
        "back_admin_panel",
        "bot_status",
        "user_stats",
        "list_groups",
        "add_group",
        "add_channel",
        "list_admins",
        "add_admin",
        "message_admin",
        "list_messages",
        "export_users_docx",
        "export_messages_docx",
        "cancel_flow",
    }
)
async def admin_actions(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    data = callback.data

    if data == "cancel_flow":
        if not state.get("mode"):
            await callback.answer("Bekor qilinadigan faol jarayon yo'q.", show_alert=True)
            return
        reset_state()
        await callback.message.answer("Jarayon bekor qilindi. Xohlasangiz, paneldan qayta boshlashingiz mumkin.")
        await callback.answer()
        return

    if data == "back_admin_panel":
        await callback.message.edit_text(
            "Admin panel\n\nKerakli bo'limni tanlang.",
            reply_markup=build_admin_panel(callback.from_user.id),
        )
        await callback.answer()
        return

    if data == "admin_settings":
        if not _owner_only(callback):
            await callback.answer("Bu bo'lim faqat asosiy admin uchun.", show_alert=True)
            return
        await callback.message.edit_text(
            "Bot sozlamalari\n\nAdminlar, guruhlar, kanallar va xizmat holatini shu yerdan boshqaring.",
            reply_markup=build_settings_panel(),
        )
        await callback.answer()
        return

    if data == "bot_status":
        await callback.message.answer(build_bot_status_text(), reply_markup=build_admin_panel(callback.from_user.id))
        await callback.answer()
        return

    if data == "start_broadcast":
        if state.get("mode"):
            await callback.answer(
                "Xabar yuborish jarayoni allaqachon boshlangan. Avval uni yakunlang yoki bekor qiling.",
                show_alert=True,
            )
            return
        reset_state()
        state["mode"] = "waiting_for_message"
        await callback.message.answer(
            "Yuboriladigan postni yuboring.\n\n"
            "Matn, rasm, video, gif, sticker, document, audio, voice yoki captionli media qabul qilinadi. "
            "Bot uni tanlangan guruh va kanallarga Telegram nusxasi sifatida yuboradi."
        )
        await callback.answer()
        return

    if data in {"add_group", "add_channel"}:
        if not _owner_only(callback):
            await callback.answer("Guruh yoki kanal qo'shish faqat asosiy admin uchun.", show_alert=True)
            return
        reset_state()
        state["mode"] = "waiting_for_group_id"
        state["new_group_type"] = "channel" if data == "add_channel" else "group"
        kind = "kanal" if data == "add_channel" else "guruh"
        await callback.message.answer(
            f"Yangi {kind} ID sini yuboring.\n\nMasalan: -1001234567890\n"
            "Bot o'sha guruh/kanalda admin bo'lishi kerak."
        )
        await callback.answer()
        return

    if data == "add_admin":
        if not _owner_only(callback):
            await callback.answer("Admin qo'shish faqat asosiy admin uchun.", show_alert=True)
            return
        reset_state()
        state["mode"] = "waiting_for_admin_id"
        await callback.message.answer("Yangi adminning Telegram ID raqamini yuboring. Masalan: 123456789")
        await callback.answer()
        return

    if data == "list_admins":
        if not _owner_only(callback):
            await callback.answer("Adminlar ro'yxati faqat asosiy admin uchun.", show_alert=True)
            return
        admins = get_admins()
        text = "Adminlar ro'yxati\n\n" + "\n".join(
            f"{idx}. {row['name']} - {row['user_id']} ({row['role']})" for idx, row in enumerate(admins, start=1)
        )
        await callback.message.answer(text, reply_markup=build_admins_panel())
        await callback.answer()
        return

    if data == "message_admin":
        if not _owner_only(callback):
            await callback.answer("Bu amal faqat asosiy admin uchun.", show_alert=True)
            return
        rows = []
        for admin in get_admins():
            rows.append([InlineKeyboardButton(text=admin["name"], callback_data=f"msg_admin_to:{admin['user_id']}")])
        rows.append([InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_flow")])
        await callback.message.answer("Qaysi adminga xabar yuboramiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        await callback.answer()
        return

    if data == "list_groups":
        groups = get_saved_groups()
        if not groups:
            await callback.message.answer(
                "Hozircha guruh yoki kanal qo'shilmagan.",
                reply_markup=build_groups_panel() if _owner_only(callback) else None,
            )
        else:
            lines = []
            for idx, row in enumerate(groups, start=1):
                owner_name = row["added_by_name"] or get_admin_name(row["added_by"]) or row["added_by"] or "Noma'lum"
                lines.append(f"{idx}. {row['name']} | {row['type']} | {row['id']} | qo'shgan: {owner_name}")
            await callback.message.answer("Guruh va kanallar\n\n" + "\n".join(lines), reply_markup=build_groups_panel())
        await callback.answer()
        return

    if data == "user_stats":
        active, stopped = get_user_counts()
        await callback.message.answer(
            "Foydalanuvchilar statistikasi\n\n"
            f"Faol foydalanuvchilar: {active}\n"
            f"Botni to'xtatganlar: {stopped}\n\n"
            "To'liq ro'yxatni Word fayl qilib yuklab olishingiz mumkin.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Wordga yuklash", callback_data="export_users_docx")]]
            ),
        )
        await callback.answer()
        return

    if data == "list_messages":
        rows = get_latest_messages(10)
        if not rows:
            await callback.message.answer("Hozircha saqlangan xabar yo'q.")
        else:
            lines = []
            for row in rows:
                lines.append(
                    f"#{row['id']} | {row['type']} | {row['created_at']}\n"
                    f"Manzil: {row['group_names'] or row['targets'] or 'Nomalum'}\n"
                    f"Matn: {str(row['content'] or row['caption'] or '')[:120]}"
                )
            await callback.message.answer("So'nggi xabarlar\n\n" + "\n\n".join(lines), reply_markup=build_messages_panel(rows))
        await callback.answer()
        return

    if data == "export_users_docx":
        file_path = Path("./media/users.docx")
        export_users_docx(str(file_path))
        await callback.message.answer_document(FSInputFile(str(file_path)))
        await callback.answer()
        return

    if data == "export_messages_docx":
        file_path = Path("./media/messages.docx")
        export_messages_docx(str(file_path))
        await callback.message.answer_document(FSInputFile(str(file_path)))
        await callback.answer()
        return


@router.callback_query(lambda c: c.data and c.data.startswith("meta_group:"))
async def meta_group_info(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    gid = callback.data.split(":", 1)[1]
    row = next((group for group in get_saved_groups() if str(group["id"]) == gid), None)
    if not row:
        await callback.answer("Topilmadi", show_alert=True)
        return
    owner_name = row["added_by_name"] or get_admin_name(row["added_by"]) or row["added_by"] or "Noma'lum"
    await callback.message.answer(f"Nomi: {row['name']}\nTuri: {row['type']}\nID: {row['id']}\nQo'shgan: {owner_name}")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("edit_group:"))
async def edit_group(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Faqat asosiy admin tahrirlay oladi.", show_alert=True)
        return
    gid = callback.data.split(":", 1)[1]
    state["mode"] = "editing_group"
    state["edit_group_id"] = gid
    await callback.message.answer("Yangi nomni yuboring.")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("delete_group:"))
async def ask_delete_group(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Faqat asosiy admin o'chira oladi.", show_alert=True)
        return
    gid = callback.data.split(":", 1)[1]
    await callback.message.answer(
        f"ID {gid} bo'lgan guruh/kanal o'chirilsinmi?",
        reply_markup=confirm_keyboard(f"confirm_delete_group:{gid}"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_delete_group:"))
async def confirm_delete_group(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    gid = callback.data.split(":", 1)[1]
    deleted = delete_group(gid)
    await callback.message.answer("O'chirildi." if deleted else "Topilmadi.")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("admin_meta:"))
async def admin_meta(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    uid = callback.data.split(":", 1)[1]
    row = next((admin for admin in get_admins() if str(admin["user_id"]) == uid), None)
    if not row:
        await callback.answer("Admin topilmadi", show_alert=True)
        return
    await callback.message.answer(f"Admin: {row['name']}\nID: {row['user_id']}\nRol: {row['role']}")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("edit_admin:"))
async def edit_admin(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    uid = callback.data.split(":", 1)[1]
    state["mode"] = "editing_admin"
    state["edit_admin_id"] = uid
    await callback.message.answer("Admin uchun yangi ko'rinadigan nomni yuboring.")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("delete_admin:"))
async def ask_delete_admin(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    uid = callback.data.split(":", 1)[1]
    if str(uid) == str(ADMIN_ID):
        await callback.answer("Asosiy admin o'chirilmaydi.", show_alert=True)
        return
    await callback.message.answer(f"Admin {uid} o'chirilsinmi?", reply_markup=confirm_keyboard(f"confirm_delete_admin:{uid}"))
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_delete_admin:"))
async def confirm_delete_admin(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    uid = callback.data.split(":", 1)[1]
    deleted = delete_admin(uid)
    await callback.message.answer("Admin o'chirildi." if deleted else "Admin topilmadi.")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("msg_admin_to:"))
async def select_admin_message_target(callback: CallbackQuery):
    if not _owner_only(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    state["mode"] = "waiting_admin_message"
    state["pending_admin_message_id"] = callback.data.split(":", 1)[1]
    await callback.message.answer("Adminga yuboriladigan xabarni yuboring. Bot uni shaxsiy chatga ko'chirib beradi.")
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("delete_message:"))
async def ask_delete_message(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    message_id = int(callback.data.split(":", 1)[1])
    await callback.message.answer(
        f"Xabar yozuvi #{message_id} bazadan o'chirilsinmi?",
        reply_markup=confirm_keyboard(f"confirm_delete_message:{message_id}"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_delete_message:"))
async def confirm_delete_message(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    message_id = int(callback.data.split(":", 1)[1])
    copies = get_sent_messages(message_id)
    deleted_in_chats = 0
    for copy in copies:
        try:
            await callback.bot.delete_message(copy["target_chat_id"], copy["target_message_id"])
            deleted_in_chats += 1
        except Exception:
            continue
    deleted = delete_message(message_id)
    await callback.message.answer(
        f"Yozuv o'chirildi. Chatlardan o'chirilgan nusxalar: {deleted_in_chats}." if deleted else "Xabar topilmadi."
    )
    await callback.answer()
