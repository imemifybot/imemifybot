import sys
import os
import traceback

sys.stdout = open("out.log", "w", encoding="utf-8")
sys.stderr = open("error.log", "w", encoding="utf-8")

try:
    print("Trying to import bot.main")
    # Add bot to sys.path
    bot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot')
    if bot_dir not in sys.path:
        sys.path.insert(0, bot_dir)
        
    import main
    print("Import successful!")
except Exception as e:
    print("Exception occurred:")
    traceback.print_exc()
