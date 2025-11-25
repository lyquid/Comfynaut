# 🧙‍♂️⚓ main.py - Comfynaut Project ⚔️🪐
# ---------------------------------------------------------------------------
# "All we have to decide is what to do with the prompts that are given to us."
#                                   —Gandalfrond the Whitebeard, 2025
#
# Here be the main entry to your teleporting promptship, captain!
# This is where Telegram messages dock, and GPU-powered image loot sets sail.
# Use with honor, cunning, and a GPU fit for a wizard or ninja.
#
# // Insert coins to continue. May your imports be DRY and your bugs be few.
#
#                                                                ~ Gandalf 'n the Pirate-Ninjas Guild

import multiprocessing
import logging
import signal
import sys

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)
logger = logging.getLogger("comfynaut.main")

def run_api_server():
  """Run the FastAPI server in a separate process."""
  import uvicorn
  from api_server import app, COMFYUI_API, COMFYUI_WS_URL, logger as api_logger
  api_logger.info("🏰 Comfynaut API Server starting...")
  api_logger.info("📡 ComfyUI connection: %s (WebSocket: %s)", COMFYUI_API, COMFYUI_WS_URL)
  api_logger.info("🌐 API server listening on http://0.0.0.0:8000/")
  uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

def run_telegram_bot():
  """Run the Telegram bot in a separate process."""
  import telegram_bot
  from telegram import Update
  from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
  
  logging.info("🦜 Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(telegram_bot.TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", telegram_bot.start))
  app.add_handler(CommandHandler("dream", telegram_bot.dream))
  app.add_handler(CommandHandler("workflows", telegram_bot.workflows))
  app.add_handler(CommandHandler("img2vid", telegram_bot.img2vid))
  app.add_handler(MessageHandler(filters.PHOTO, telegram_bot.handle_photo))
  app.add_handler(CallbackQueryHandler(telegram_bot.button))
  logging.info("🎩🦜 Comfynaut Telegram Parrot listening for orders!")
  app.run_polling()

def signal_handler(signum, frame):
  """Handle shutdown signals gracefully."""
  logger.info("🛑 Shutdown signal received. Stopping Comfynaut...")
  sys.exit(0)

if __name__ == "__main__":
  print("""
  ⚓🧙‍♂️ COMFYNAUT LAUNCHING! 🧙‍♂️⚓
  ══════════════════════════════════════
  "All we have to decide is what to do 
   with the prompts that are given to us."
  ══════════════════════════════════════
  """)
  
  # Handle Ctrl+C gracefully
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  
  # Create processes for both services
  api_process = multiprocessing.Process(target=run_api_server, name="api_server")
  bot_process = multiprocessing.Process(target=run_telegram_bot, name="telegram_bot")
  
  try:
    # Start both processes
    logger.info("🚀 Starting API Server...")
    api_process.start()
    
    logger.info("🦜 Starting Telegram Bot...")
    bot_process.start()
    
    logger.info("✨ Comfynaut is fully operational! Press Ctrl+C to stop.")
    
    # Wait for both processes
    api_process.join()
    bot_process.join()
    
  except KeyboardInterrupt:
    logger.info("🛑 Shutting down Comfynaut...")
    api_process.terminate()
    bot_process.terminate()
    api_process.join()
    bot_process.join()
    logger.info("👋 Comfynaut has stopped. Safe travels, captain!")

