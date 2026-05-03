import os
import sys
import asyncio
import importlib.util

# 1. Define the absolute path to the actual bot entry point
base_dir = os.path.dirname(os.path.abspath(__file__))
# Support both local execution and Railway (where /app might be the root)
bot_main_path = os.path.join(base_dir, 'bot', 'main.py')
if not os.path.exists(bot_main_path):
    print(f"Warning: {bot_main_path} not found. Checking current directory...")
    bot_main_path = os.path.join(os.getcwd(), 'bot', 'main.py')
    base_dir = os.getcwd()

bot_dir = os.path.join(base_dir, 'bot')

# 2. Add 'bot' directory to sys.path so its internal imports work
# (e.g. 'from database.db import ...' inside bot/main.py)
if bot_dir not in sys.path:
    sys.path.insert(0, bot_dir)

def load_bot_module():
    if not os.path.exists(bot_main_path):
        print(f"CRITICAL ERROR: Could not find bot main file at {bot_main_path}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir(os.getcwd())}")
        if os.path.exists(os.path.join(os.getcwd(), 'bot')):
            print(f"Bot directory contents: {os.listdir(os.path.join(os.getcwd(), 'bot'))}")
        sys.exit(1)

    # Explicitly load the module from the file path to avoid naming collisions
    spec = importlib.util.spec_from_file_location("bot_entry", bot_main_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

if __name__ == "__main__":
    print(f"Launching bot from: {bot_main_path}")
    bot_module = load_bot_module()
    
    # Run the main function
    if hasattr(bot_module, 'main'):
        asyncio.run(bot_module.main())
    else:
        print("Error: Could not find 'main' function in bot/main.py")
        sys.exit(1)
