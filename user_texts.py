def welcome_first_name_text(display_name: str | None = None) -> str:
    name = display_name or "aziz foydalanuvchi"
    return (
        f" "
        # "✨ Sizni botimizda ko'rib turganimdan xursandman.\n"
        # "Boshlash uchun kichik tanishuv qilamiz.\n\n"
        # "📝 Iltimos, ismingizni yozing."
    )


def ask_last_name_text(first_name: str) -> str:
    return (
        f" "
        " ."
    )


def ask_phone_text() -> str:
    return (
        " "
       
    )


def ask_age_text() -> str:
    return (
        " "
        # "Endi yoshingizni yozing. Masalan: 21"
    )


def profile_complete_text(first_name: str, last_name: str, age: int) -> str:
    return (
        f" "
        
    )


def returning_user_text(first_name: str) -> str:
    return (
        f" "
    )


def user_stop_text() -> str:
    return (
        " "
       
    )


def smart_reply_text(text: str, first_name: str = "") -> str:
    normalized = (text or "").lower().strip()
    name = first_name or "do'stim"

    if any(word in normalized for word in ["salom", "assalom", "hello", "hi"]):
        return f""
    if " " in normalized or " " in normalized:
        return ""
    if "" in normalized or "" in normalized:
        return ""
    if any(word in normalized for word in [""]):
        return (
            " "
  
        )
    if " " in normalized:
        return ""
    if any(word in normalized for word in ["rahmat"]):
        return f""

    return (
        f""
        
    )
