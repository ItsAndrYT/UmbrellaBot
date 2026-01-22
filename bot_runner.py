import os
import sys
import asyncio
from aiohttp import web

# ===== ВАЖНО: добавляем текущую директорию в путь =====
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Импортируем из main.py
    from main import dp, bot, main
    print("✅ Модули успешно импортированы из main.py")
except Exception as e:
    print(f"❌ Ошибка импорта из main.py: {e}")
    print(f"❌ Возможно в main.py нет dp, bot или main")
    sys.exit(1)

# ===== ОБРАБОТЧИК ВЕБХУКА =====
async def handle_webhook(request):
    """Обработчик запросов от Telegram"""
    try:
        # Получаем данные от Telegram
        data = await request.json()
        
        # Импортируем Update здесь, чтобы избежать циклических импортов
        from aiogram.types import Update
        update = Update(**data)
        
        # ВАЖНО: Обрабатываем асинхронно, не блокируя ответ
        asyncio.create_task(dp.feed_update(bot, update))
        
        # Сразу отвечаем OK
        return web.Response(text="OK")
    except Exception as e:
        # Даже при ошибке отвечаем OK
        print(f"⚠️ Ошибка в webhook (игнорируем): {e}")
        return web.Response(text="OK")

# ===== ПРОВЕРКА ЗДОРОВЬЯ =====
async def handle_health(request):
    """Проверка работоспособности"""
    return web.Response(text="✅ Bot is running!")

# ===== ЗАПУСК БОТА =====
async def startup(app):
    """Выполняется при запуске сервера"""
    print("🚀 Запускаю UmbrellaBot...")
    
    # 1. УДАЛЯЕМ ВСЕ СТАРЫЕ ОБНОВЛЕНИЯ
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Старые обновления Telegram удалены")
    except Exception as e:
        print(f"⚠️ Не удалось удалить старые обновления: {e}")
    
    # 2. Инициализируем бота (функция main() из main.py)
    await main()
    
    # 3. Устанавливаем вебхук на Render
    try:
        render_url = 'https://umbrellabot-cqpu.onrender.com'
        webhook_url = f"{render_url}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"✅ Вебхук установлен: {webhook_url}")
    except Exception as e:
        print(f"⚠️ Ошибка установки вебхука: {e}")

# ===== ОСТАНОВКА =====
async def shutdown(app):
    """Выполняется при остановке сервера"""
    print("🛑 Останавливаю сервер...")
    # НЕ удаляем вебхук - иначе будут ошибки при перезапуске

# ===== СОЗДАНИЕ ПРИЛОЖЕНИЯ =====
def create_app():
    """Создаем веб-приложение"""
    app = web.Application()
    
    # Регистрируем обработчики
    app.router.add_post("/webhook", handle_webhook)  # для Telegram
    app.router.add_get("/", handle_health)           # главная страница
    app.router.add_get("/health", handle_health)     # проверка здоровья
    
    # Добавляем обработчики запуска/остановки
    app.on_startup.append(startup)
    app.on_shutdown.append(shutdown)
    
    return app

# ===== ТОЧКА ВХОДА =====
if __name__ == "__main__":
    print("🤖 Starting UmbrellaBot on Render...")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=10000)
