from datetime import datetime

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from bot_state import reset_state, state
from database.db import (
    add_admin,
    add_group,
    create_schedule,
    get_group_names,
    get_message,
    get_saved_groups,
    get_sent_messages,
    group_exists,
    is_admin,
    update_admin_name,
    update_group_name,
    update_message_content,
)
from keyboards import (
    build_day_keyboard,
    build_hour_keyboard,
    build_minute_keyboard,
    build_month_keyboard,
    build_target_selection,
    build_year_keyboard,
)
from scheduler import send_payload_to_targets

router = Router()


def get_message_type(message: Message) -> str:
    if message.text:
        return "text"
    if message.photo:
        return "photo"
    if message.video:
        return "video"
    if message.animation:
        return "animation"
    if message.sticker:
        return "sticker"
    if message.document:
        return "document"
    if message.audio:
        return "audio"
    if message.voice:
        return "voice"
    if message.video_note:
        return "video_note"
    return "copy"


def _extract_content(message: Message, message_type: str) -> str:
    if message_type == "text":
        return message.text or ""
    if message_type == "photo":
        return message.photo[-1].file_id
    media = getattr(message, message_type, None)
    return getattr(media, "file_id", "") if media else ""


@router.message(lambda message: is_admin(message.from_user.id))
async def handle_admin_messages(message: Message):
    mode = state.get("mode")

    if mode == "waiting_for_group_id":
        if not message.text or not message.text.strip().startswith("-100"):
            await message.answer("Iltimos, guruh yoki kanal ID sini -100 bilan boshlanadigan formatda yuboring.")
            return
        group_id = message.text.strip()
        if group_exists(group_id):
            await message.answer("Bu ID allaqachon ro'yxatda bor. Boshqa ID yuboring.")
            return
        state["new_group_id"] = group_id
        state["mode"] = "waiting_for_group_name"
        await message.answer("Endi shu guruh/kanal uchun chiroyli nom yuboring.")
        return

    if mode == "waiting_for_group_name":
        if not message.text:
            await message.answer("Nom matn ko'rinishida bo'lishi kerak.")
            return
        group_type = state.get("new_group_type") or "group"
        add_group(
            state["new_group_id"],
            message.text.strip(),
            str(message.from_user.id),
            message.from_user.username or message.from_user.full_name or "",
            group_type,
        )
        added_id = state["new_group_id"]
        reset_state()
        await message.answer(f"Qo'shildi.\n\nID: {added_id}\nNom: {message.text.strip()}")
        return

    if mode == "waiting_for_admin_id":
        if not message.text or not message.text.strip().isdigit():
            await message.answer("Admin ID faqat raqamlardan iborat bo'lishi kerak.")
            return
        state["new_admin_id"] = message.text.strip()
        state["mode"] = "waiting_for_admin_name"
        await message.answer("Admin uchun ko'rinadigan nom yuboring.")
        return

    if mode == "waiting_for_admin_name":
        if not message.text:
            await message.answer("Iltimos, admin nomini matn qilib yuboring.")
            return
        add_admin(state["new_admin_id"], message.text.strip())
        new_admin_id = state["new_admin_id"]
        reset_state()
        await message.answer(f"Admin qo'shildi.\n\nID: {new_admin_id}\nNom: {message.text.strip()}")
        return

    if mode == "editing_group":
        if not message.text:
            await message.answer("Yangi nom matn ko'rinishida bo'lishi kerak.")
            return
        updated = update_group_name(state["edit_group_id"], message.text.strip())
        reset_state()
        await message.answer("Guruh/kanal nomi yangilandi." if updated else "Yangilashda xatolik bo'ldi.")
        return

    if mode == "editing_admin":
        if not message.text:
            await message.answer("Yangi nom matn ko'rinishida bo'lishi kerak.")
            return
        updated = update_admin_name(state["edit_admin_id"], message.text.strip())
        reset_state()
        await message.answer("Admin nomi yangilandi." if updated else "Yangilashda xatolik bo'ldi.")
        return

    if mode == "waiting_admin_message":
        target_admin = state.get("pending_admin_message_id")
        reset_state()
        try:
            await message.bot.copy_message(target_admin, message.chat.id, message.message_id)
            await message.answer("Xabar adminga yuborildi.")
        except Exception:
            await message.answer("Xabar yuborilmadi. Admin avval botga /start bosgan bo'lishi kerak.")
        return

    if mode == "waiting_for_message":
        groups = get_saved_groups()
        if not groups:
            await message.answer("Avval kamida bitta guruh yoki kanal qo'shing.")
            return

        message_type = get_message_type(message)
        state["draft"] = {
            "type": message_type,
            "content": _extract_content(message, message_type),
            "caption": message.caption or "",
            "source_chat_id": message.chat.id,
            "source_message_id": message.message_id,
        }
        state["mode"] = "choose_targets"
        state["selected_targets"] = set()
        await message.answer(
            "Xabar tayyor.\n\nEndi guruh yoki kanallarni tanlang. Bosilganda [x] belgisi qo'yiladi, yana bossangiz olib tashlanadi.",
            reply_markup=build_target_selection(),
        )
        return

    if mode == "editing_sent_message":
        if not message.text and not message.caption:
            await message.answer("Tahrirlash uchun yangi matn yoki captionli media yuboring.")
            return

        message_id = state.get("edit_id")
        row = get_message(message_id)
        if not row:
            reset_state()
            await message.answer("Bu xabar bazadan topilmadi.")
            return

        new_text = message.text or message.caption or ""
        copies = get_sent_messages(message_id)
        edited = 0
        for copy in copies:
            try:
                if row["type"] == "text":
                    await message.bot.edit_message_text(new_text, chat_id=copy["target_chat_id"], message_id=copy["target_message_id"])
                else:
                    await message.bot.edit_message_caption(
                        chat_id=copy["target_chat_id"],
                        message_id=copy["target_message_id"],
                        caption=new_text,
                    )
                edited += 1
            except Exception:
                continue

        update_message_content(message_id, new_text, "" if row["type"] == "text" else new_text)
        reset_state()
        await message.answer(
            f"Xabar bazada yangilandi. Telegramdagi yangilangan nusxalar: {edited}/{len(copies)}.\n"
            "Eslatma: Telegram faqat matn va captionni tahrirlashga ruxsat beradi."
        )


