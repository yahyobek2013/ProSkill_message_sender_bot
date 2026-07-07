from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove

from database.db import (
    get_admins,
    get_saved_groups,
    get_user_counts,
    get_user_profile,
    is_admin,
    register_user_start,
    register_user_stop,
    start_user_onboarding,
)
from keyboards import build_admin_panel
from user_texts import returning_user_text, user_stop_text, welcome_first_name_text

router = Router()


@router.message(Command(commands=["start"]))
async def start_handler(message: Message):
    register_user_start(message.from_user.id)

    if is_admin(message.from_user.id):
        active, stopped = get_user_counts()
        groups = get_saved_groups()
        admins = get_admins()
        text = (
            "✨ Admin panelga xush kelibsiz!\n\n"
            "📊 Tezkor holat\n"
            f"👥 Faol foydalanuvchilar: {active}\n"
            f"🛑 Botni to'xtatganlar: {stopped}\n"
            f"📚 Guruh/Kanallar: {len(groups)}\n"
            f"🛡 Adminlar: {len(admins)}\n\n"
            "👇 Kerakli bo'limni tanlang. Hamma asosiy amallar tugmalar orqali boshqariladi."
        )
        await message.answer(text, reply_markup=build_admin_panel(message.from_user.id))
        return

    profile = get_user_profile(message.from_user.id)
    if profile and profile["onboarding_step"] == "done" and profile["first_name"]:
        await message.answer(returning_user_text(profile["first_name"]), reply_markup=ReplyKeyboardRemove())
        return

    start_user_onboarding(message.from_user.id)
    await message.answer(welcome_first_name_text(message.from_user.full_name), reply_markup=ReplyKeyboardRemove())


@router.message(Command(commands=["stop"]))
async def stop_handler(message: Message):
    register_user_stop(message.from_user.id)
    await message.answer(user_stop_text())
