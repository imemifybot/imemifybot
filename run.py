import os
import sys
import asyncio

# 1. Define the absolute path to the actual bot entry point
base_dir = os.path.dirname(os.path.abspath(__file__))
bot_dir = os.path.join(base_dir, 'bot')

# 2. Add the base directory to sys.path so 'import bot.main' works
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 3. Add 'bot' directory to sys.path so internal bot imports work 
# (e.g. 'from database.db import ...' inside bot/main.py)
if bot_dir not in sys.path:
    sys.path.insert(0, bot_dir)

if __name__ == "__main__":
    print(f"Launching bot from: {bot_dir}/main.py")
    try:
        from bot.main import main
        asyncio.run(main())
    except Exception as e:
        print(f"Failed to start the bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
