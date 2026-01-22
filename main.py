import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from config import (
    BOT_TOKEN, ADMIN_ID, SUPPORT_USERNAME, PAY_STARS_USERNAME,
    UA_CARD_INFO, UA_CARD_NAME, NEWBIE_DISCOUNT_STARS,
    REQUIRED_CHANNEL, REVIEWS_URL
)
from keyboards import (
    kb_main, kb_levels, kb_countries, kb_pay, kb_after_invoice, kb_admin,
    kb_subscribe
)
from db import (
    init_db, upsert_user, get_user, create_order, get_order,
    set_order_status, add_proof, set_first_purchase_done,
    add_bonus, consume_bonus, list_user_orders
)

# ===== Цены =====
STARS_PRICE = {"basic": 25, "premium": 50}
UAH_PRICE = {"basic": 15, "premium": 30}

CATALOG = {
    "basic": {
        "title": "🔹 BASIC",
        "countries": [
            ("IN", "🇮🇳 Индия"),
            ("ID", "🇮🇩 Индонезия"),
            ("PH", "🇵🇭 Филиппины"),
            ("TH", "🇹🇭 Таиланд"),
            ("MY", "🇲🇾 Малайзия"),
            ("BD", "🇧🇩 Бангладеш"),
            ("MM", "🇲🇲 Мьянма"),
            ("NG", "🇳🇬 Нигерия"),
            ("KE", "🇰🇪 Кения"),
            ("EG", "🇪🇬 Египет"),
            ("PE", "🇵🇪 Перу"),
        ],
    },
    "premium": {
        "title": "⭐ PREMIUM",
        "countries": [
            ("US", "🇺🇸 США"),
            ("CA", "🇨🇦 Канада"),
            ("UA", "🇺🇦 Украина"),
            ("BY", "🇧🇾 Беларусь"),
        ],
    }
}

WAITING_PROOF: dict[int, int] = {}

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== HELPERS =====
def channel_url(required: str) -> str:
    return f"https://t.me/{required.lstrip('@')}" if required.startswith("@") else ""

def main_menu_markup():
    return kb_main(
        SUPPORT_USERNAME,
        reviews_url=REVIEWS_URL,
        channel_url=channel_url(REQUIRED_CHANNEL)
    )

async def is_subscribed(user_id: int) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest:
        return False

def country_label(level_key: str, code: str) -> str:
    for c, label in CATALOG[level_key]["countries"]:
        if c == code:
            return label
    return code

def calc_stars_price(base_price: int, is_newbie: bool, bonus_balance: int):
    newbie_discount = NEWBIE_DISCOUNT_STARS if is_newbie else 0
    after_newbie = max(0, base_price - newbie_discount)
    bonus_used = min(bonus_balance, after_newbie)
    final_price = after_newbie - bonus_used
    return newbie_discount, bonus_used, final_price

def pay_text(method: str, stars_amount: int | None, uah_amount: int | None):
    if method == "stars":
        return (
            f"⭐ Оплата Stars подарком на аккаунт @{PAY_STARS_USERNAME}\n"
            f"Сумма: {stars_amount}⭐\n\nПосле оплаты нажми «Я оплатил» и отправь подтверждение."
        )
    name_line = f"\nПолучатель: {UA_CARD_NAME}" if UA_CARD_NAME else ""
    return (
        f"🇺🇦 Оплата картой Украины\n{UA_CARD_INFO}{name_line}\n"
        f"Сумма: {uah_amount} грн 🇺🇦\n\nПосле оплаты нажми «Я оплатил» и отправь скрин перевода."
    )

async def show_sub_gate(target: Message | CallbackQuery):
    text = "☂️ Чтобы пользоваться ботом, подпишись на наш канал 👇\n\nПосле подписки нажми «Проверить подписку»."
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb_subscribe(channel_url(REQUIRED_CHANNEL)))
    else:
        await target.message.edit_text(text, reply_markup=kb_subscribe(channel_url(REQUIRED_CHANNEL)))

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def mention(msg: Message):
    return f"<a href='tg://user?id={msg.from_user.id}'>{msg.from_user.full_name}</a>"

