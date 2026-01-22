import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

# ===== КОНФИГУРАЦИЯ =====
BOT_TOKEN = "8578950640:AAG-_tcpG0NUAkKp3drcBDU2_tFv-RNbNIs"

# ===== СОЗДАЕМ БОТА И ДИСПЕТЧЕРА ГЛОБАЛЬНО =====
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ===== ЛОГИРОВАНИЕ =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== КЛАВИАТУРЫ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить", callback_data="buy"),
            InlineKeyboardButton(text="📦 Мои покупки", callback_data="purchases")
        ],
        [
            InlineKeyboardButton(text="❓ Как купить", callback_data="how"),
            InlineKeyboardButton(text="🛡 Гарантия", callback_data="guarantee")
        ],
        [
            InlineKeyboardButton(text="⭐ Отзывы", url="https://t.me/otzivumbrella"),
            InlineKeyboardButton(text="💬 Поддержка", url="https://t.me/TakeTGOwner")
        ],
        [
            InlineKeyboardButton(text="📢 Наш канал", url="https://t.me/umbrellatgteam")
        ]
    ])

# ===== БЕЗОПАСНОЕ РЕДАКТИРОВАНИЕ =====
async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None):
    """Безопасное редактирование без ошибок"""
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
    """Обработчик команды /start"""
    try:
        text = (
            "☂️ Добро пожаловать в UmbrellaTeam!\n\n"
            "🎁 Новым клиентам скидка 5⭐ на первый заказ!\n\n"
            "Выбирайте действие:"
        )
        await message.answer(text, reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")

@dp.message(Command("help"))
async def help_command(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "📚 Помощь по боту:\n\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n\n"
        "💬 Поддержка: @TakeTGOwner\n"
        "⭐ Отзывы: https://t.me/otzivumbrella"
    )

# ===== ОБРАБОТЧИКИ КНОПОК =====
@dp.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    """Кнопка 'Купить'"""
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔹 BASIC - 25⭐", callback_data="level_basic")],
        [InlineKeyboardButton(text="⭐ PREMIUM - 50⭐", callback_data="level_premium")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])
    await safe_edit_message(callback, "Выберите уровень:", keyboard)

@dp.callback_query(F.data == "purchases")
async def purchases_handler(callback: CallbackQuery):
    """Кнопка 'Мои покупки'"""
    await callback.answer()
    text = (
        "📦 Ваши покупки:\n\n"
        "У вас пока нет покупок.\n"
        "Совершите первый заказ через меню 'Купить'!\n\n"
        "⬇️ Выберите действие:"
    )
    await safe_edit_message(callback, text, main_menu())

@dp.callback_query(F.data == "how")
async def how_handler(callback: CallbackQuery):
    """Кнопка 'Как купить'"""
    await callback.answer()
    text = (
        "📘 Как купить:\n\n"
        "1️⃣ Нажмите 'Купить'\n"
        "2️⃣ Выберите уровень (BASIC/PREMIUM)\n"
        "3️⃣ Выберите страну\n"
        "4️⃣ Выберите способ оплаты\n"
        "5️⃣ Оплатите и отправьте подтверждение\n"
        "6️⃣ Получите аккаунт!\n\n"
        "🎁 Новым клиентам скидка 5⭐!\n\n"
        "⬇️ Выберите действие:"
    )
    await safe_edit_message(callback, text, main_menu())

@dp.callback_query(F.data == "guarantee")
async def guarantee_handler(callback: CallbackQuery):
    """Кнопка 'Гарантия'"""
    await callback.answer()
    text = (
        "🛡 Гарантия:\n\n"
        "✅ 48 часов на замену аккаунта\n"
        "✅ Быстрая поддержка\n"
        "✅ Возврат при проблемах\n\n"
        "📞 Поддержка: @TakeTGOwner\n\n"
        "⬇️ Выберите действие:"
    )
    await safe_edit_message(callback, text, main_menu())

@dp.callback_query(F.data == "back")
async def back_handler(callback: CallbackQuery):
    """Кнопка 'Назад'"""
    await callback.answer()
    await safe_edit_message(callback, "Главное меню:", main_menu())

@dp.callback_query(F.data.in_(["level_basic", "level_premium"]))
async def level_handler(callback: CallbackQuery):
    """Выбор уровня"""
    await callback.answer()
    level = "BASIC" if "basic" in callback.data else "PREMIUM"
    price = "25⭐" if level == "BASIC" else "50⭐"
    
    text = (
        f"Вы выбрали {level} ({price})\n\n"
        "Временно недоступно. Скоро добавим!\n\n"
        "⬇️ Выберите действие:"
    )
    await safe_edit_message(callback, text, main_menu())

# ===== ОБРАБОТКА ЛЮБЫХ СООБЩЕНИЙ =====
@dp.message()
async def any_message(message: Message):
    """Обработка любых текстовых сообщений"""
    if message.text and not message.text.startswith('/'):
        await message.answer(
            "Используйте кнопки меню или команду /start",
            reply_markup=main_menu()
        )

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
async def initialize_bot():
    """Инициализация бота - ВАЖНО: должна быть асинхронной"""
    try:
        # Проверяем что бот доступен
        me = await bot.get_me()
        print(f"✅ Бот @{me.username} готов к работе!")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации бота: {e}")
        return False

# ===== ГЛАВНАЯ ФУНКЦИЯ =====
async def main():
    """Основная функция для запуска бота"""
    success = await initialize_bot()
    if success:
        print("🤖 Бот инициализирован успешно!")
        print("📡 Режим работы: webhook (через bot_runner.py)")
    else:
        print("⚠️ Бот инициализирован с ошибками")

# ===== ТОЧКА ВХОДА ДЛЯ ЛОКАЛЬНОГО ТЕСТИРОВАНИЯ =====
if __name__ == "__main__":
    # Этот блок выполняется только при запуске main.py напрямую
    # На Render используется bot_runner.py
    print("⚠️ Запуск напрямую не поддерживается на Render")
    print("ℹ️ Используйте: python bot_runner.py")
