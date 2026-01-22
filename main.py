import asyncio
import logging
import random
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8578950640:AAG-_tcpG0NUAkKp3drcBDU2_tFv-RNbNIs"
ADMIN_ID = 700985795
SUPPORT_USERNAME = "TakeTGOwner"
PAY_STARS_USERNAME = "QweAndrey"
REQUIRED_CHANNEL = "@umbrellatgteam"
REVIEWS_URL = "https://t.me/otzivumbrella"
UA_CARD_INFO = "🇺🇦 Карта: 4218 5500 0965 1709"
UA_CARD_NAME = "Andrii Pohodin"
NEWBIE_DISCOUNT_STARS = 5

# ===== БАЗА ДАННЫХ (JSON файл) =====
DB_FILE = "orders.json"

def load_orders():
    """Загружаем заказы из файла"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"orders": {}, "last_id": 0}

def save_orders(data):
    """Сохраняем заказы в файл"""
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_order(user_id, username, level, country, payment_method, price, currency):
    """Добавляем новый заказ"""
    data = load_orders()
    order_id = data["last_id"] + 1
    
    order = {
        "id": order_id,
        "user_id": user_id,
        "username": username,
        "level": level,
        "country": country,
        "payment_method": payment_method,
        "price": price,
        "currency": currency,
        "status": "pending",  # pending, proof_sent, approved, rejected
        "proof_photo": None,
        "proof_text": None,
        "created_at": datetime.now().isoformat(),
        "approved_at": None,
        "admin_id": None
    }
    
    data["orders"][str(order_id)] = order
    data["last_id"] = order_id
    save_orders(data)
    
    return order_id

def get_order(order_id):
    """Получаем заказ по ID"""
    data = load_orders()
    return data["orders"].get(str(order_id))

def update_order_status(order_id, status, proof_photo=None, proof_text=None):
    """Обновляем статус заказа"""
    data = load_orders()
    if str(order_id) in data["orders"]:
        data["orders"][str(order_id)]["status"] = status
        if proof_photo:
            data["orders"][str(order_id)]["proof_photo"] = proof_photo
        if proof_text:
            data["orders"][str(order_id)]["proof_text"] = proof_text
        save_orders(data)
        return True
    return False

def approve_order(order_id, admin_id):
    """Подтверждаем заказ"""
    data = load_orders()
    if str(order_id) in data["orders"]:
        data["orders"][str(order_id)]["status"] = "approved"
        data["orders"][str(order_id)]["approved_at"] = datetime.now().isoformat()
        data["orders"][str(order_id)]["admin_id"] = admin_id
        save_orders(data)
        return True
    return False

def reject_order(order_id, admin_id):
    """Отклоняем заказ"""
    data = load_orders()
    if str(order_id) in data["orders"]:
        data["orders"][str(order_id)]["status"] = "rejected"
        data["orders"][str(order_id)]["admin_id"] = admin_id
        save_orders(data)
        return True
    return False

def get_user_orders(user_id):
    """Получаем все заказы пользователя"""
    data = load_orders()
    user_orders = []
    
    for order_id, order in data["orders"].items():
        if order["user_id"] == user_id:
            user_orders.append(order)
    
    # Сортируем по дате (новые первыми)
    user_orders.sort(key=lambda x: x["created_at"], reverse=True)
    return user_orders

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== ЛОГИРОВАНИЕ =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== КАТАЛОГ И ЦЕНЫ =====
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

# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====
WAITING_PROOF = {}  # user_id: order_id

# ===== ПОЛУЧЕНИЕ НАЗВАНИЯ СТРАНЫ =====
def get_country_name(level: str, code: str) -> str:
    for country_code, country_name in CATALOG[level]["countries"]:
        if country_code == code:
            return country_name
    return code

# ===== КЛАВИАТУРЫ =====
def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 Купить", callback_data="buy"),
            InlineKeyboardButton(text="📦 Мои покупки", callback_data="purchases")
        ],
        [
            InlineKeyboardButton(text="❓ Как купить", callback_data="how"),
            InlineKeyboardButton(text="🛡 Гарантия", callback_data="guarantee")
        ],
        [
            InlineKeyboardButton(text="⭐ Отзывы", url=REVIEWS_URL),
            InlineKeyboardButton(text="💬 Поддержка", url=f"https://t.me/{SUPPORT_USERNAME}")
        ]
    ]
    
    if REQUIRED_CHANNEL:
        keyboard.append([
            InlineKeyboardButton(text="📢 Наш канал", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def levels_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔹 BASIC - 25⭐", callback_data="level:basic"),
            InlineKeyboardButton(text="⭐ PREMIUM - 50⭐", callback_data="level:premium")
        ],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])

def countries_keyboard(level: str):
    countries = CATALOG[level]["countries"]
    buttons = []
    
    for i in range(0, len(countries), 2):
        row = []
        code1, name1 = countries[i]
        row.append(InlineKeyboardButton(text=name1, callback_data=f"country:{level}:{code1}"))
        
        if i + 1 < len(countries):
            code2, name2 = countries[i + 1]
            row.append(InlineKeyboardButton(text=name2, callback_data=f"country:{level}:{code2}"))
        
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="buy")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def payment_keyboard(level: str, country: str):
    has_card = bool(UA_CARD_INFO.strip())
    
    buttons = [
        [InlineKeyboardButton(text="⭐ Оплата Stars", callback_data=f"pay:{level}:{country}:stars")]
    ]
    
    if has_card:
        buttons[0].append(InlineKeyboardButton(text="🇺🇦 Карта", callback_data=f"pay:{level}:{country}:card"))
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"level:{level}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def after_payment_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid:{order_id}")],
        [
            InlineKeyboardButton(text="🔄 Выбрать другой", callback_data="buy"),
            InlineKeyboardButton(text="🏠 Главная", callback_data="back")
        ]
    ])

def admin_keyboard(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin:approve:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{order_id}")
        ]
    ])

# ===== БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ =====
async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
        return True
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "message is not modified" in error_msg or "query is too old" in error_msg:
            await callback.answer()
            return False
        return False
    except Exception:
        return False

# ===== ОБРАБОТЧИКИ КОМАНД =====
@dp.message(CommandStart())
async def start_command(message: Message):
    try:
        text = (
            f"☂️ Добро пожаловать в UmbrellaTeam!\n\n"
            f"🎁 Новым клиентам: скидка {NEWBIE_DISCOUNT_STARS}⭐ на первый Stars-заказ!\n\n"
            "Выбирайте действие:"
        )
        await message.answer(text, reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "📚 Помощь по боту:\n\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        f"💬 Поддержка: @{SUPPORT_USERNAME}\n"
        f"⭐ Отзывы: {REVIEWS_URL}"
    )

# ===== ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ =====
@dp.callback_query(F.data == "back")
async def back_handler(callback: CallbackQuery):
    await callback.answer()
    await safe_edit_message(callback, "Главное меню:", main_menu())

@dp.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    await callback.answer()
    await safe_edit_message(callback, "Выберите уровень:", levels_keyboard())

@dp.callback_query(F.data == "purchases")
async def purchases_handler(callback: CallbackQuery):
    await callback.answer()
    
    # Получаем заказы пользователя
    user_orders = get_user_orders(callback.from_user.id)
    
    if not user_orders:
        text = "📭 У вас пока нет покупок.\nСовершите первый заказ через меню 'Купить'!"
    else:
        text = "📦 Ваши покупки:\n\n"
        for order in user_orders:
            status_icons = {
                "pending": "⏳",
                "proof_sent": "📸",
                "approved": "✅",
                "rejected": "❌"
            }
            
            status = status_icons.get(order["status"], "❓")
            price = f"{order['price']}{order['currency']}"
            
            text += f"{status} Заказ #{order['id']}\n"
            text += f"   Уровень: {order['level'].upper()}\n"
            text += f"   Страна: {order['country']}\n"
            text += f"   Цена: {price}\n"
            
            if order["status"] == "approved" and order.get("approved_at"):
                date = order["approved_at"][:10]
                text += f"   Подтвержден: {date}\n"
            
            text += "\n"
    
    text += "\n⬇️ Выберите действие:"
    await safe_edit_message(callback, text, main_menu())

@dp.callback_query(F.data == "how")
async def how_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "📘 Как купить:\n\n"
        "1️⃣ Нажмите 'Купить'\n"
        "2️⃣ Выберите уровень (BASIC/PREMIUM)\n"
        "3️⃣ Выберите страну\n"
        "4️⃣ Выберите способ оплаты (Stars/Карта)\n"
        "5️⃣ Оплатите и отправьте подтверждение\n"
        "6️⃣ Получите аккаунт!\n\n"
        f"🎁 Новым клиентам скидка {NEWBIE_DISCOUNT_STARS}⭐!\n\n"
        "⬇️ Выберите действие:"
    )
    await safe_edit_message(callback, text, main_menu())

@dp.callback_query(F.data == "guarantee")
async def guarantee_handler(callback: CallbackQuery):
    await callback.answer()
    text = (
        "🛡 Гарантия 48 часов\n\n"
        "✅ В случае проблем с аккаунтом в течение 48 часов — бесплатная замена\n"
        "✅ Быстрая поддержка 24/7\n"
        "✅ Честные условия\n\n"
        f"📞 Поддержка: @{SUPPORT_USERNAME}\n\n"
        "⬇️ Выберите действие:"
    )
    await safe_edit_message(callback, text, main_menu())

# ===== ЛОГИКА ПОКУПКИ =====
@dp.callback_query(F.data.startswith("level:"))
async def level_handler(callback: CallbackQuery):
    await callback.answer()
    level = callback.data.split(":")[1]
    
    text = (
        f"{CATALOG[level]['title']}\n"
        f"⭐ Stars: {STARS_PRICE[level]}⭐\n"
        f"🇺🇦 Карта: {UAH_PRICE[level]} грн\n\n"
        "Выберите страну:"
    )
    
    await safe_edit_message(callback, text, countries_keyboard(level))

@dp.callback_query(F.data.startswith("country:"))
async def country_handler(callback: CallbackQuery):
    await callback.answer()
    _, level, country_code = callback.data.split(":")
    country_name = get_country_name(level, country_code)
    
    text = (
        f"{CATALOG[level]['title']}\n"
        f"Страна: {country_name}\n\n"
        "Выберите способ оплаты:"
    )
    
    await safe_edit_message(callback, text, payment_keyboard(level, country_code))

@dp.callback_query(F.data.startswith("pay:"))
async def payment_handler(callback: CallbackQuery):
    await callback.answer()
    _, level, country_code, method = callback.data.split(":")
    country_name = get_country_name(level, country_code)
    
    # Определяем цену и валюту
    if method == "stars":
        price = STARS_PRICE[level]
        currency = "⭐"
        payment_text = f"Stars подарком на @{PAY_STARS_USERNAME}"
    else:  # card
        price = UAH_PRICE[level]
        currency = " грн"
        payment_text = f"картой Украины\n{UA_CARD_INFO}"
        if UA_CARD_NAME:
            payment_text += f"\nПолучатель: {UA_CARD_NAME}"
    
    # Сохраняем заказ в базу
    order_id = add_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        level=level.upper(),
        country=country_name,
        payment_method=method,
        price=price,
        currency=currency
    )
    
    # Сохраняем для проверки оплаты
    WAITING_PROOF[callback.from_user.id] = order_id
    
    # Формируем текст
    text = (
        f"🧾 Заказ #{order_id}\n"
        f"Уровень: {CATALOG[level]['title']}\n"
        f"Страна: {country_name}\n"
        f"Цена: {price}{currency}\n\n"
        f"💳 Оплата {payment_text}\n"
        f"Сумма: {price}{currency}\n\n"
        "После оплаты нажми «Я оплатил» и отправь подтверждение."
    )
    
    await safe_edit_message(callback, text, after_payment_keyboard(order_id))

@dp.callback_query(F.data.startswith("paid:"))
async def paid_handler(callback: CallbackQuery):
    await callback.answer()
    order_id = int(callback.data.split(":")[1])
    
    # Проверяем что заказ существует и принадлежит пользователю
    order = get_order(order_id)
    if not order or order["user_id"] != callback.from_user.id:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    # Обновляем статус
    update_order_status(order_id, "proof_sent")
    
    text = f"✅ Заказ #{order_id} отмечен как оплаченный.\nТеперь отправь подтверждение (скрин/текст)."
    
    await safe_edit_message(callback, text, None)

# ===== ПОДТВЕРЖДЕНИЯ ОПЛАТЫ =====
@dp.message(F.photo)
async def proof_photo(message: Message):
    if message.from_user.id not in WAITING_PROOF:
        return
    
    order_id = WAITING_PROOF.pop(message.from_user.id)
    file_id = message.photo[-1].file_id
    
    # Обновляем заказ
    update_order_status(order_id, "proof_sent", proof_photo=file_id)
    
    # Получаем данные заказа
    order = get_order(order_id)
    
    # Отправляем админу
    try:
        await bot.send_photo(
            ADMIN_ID,
            file_id,
            caption=(
                f"📸 Подтверждение оплаты\n"
                f"Заказ #{order_id}\n"
                f"От: @{message.from_user.username or message.from_user.id}\n"
                f"Уровень: {order['level']}\n"
                f"Страна: {order['country']}\n"
                f"Сумма: {order['price']}{order['currency']}"
            ),
            reply_markup=admin_keyboard(order_id)
        )
        await message.answer("✅ Скриншот получен! Проверяем оплату, скоро ответим.")
    except Exception as e:
        await message.answer("✅ Скрин получен! Ожидайте проверки.")
        logger.error(f"Ошибка отправки админу: {e}")

@dp.message(F.text)
async def proof_text(message: Message):
    if message.from_user.id not in WAITING_PROOF:
        return
    
    order_id = WAITING_PROOF.pop(message.from_user.id)
    
    # Обновляем заказ
    update_order_status(order_id, "proof_sent", proof_text=message.text)
    
    # Получаем данные заказа
    order = get_order(order_id)
    
    # Отправляем админу
    try:
        await bot.send_message(
            ADMIN_ID,
            f"📝 Подтверждение оплаты (текст)\n"
            f"Заказ #{order_id}\n"
            f"От: @{message.from_user.username or message.from_user.id}\n"
            f"Уровень: {order['level']}\n"
            f"Страна: {order['country']}\n"
            f"Сумма: {order['price']}{order['currency']}\n\n"
            f"Текст: {message.text}",
            reply_markup=admin_keyboard(order_id)
        )
        await message.answer("✅ Текст подтверждения получен! Проверяем оплату.")
    except Exception as e:
        await message.answer("✅ Подтверждение получено! Ожидайте проверки.")
        logger.error(f"Ошибка отправки админу: {e}")

# ===== АДМИН ПАНЕЛЬ (ИСПРАВЛЕННАЯ!) =====
@dp.callback_query(F.data.startswith("admin:"))
async def admin_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    _, action, order_id_str = callback.data.split(":")
    order_id = int(order_id_str)
    
    # Получаем заказ
    order = get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    
    if action == "approve":
        # Подтверждаем заказ
        approve_order(order_id, ADMIN_ID)
        
        # ОТПРАВЛЯЕМ СООБЩЕНИЕ КЛИЕНТУ
        try:
            await bot.send_message(
                order["user_id"],
                f"🎉 Поздравляем! Ваш заказ подтвержден!\n\n"
                f"✅ Заказ #{order_id} оплачен и подтвержден\n"
                f"📊 Уровень: {order['level']}\n"
                f"🌍 Страна: {order['country']}\n\n"
                f"📞 Для получения аккаунта напишите: @{SUPPORT_USERNAME}\n"
                f"💬 Укажите номер заказа: #{order_id}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение клиенту: {e}")
        
        await callback.answer("✅ Заказ подтвержден и клиент уведомлен")
        
        # Обновляем сообщение админу
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ ПОДТВЕРЖДЕНО\n👤 Клиент уведомлен"
        )
    
    elif action == "reject":
        # Отклоняем заказ
        reject_order(order_id, ADMIN_ID)
        
        # ОТПРАВЛЯЕМ СООБЩЕНИЕ КЛИЕНТУ
        try:
            await bot.send_message(
                order["user_id"],
                f"❌ Заказ не подтвержден\n\n"
                f"Заказ #{order_id} отклонен.\n"
                f"Возможные причины:\n"
                f"• Неверные реквизиты оплаты\n"
                f"• Нечеткий скриншот\n"
                f"• Несоответствие суммы\n\n"
                f"📞 Для уточнения напишите: @{SUPPORT_USERNAME}"
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение клиенту: {e}")
        
        await callback.answer("❌ Заказ отклонен и клиент уведомлен")
        
        # Обновляем сообщение админу
        await callback.message.edit_text(
            f"{callback.message.text}\n\n❌ ОТКЛОНЕНО\n👤 Клиент уведомлен"
        )

# ===== ОБРАБОТКА ЛЮБЫХ СООБЩЕНИЙ =====
@dp.message()
async def any_message(message: Message):
    if message.text and not message.text.startswith('/'):
        await message.answer(
            "Используйте кнопки меню или команду /start",
            reply_markup=main_menu()
        )

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
async def initialize_bot():
    try:
        me = await bot.get_me()
        print(f"✅ Бот @{me.username} готов к работе!")
        print(f"📁 База данных: {DB_FILE}")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        return False

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
async def main():
    success = await initialize_bot()
    if success:
        print("🤖 Бот инициализирован успешно!")
        print("📡 Режим работы: webhook")
    else:
        print("⚠️ Бот инициализирован с ошибками")

# ===== ТОЧКА ВХОДА =====
if __name__ == "__main__":
    print("⚠️ Запуск напрямую не поддерживается на Render")
    print("ℹ️ Используйте: python bot_runner.py")
