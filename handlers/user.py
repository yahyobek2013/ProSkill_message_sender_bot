from aiogram import Router
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from database.db import (
    complete_user_onboarding,
    get_user_profile,
    is_admin,
    register_user_start,
    set_user_onboarding_step,
    update_user_profile_field,
)
from user_texts import ask_age_text, ask_last_name_text, ask_phone_text, profile_complete_text, smart_reply_text, welcome_first_name_text

router = Router()


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=" ", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="",
    )


def clean_name(value: str | None) -> str:
    return (value or "").strip().replace("\n", " ")


def valid_name(value: str) -> bool:
    return len(value) >= 2 and any(char.isalpha() for char in value)


def clean_phone(message: Message) -> str:
    if message.contact and message.contact.phone_number:
        return message.contact.phone_number.strip()
    return (message.text or "").strip()


def valid_phone(value: str) -> bool:
    digits = "".join(char for char in value if char.isdigit())
    return 7 <= len(digits) <= 15


@router.message(lambda message: not is_admin(message.from_user.id))
async def user_message_handler(message: Message):
    profile = get_user_profile(message.from_user.id)
    if not profile:
        register_user_start(message.from_user.id)
        set_user_onboarding_step(message.from_user.id, "first_name")
        await message.answer(welcome_first_name_text(message.from_user.full_name), reply_markup=ReplyKeyboardRemove())
        return

    step = profile["onboarding_step"] or ""

    if step in {"", "first_name"}:
        first_name = clean_name(message.text)
        if not valid_name(first_name):
            await message.answer(" ")
            return
        update_user_profile_field(message.from_user.id, "first_name", first_name)
        set_user_onboarding_step(message.from_user.id, "last_name")
        await message.answer(ask_last_name_text(first_name))
        return

    if step == "last_name":
        last_name = clean_name(message.text)
        if not valid_name(last_name):
            await message.answer(" ")
            return
        update_user_profile_field(message.from_user.id, "last_name", last_name)
        set_user_onboarding_step(message.from_user.id, "phone")
        await message.answer(ask_phone_text(), reply_markup=phone_keyboard())
        return

    if step == "phone":
        phone = clean_phone(message)
        if not valid_phone(phone):
            await message.answer(
                "📱 Telefon raqam tushunarsiz ko'rindi.\n\n"
                "Iltimos, pastdagi tugma orqali kontakt yuboring yoki +998901234567 ko'rinishida yozing.",
                reply_markup=phone_keyboard(),
            )
            return
        update_user_profile_field(message.from_user.id, "phone", phone)
        set_user_onboarding_step(message.from_user.id, "age")
        await message.answer(ask_age_text(), reply_markup=ReplyKeyboardRemove())
        return

    if step == "age":
        if not message.text or not message.text.strip().isdigit():
            await message.answer(" ")
            return
        age = int(message.text.strip())
        if age < 7 or age > 100:
            await message.answer(" ")
            return
        update_user_profile_field(message.from_user.id, "age", age)
        complete_user_onboarding(message.from_user.id)
        profile = get_user_profile(message.from_user.id)
        await message.answer(
            profile_complete_text(profile["first_name"], profile["last_name"], profile["age"]),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await message.answer(smart_reply_text(message.text or message.caption or "", profile["first_name"] or ""))
