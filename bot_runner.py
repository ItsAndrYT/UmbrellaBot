import os
import sys
import asyncio
from aiohttp import web

# Добавляем текущую папку
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем твоего бота
from main import dp, bot

async def handle_webhook(request):
    """Обработчик вебхуков"""
    try:
        data = await request.json()
        from aiogram.types import Update
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return web.Response(text="ERROR", status=500)

async def handle_health(request):
    return web.Response(text="✅ Bot is running!")

async def startup(app):
    print("🚀 Запускаю бота...")
    
    # Устанавливаем вебхук
    render_url = os.getenv('RENDER_EXTERNAL_URL', '')
    if render_url:
        webhook_url = f"{render_url}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"✅ Вебхук установлен: {webhook_url}")
    else:
        print("⚠️ RENDER_EXTERNAL_URL не найден")

async def shutdown(app):
    await bot.delete_webhook()
    print("🛑 Бот остановлен")

def create_app():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.on_startup.append(startup)
    app.on_shutdown.append(shutdown)
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=10000)