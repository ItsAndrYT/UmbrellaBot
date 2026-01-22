import os
import sys
import asyncio
from aiohttp import web

# Добавляем текущую папку
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import dp, bot, main
    print("✅ Модули импортированы")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

async def handle_webhook(request):
    """Обработчик вебхуков - УПРОЩЕННЫЙ"""
    try:
        data = await request.json()
        from aiogram.types import Update
        update = Update(**data)
        
        # Обрабатываем НЕМЕДЛЕННО без await
        asyncio.create_task(dp.feed_update(bot, update))
        
        # Сразу отвечаем OK
        return web.Response(text="OK")
    except Exception as e:
        # Даже при ошибке отвечаем OK, чтобы Telegram не повторял запрос
        return web.Response(text="OK")

async def handle_health(request):
    return web.Response(text="✅ Bot is running!")

async def startup(app):
    print("🚀 Запускаю бота...")
    
    # ВАЖНО: Удаляем ВСЕ старые обновления
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Старые обновления удалены")
    except Exception as e:
        print(f"⚠️ Ошибка очистки: {e}")
    
    # Инициализируем базу
    await main()
    
    # Устанавливаем вебхук
    try:
        render_url = 'https://umbrellabot-cqpu.onrender.com'
        webhook_url = f"{render_url}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"✅ Вебхук установлен: {webhook_url}")
    except Exception as e:
        print(f"⚠️ Ошибка вебхука: {e}")

# НЕ удаляем вебхук при shutdown - иначе будут ошибки
async def shutdown(app):
    print("🛑 Остановка сервера...")

def create_app():
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/", handle_health)
    app.router.add_get("/health", handle_health)
    app.on_startup.append(startup)
    app.on_shutdown.append(shutdown)
    return app

if __name__ == "__main__":
    print("🤖 Starting UmbrellaBot...")
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=10000)
