import os
import sys
import asyncio

# 1. Ensure the current working directory is correct
base_dir = os.path.dirname(os.path.abspath(__file__))
if not base_dir:
    base_dir = os.getcwd()

bot_dir = os.path.join(base_dir, 'bot')

# 2. Add the base directory to sys.path
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 3. Add 'bot' directory to sys.path
if bot_dir not in sys.path:
    sys.path.insert(0, bot_dir)

# Ensure the 'bot' directory actually exists
if not os.path.exists(bot_dir):
    print(f"CRITICAL ERROR: 'bot' directory not found at {bot_dir}")
    print(f"Current directory contents: {os.listdir(base_dir)}")
    sys.exit(1)

if __name__ == "__main__":
    print(f"Launching bot from: {bot_dir}/main.py")
    try:
        # Import as 'main' from the 'bot' folder which is now in sys.path
        import main as bot_main
        asyncio.run(bot_main.main())
    except Exception as e:
        print(f"Failed to start the bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
