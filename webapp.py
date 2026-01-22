from main import dp, bot
from aiogram import executor
import asyncio
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

async def on_startup(_):
    await bot.set_webhook("https://ваш_username.pythonanywhere.com/")  # пока не знаем URL

if __name__ == '__main__':
    # Этот код будет работать на сервере
    executor.start_webhook(
        dispatcher=dp,
        webhook_path='',
        on_startup=on_startup,
        skip_updates=True,
        host='0.0.0.0',
        port=5000
    )