# ===== УНИВЕРСАЛЬНЫЙ РЕДАКТОР СООБЩЕНИЙ =====
async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    """Безопасное редактирование сообщения с защитой от ошибки 'message is not modified'"""
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение уже имеет тот же контент - просто отвечаем callback
            await callback.answer()
            return False
        else:
            # Другая ошибка - пытаемся отправить новое сообщение
            try:
                await callback.message.answer(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                await callback.message.delete()
                return True
            except Exception:
                return False
    except Exception:
        return False

# ===== START =====
@dp.message(CommandStart())
async def start(msg: Message):
    await upsert_user(msg.from_user.id, msg.from_user.username)
    if not await is_subscribed(msg.from_user.id):
        await show_sub_gate(msg)
        return
    
    welcome_text = (
        "☂️ UmbrellaTeam\n\n"
        f"🎁 Новым клиентам: –{NEWBIE_DISCOUNT_STARS}⭐ на первый Stars-заказ\n\n"
        "Выбирай действие 👇"
    )
    
    await msg.answer(welcome_text, reply_markup=main_menu_markup())

# ===== CALLBACKS =====
@dp.callback_query(F.data == "m:home")
async def cb_home(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    text = "Выберите действие:"
    await safe_edit_message(cb, text, main_menu_markup())
    await cb.answer()

@dp.callback_query(F.data == "m:buy")
async def cb_buy(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    text = "Выберите уровень:"
    await safe_edit_message(cb, text, kb_levels())
    await cb.answer()

# ===== КНОПКА "МОИ ПОКУПКИ" =====
@dp.callback_query(F.data == "m:purchases")
async def cb_purchases(cb: CallbackQuery):
    """Кнопка 'Мои покупки'"""
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    # Получаем заказы пользователя
    orders = await list_user_orders(cb.from_user.id)
    
    if not orders:
        text = "📭 У вас пока нет покупок.\n\n⬇️ Выберите действие:"
    else:
        text = "📦 Ваши покупки:\n\n"
        for order in orders:
            status_icons = {
                "pending": "⏳ Ожидает оплаты",
                "proof_required": "📸 Ожидает проверки",
                "approved": "✅ Подтверждено",
                "rejected": "❌ Отклонено"
            }
            
            status = status_icons.get(order["status"], "❓ Неизвестно")
            
            if order["pay_method"] == "stars":
                price = f"{order['stars_final_price']}⭐"
            else:
                price = f"{order['uah_final_price']} грн 🇺🇦"
            
            order_date = order['created_at'][:10] if order['created_at'] else "дата неизвестна"
            
            text += f"🆔 Заказ #{order['id']}\n"
            text += f"   📊 Уровень: {order['level_title']}\n"
            text += f"   🌍 Страна: {order['country_label']}\n"
            text += f"   💰 Стоимость: {price}\n"
            text += f"   📅 Дата: {order_date}\n"
            text += f"   📊 Статус: {status}\n\n"
        
        text += "📞 По вопросам по заказам обращайтесь: @TakeTGOwner\n\n⬇️ Выберите действие:"
    
    await safe_edit_message(cb, text, main_menu_markup())
    await cb.answer()

# ===== КНОПКА "КАК КУПИТЬ" =====
@dp.callback_query(F.data == "m:how")
async def cb_how(cb: CallbackQuery):
    """Кнопка 'Как купить'"""
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    text = (
        "📘 Как происходит покупка:\n\n"
        "1️⃣ Выбираешь уровень и страну\n"
        "2️⃣ Выбираешь оплату (⭐ Stars / 🇺🇦 карта)\n"
        "3️⃣ Нажимаешь «Я оплатил»\n"
        "4️⃣ Отправляешь скрин/пруф оплаты\n"
        "5️⃣ Я подтверждаю — и выдаю аккаунт\n\n"
        f"⭐ Stars: оплата подарком на аккаунт @{PAY_STARS_USERNAME}\n"
        f"🇺🇦 Карта: перевод на украинскую карту\n\n"
        f"🎁 Новым клиентам: скидка {NEWBIE_DISCOUNT_STARS}⭐ на первый Stars-заказ!\n\n"
        "💡 Советы:\n"
        "• Сохраняйте скриншоты оплаты\n"
        "• Указывайте номер заказа при обращении в поддержку\n"
        "• Проверяйте статус заказа в разделе 'Мои покупки'\n\n"
        "📞 Поддержка: @TakeTGOwner\n\n⬇️ Выберите действие:"
    )
    
    await safe_edit_message(cb, text, main_menu_markup())
    await cb.answer()

# ===== КНОПКА "ГАРАНТИЯ" =====
@dp.callback_query(F.data == "m:guarantee")
async def cb_guarantee(cb: CallbackQuery):
    """Кнопка 'Гарантия'"""
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    text = (
        "🛡 Гарантия 48 часов\n\n"
        "✅ В случае проблем с аккаунтом в течение 48 часов после выдачи — бесплатная замена.\n\n"
        "📋 Условия гарантии:\n"
        "• Аккаунт не менял пароль\n"
        "• Не было подозрительной активности\n"
        "• В течение 48 часов с момента выдачи\n"
        "• Вы предоставили доступ только себе\n\n"
        "🔧 Для замены аккаунта:\n"
        "1) Напиши в поддержку: @TakeTGOwner\n"
        "2) Укажи номер заказа\n"
        "3) Опиши проблему подробно\n"
        "4) Приложи скриншоты (если есть)\n\n"
        "⚠️ Гарантия не распространяется:\n"
        "• На нарушение правил платформы\n"
        "• На передачу аккаунта третьим лицам\n"
        "• На истечение 48-часового срока\n\n"
        "📞 По всем вопросам: @TakeTGOwner\n\n⬇️ Выберите действие:"
    )
    
    await safe_edit_message(cb, text, main_menu_markup())
    await cb.answer()

# ===== КНОПКА "ОТЗЫВЫ" =====
@dp.callback_query(F.data == "m:reviews")
async def cb_reviews(cb: CallbackQuery):
    """Кнопка 'Отзывы'"""
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    text = (
        "📢 Отзывы наших клиентов\n\n"
        f"👉 Посмотреть все отзывы можно здесь: {REVIEWS_URL}\n\n"
        "⭐ Средняя оценка: 4.9/5\n"
        "👥 Более 500 довольных клиентов\n"
        "🕐 Работаем с 2023 года\n\n"
        "💬 Что говорят клиенты:\n"
        "• 'Быстрая выдача, все работает'\n"
        "• 'Отличная поддержка, помогли с настройкой'\n"
        "• 'Качественные аккаунты, рекомендую!'\n\n"
        f"📣 Читайте больше отзывов: {REVIEWS_URL}\n\n⬇️ Выберите действие:"
    )
    
    await safe_edit_message(cb, text, main_menu_markup())
    await cb.answer()

@dp.callback_query(F.data.startswith("lvl:"))
async def cb_level(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    level_key = cb.data.split(":")[1]
    stars = STARS_PRICE[level_key]
    uah = UAH_PRICE[level_key]
    
    text = (
        f"{CATALOG[level_key]['title']}\n"
        f"⭐ Stars: {stars}⭐\n"
        f"🇺🇦 Карта: {uah} грн\n\n"
        "Выберите страну:"
    )
    
    await safe_edit_message(cb, text, kb_countries(level_key, CATALOG[level_key]["countries"]))
    await cb.answer()

@dp.callback_query(F.data.startswith("cty:"))
async def cb_country(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    _, level_key, code = cb.data.split(":")
    has_card = bool(UA_CARD_INFO.strip())
    
    text = (
        f"{CATALOG[level_key]['title']}\n"
        f"Страна: {country_label(level_key, code)}\n\n"
        "Выберите оплату:"
    )
    
    await safe_edit_message(cb, text, kb_pay(level_key, code, has_card))
    await cb.answer()

@dp.callback_query(F.data.startswith("pay:"))
async def cb_pay(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await show_sub_gate(cb)
        await cb.answer()
        return
    
    _, level_key, code, method = cb.data.split(":")
    await upsert_user(cb.from_user.id, cb.from_user.username)
    user = await get_user(cb.from_user.id)

    lvl_title = CATALOG[level_key]["title"]
    c_label = country_label(level_key, code)

    if method == "stars":
        base = STARS_PRICE[level_key]
        is_newbie = (user["first_purchase_done"] == 0)
        bonus_balance = int(user["bonus_balance"])
        newbie_discount, bonus_used, final_price = calc_stars_price(base, is_newbie, bonus_balance)

        order_id = await create_order(
            user_id=cb.from_user.id,
            username=cb.from_user.username,
            level_key=level_key,
            level_title=lvl_title,
            country_code=code,
            country_label=c_label,
            pay_method="stars",
            stars_base_price=base,
            stars_newbie_discount=newbie_discount,
            stars_bonus_used=bonus_used,
            stars_final_price=final_price
        )

        text = f"🧾 Заказ #{order_id}\nУровень: {lvl_title}\nСтрана: {c_label}\nЦена: {base}⭐\n"
        if newbie_discount: 
            text += f"🎁 Скидка новичка: –{newbie_discount}⭐\n"
        if bonus_used: 
            text += f"🎁 Списано бонусов: –{bonus_used}⭐\n"
        text += f"К оплате: {final_price}⭐\n\n" + pay_text("stars", final_price, None)
        
        await safe_edit_message(cb, text, kb_after_invoice(order_id))
        await cb.answer()
        return

    # Оплата картой
    uah = UAH_PRICE[level_key]
    order_id = await create_order(
        user_id=cb.from_user.id,
        username=cb.from_user.username,
        level_key=level_key,
        level_title=lvl_title,
        country_code=code,
        country_label=c_label,
        pay_method="card",
        uah_final_price=uah
    )
    
    text = f"🧾 Заказ #{order_id}\nУровень: {lvl_title}\nСтрана: {c_label}\nК оплате: {uah} грн 🇺🇦\n\n" + pay_text("card", None, uah)
    
    await safe_edit_message(cb, text, kb_after_invoice(order_id))
    await cb.answer()

@dp.callback_query(F.data.startswith("paid:"))
async def cb_paid(cb: CallbackQuery):
    order_id = int(cb.data.split(":")[1])
    order = await get_order(order_id)
    
    if not order or int(order["user_id"]) != cb.from_user.id:
        await cb.answer("Заказ не найден.", show_alert=True)
        return
    
    await set_order_status(order_id, "proof_required")
    WAITING_PROOF[cb.from_user.id] = order_id
    
    text = f"✅ Заказ #{order_id} отмечен как оплаченный.\nТеперь отправь подтверждение (скрин/текст)."
    
    await safe_edit_message(cb, text, None)
    await cb.answer()

# ===== ПРУФЫ ОПЛАТЫ =====
@dp.message(F.photo)
async def proof_photo(msg: Message):
    if msg.from_user.id not in WAITING_PROOF:
        return
    
    order_id = WAITING_PROOF.pop(msg.from_user.id)
    file_id = msg.photo[-1].file_id
    await add_proof(order_id, msg.from_user.id, msg.caption, file_id)
    
    order = await get_order(order_id)
    method = order["pay_method"]
    price_line = f"{order['stars_final_price']}⭐" if method=="stars" else f"{order['uah_final_price']} грн 🇺🇦"
    
    caption = (
        f"🔔 Пруф оплаты (фото)\n"
        f"Заказ #{order_id}\n"
        f"Пользователь: {mention(msg)}\n"
        f"{order['level_title']} | {order['country_label']}\n"
        f"К оплате: {price_line}\n"
        f"Метод: {method}"
    )
    
    await bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=kb_admin(order_id))
    await msg.answer("Принял ✅ Проверяю, скоро отвечу в личке.")

@dp.message(F.text)
async def proof_text(msg: Message):
    if msg.from_user.id not in WAITING_PROOF:
        return
    
    order_id = WAITING_PROOF.pop(msg.from_user.id)
    await add_proof(order_id, msg.from_user.id, msg.text, None)
    
    order = await get_order(order_id)
    method = order["pay_method"]
    price_line = f"{order['stars_final_price']}⭐" if method=="stars" else f"{order['uah_final_price']} грн 🇺🇦"
    
    text = (
        f"🔔 Пруф оплаты (текст)\n"
        f"Заказ #{order_id}\n"
        f"Пользователь: {mention(msg)}\n"
        f"{order['level_title']} | {order['country_label']}\n"
        f"К оплате: {price_line}\n"
        f"Метод: {method}\n\n"
        f"Текст:\n{msg.text}"
    )
    
    await bot.send_message(ADMIN_ID, text, reply_markup=kb_admin(order_id))
    await msg.answer("Принял ✅ Проверяю, скоро отвечу в личке.")

# ===== АДМИН ПАНЕЛЬ =====
@dp.callback_query(F.data.startswith("adm:"))
async def admin_actions(cb: CallbackQuery):
    if not is_admin(cb.from_user.id):
        await cb.answer("Нет доступа.", show_alert=True)
        return
    
    _, action, order_id_s, *rest = cb.data.split(":")
    order_id = int(order_id_s)
    order = await get_order(order_id)
    
    if not order:
        await cb.answer("Заказ не найден.", show_alert=True)
        return
    
    user_id = int(order["user_id"])
    
    if action == "ok":
        if order["pay_method"]=="stars":
            bonus_used = int(order["stars_bonus_used"] or 0)
            if bonus_used>0: 
                await consume_bonus(user_id, bonus_used)
            await set_first_purchase_done(user_id)
        
        await set_order_status(order_id, "approved")
        await bot.send_message(
            user_id, 
            f"✅ Оплата подтверждена.\nЗаказ #{order_id}\nНапиши в поддержку: https://t.me/{SUPPORT_USERNAME}"
        )
        await cb.answer("Подтверждено ✅")
    
    elif action=="no":
        await set_order_status(order_id, "rejected")
        await bot.send_message(
            user_id, 
            f"❌ Оплата не подтверждена.\nЗаказ #{order_id}\nЕсли ошибка — отправь снова или напиши в поддержку: https://t.me/{SUPPORT_USERNAME}"
        )
        await cb.answer("Отклонено ❌")
    
    elif action=="bonus":
        amount = int(rest[0]) if rest else 5
        await add_bonus(user_id, amount)
        await bot.send_message(user_id, f"🎁 Начислен бонус: +{amount}⭐")
        await cb.answer(f"Бонус +{amount} ✅")

# ===== ИНИЦИАЛИЗАЦИЯ =====
async def initialize():
    """Инициализация базы данных"""
    await init_db()
    print("✅ База данных инициализирована")
    
    try:
        me = await bot.get_me()
        print(f"🤖 Бот @{me.username} готов к работе!")
    except:
        print("🤖 Бот готов к работе!")

async def setup_webhook():
    """Настройка вебхука"""
    await initialize()

async def main():
    """Основная функция"""
    await setup_webhook()

if __name__ == "__main__":
    # Для локального тестирования (если нужно)
    # asyncio.run(start_polling())
    
    asyncio.run(main())
    print("📡 Бот работает в режиме webhook")
    print("🌐 Для запуска используйте: python bot_runner.py")
