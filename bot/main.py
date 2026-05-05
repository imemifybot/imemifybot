import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables FIRST.
# Local dev: allow `bot/.env` (optional).
# Production (Railway): env vars are injected by the platform.
_bot_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_bot_env_path):
    load_dotenv(_bot_env_path)
load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.fsm.storage.memory import MemoryStorage
from database.db import init_db
from handlers.start import router as start_router
from handlers.payment import router as payment_router
from handlers.admin import router as admin_router
from handlers.memebuilder import router as memebuilder_router

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError(
            "Missing required env var BOT_TOKEN. "
            "On Railway: Service → Variables → add BOT_TOKEN (your Telegram bot token)."
        )
    
    # Initialize Database
    init_db()

    # Initialize Bot and Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Set bot commands for shortcuts (visible to all users)
    commands = [
        BotCommand(command="start", description="Home Menu"),
        BotCommand(command="create", description="Choose Template"),
        BotCommand(command="help", description="Help & Support"),
    ]
    await bot.set_my_commands(commands)

    # Admin-only commands — only visible in the admin's private chat
    try:
        admin_id = int(os.getenv("ADMIN_ID", "0"))
    except ValueError:
        admin_id = 0
    if admin_id:
        admin_commands = commands + [
            BotCommand(command="admin", description="🛡️ Admin Panel"),
        ]
        try:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            print(f"Could not set admin commands: {e}")

    # Include routers
    dp.include_router(start_router)
    dp.include_router(payment_router)

    dp.include_router(admin_router)
    dp.include_router(memebuilder_router)

    # Start polling
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
