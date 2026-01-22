from aiogram.utils.keyboard import InlineKeyboardBuilder

def kb_main(support_username: str, reviews_url: str = "", channel_url: str = ""):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Купить аккаунт", callback_data="m:buy")
    kb.button(text="🧾 Мои покупки", callback_data="m:orders")
    if reviews_url:
        kb.button(text="🧾 Отзывы", url=reviews_url)
    if channel_url:
        kb.button(text="📌 Наш канал", url=channel_url)
    kb.button(text="📘 Как купить", callback_data="m:how")
    kb.button(text="🛡 Гарантия", callback_data="m:gar")
    kb.button(text="💬 Поддержка", url=f"https://t.me/{support_username}")
    kb.adjust(1)
    return kb.as_markup()

def kb_subscribe(channel_url: str):
    kb = InlineKeyboardBuilder()
    if channel_url:
        kb.button(text="✅ Подписаться", url=channel_url)
    kb.button(text="🔄 Проверить подписку", callback_data="sub:check")
    kb.adjust(1)
    return kb.as_markup()

def kb_levels():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔹 BASIC", callback_data="lvl:basic")
    kb.button(text="⭐ PREMIUM", callback_data="lvl:premium")
    kb.button(text="⬅️ В меню", callback_data="m:home")
    kb.adjust(1)
    return kb.as_markup()

def kb_countries(level_key: str, countries: list[tuple[str, str]]):
    kb = InlineKeyboardBuilder()
    for code, label in countries:
        kb.button(text=label, callback_data=f"cty:{level_key}:{code}")
    kb.button(text="⬅️ Назад", callback_data="m:buy")
    kb.adjust(1)
    return kb.as_markup()

def kb_pay(level_key: str, country_code: str, has_card: bool = True):
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Stars (подарком)", callback_data=f"pay:{level_key}:{country_code}:stars")
    if has_card:
        kb.button(text="🇺🇦 Карта Украины", callback_data=f"pay:{level_key}:{country_code}:card")
    kb.button(text="⬅️ Назад", callback_data=f"lvl:{level_key}")
    kb.adjust(1)
    return kb.as_markup()

def kb_after_invoice(order_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я оплатил", callback_data=f"paid:{order_id}")
    kb.button(text="⬅️ В меню", callback_data="m:home")
    kb.adjust(1)
    return kb.as_markup()

def kb_admin(order_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"adm:ok:{order_id}")
    kb.button(text="❌ Отклонить", callback_data=f"adm:no:{order_id}")
    kb.button(text="🎁 +5 бонус", callback_data=f"adm:bonus:{order_id}:5")
    kb.adjust(2)
    return kb.as_markup()