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
    """Обработчик вебхуков"""
    try:
        data = await request.json()
        from aiogram.types import Update
        update = Update(**data)
        
        # Обрабатываем асинхронно, не блокируя ответ
        asyncio.create_task(dp.feed_update(bot, update))
        
        return web.Response(text="OK")
    except Exception as e:
        print(f"⚠️ Ошибка в webhook (игнорируем): {e}")
        return web.Response(text="OK")  # Всегда отвечаем OK

async def handle_health(request):
    return web.Response(text="✅ Bot is running!")

async def startup(app):
    print("🚀 Запускаю бота...")
    
    # 1. УДАЛЯЕМ ВСЕ СТАРЫЕ ОБНОВЛЕНИЯ
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Старые обновления удалены")
    except Exception as e:
        print(f"⚠️ Не удалось удалить старые обновления: {e}")
    
    # 2. Инициализируем бота
    await main()
    
    # 3. Устанавливаем вебхук заново
    try:
        render_url = 'https://umbrellabot-cqpu.onrender.com'
        webhook_url = f"{render_url}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"✅ Вебхук установлен: {webhook_url}")
    except Exception as e:
        print(f"⚠️ Ошибка вебхука: {e}")

async def shutdown(app):
    try:
        await bot.delete_webhook()
        print("🛑 Вебхук удален")
    except:
        pass

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