@router.callback_query(lambda c: c.data and c.data.startswith("toggle_target:"))
async def toggle_target(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    if state.get("mode") != "choose_targets" or not state.get("draft"):
        await callback.answer("Avval xabar yuboring.", show_alert=True)
        return

    value = callback.data.split(":", 1)[1]
    groups = get_saved_groups()
    selected = state.setdefault("selected_targets", set())
    if value == "all":
        all_ids = {str(row["id"]) for row in groups}
        state["selected_targets"] = set() if selected == all_ids else all_ids
    else:
        if value in selected:
            selected.remove(value)
        else:
            selected.add(value)

    try:
        await callback.message.edit_reply_markup(reply_markup=build_target_selection())
    except Exception:
        await callback.message.answer("Tanlov yangilandi.", reply_markup=build_target_selection())
    await callback.answer()


@router.callback_query(lambda c: c.data == "send_broadcast")
async def send_broadcast(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    if state.get("mode") != "choose_targets" or not state.get("draft"):
        await callback.answer("Avval xabar va manzil tanlang.", show_alert=True)
        return

    targets = list(state.get("selected_targets") or [])
    if not targets:
        await callback.answer("Kamida bitta guruh yoki kanal tanlang.", show_alert=True)
        return
    group_names = get_group_names(targets)
    payload = dict(state["draft"])
    success, saved_id = await send_payload_to_targets(callback.bot, payload, targets, group_names, callback.from_user.id)
    reset_state()
    await callback.message.answer(
        f"Yuborish yakunlandi: {success}/{len(targets)}.\n"
        f"Xabar ID: {saved_id}\n"
        f"Manzillar: {', '.join(group_names)}"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "schedule_broadcast")
async def start_schedule(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    if state.get("mode") != "choose_targets" or not state.get("draft"):
        await callback.answer("Avval xabar va manzil tanlang.", show_alert=True)
        return
    if not state.get("selected_targets"):
        await callback.answer("Kamida bitta guruh yoki kanal tanlang.", show_alert=True)
        return
    state["mode"] = "schedule_year"
    await callback.message.answer("Yuboriladigan yilni tanlang.", reply_markup=build_year_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("s_year:"))
async def schedule_year(callback: CallbackQuery):
    state["schedule_year"] = int(callback.data.split(":", 1)[1])
    state["mode"] = "schedule_month"
    await callback.message.edit_text("Oyni tanlang.", reply_markup=build_month_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "s_back_year")
async def schedule_back_year(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    state["mode"] = "schedule_year"
    await callback.message.edit_text("Yuboriladigan yilni tanlang.", reply_markup=build_year_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("s_month:"))
async def schedule_month(callback: CallbackQuery):
    state["schedule_month"] = int(callback.data.split(":", 1)[1])
    state["mode"] = "schedule_day"
    await callback.message.edit_text(
        "Kunni tanlang.",
        reply_markup=build_day_keyboard(state["schedule_year"], state["schedule_month"]),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "s_back_month")
async def schedule_back_month(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    state["mode"] = "schedule_month"
    await callback.message.edit_text("Oyni tanlang.", reply_markup=build_month_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("s_day:"))
async def schedule_day(callback: CallbackQuery):
    state["schedule_day"] = int(callback.data.split(":", 1)[1])
    state["mode"] = "schedule_hour"
    await callback.message.edit_text("Soatni tanlang.", reply_markup=build_hour_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "s_back_day")
async def schedule_back_day(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    state["mode"] = "schedule_day"
    await callback.message.edit_text(
        "Kunni tanlang.",
        reply_markup=build_day_keyboard(state["schedule_year"], state["schedule_month"]),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("s_hour:"))
async def schedule_hour(callback: CallbackQuery):
    state["schedule_hour"] = int(callback.data.split(":", 1)[1])
    state["mode"] = "schedule_minute"
    await callback.message.edit_text("Daqiqani tanlang.", reply_markup=build_minute_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data == "s_back_hour")
async def schedule_back_hour(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    state["mode"] = "schedule_hour"
    await callback.message.edit_text("Soatni tanlang.", reply_markup=build_hour_keyboard())
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("s_minute:"))
async def schedule_minute(callback: CallbackQuery):
    state["schedule_minute"] = int(callback.data.split(":", 1)[1])
    run_at = datetime(
        state["schedule_year"],
        state["schedule_month"],
        state["schedule_day"],
        state["schedule_hour"],
        state["schedule_minute"],
    )
    if run_at <= datetime.now():
        await callback.answer("Vaqt kelajakda bo'lishi kerak.", show_alert=True)
        return

    targets = list(state.get("selected_targets") or [])
    group_names = get_group_names(targets)
    schedule_id = create_schedule(
        state["draft"],
        targets,
        group_names,
        run_at.strftime("%Y-%m-%d %H:%M:%S"),
        callback.from_user.id,
    )
    reset_state()
    await callback.message.edit_text(
        f"Rejalashtirildi.\n\nID: {schedule_id}\nVaqt: {run_at:%Y-%m-%d %H:%M}\nManzillar: {', '.join(group_names)}"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("edit_sent:"))
async def edit_sent(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    message_id = int(callback.data.split(":", 1)[1])
    row = get_message(message_id)
    if not row:
        await callback.answer("Xabar topilmadi", show_alert=True)
        return
    state["mode"] = "editing_sent_message"
    state["edit_id"] = message_id
    await callback.message.answer(
        "Yangi matnni yuboring.\n\n"
        "Agar asl xabar media bo'lsa, media fayl o'zgarmaydi, caption tahrirlanadi. "
        "Matnli xabarda esa matn barcha yuborilgan chatlarda tahrirlanadi."
    )
    await callback.answer()
