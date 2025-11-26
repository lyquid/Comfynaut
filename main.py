# 🧙‍♂️⚓ main.py - Comfynaut Project ⚔️🪐
# ---------------------------------------------------------------------------
# "All we have to decide is what to do with the prompts that are given to us."
#                                   —Gandalfrond the Whitebeard, 2025
#
# This is the main entry point for the Comfynaut project.
# It launches both the FastAPI server and the Telegram bot in separate processes.
# The API server handles image generation requests, while the Telegram bot interacts with users.
#
# The code below ensures both services run independently and can be stopped gracefully.
#
#                                                                ~ Gandalf 'n the Pirate-Ninjas Guild

import multiprocessing
import logging
import signal
import sys

# Configure logging for the main process
logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)
logger = logging.getLogger("comfynaut.main")

# Function to run the FastAPI server in a separate process
def run_api_server():
  """Run the FastAPI server in a separate process.
  This imports the FastAPI app from api_server.py and starts it using uvicorn.
  """
  import uvicorn
  from api_server import app, COMFYUI_API, COMFYUI_WS_URL, logger as api_logger
  api_logger.info("🏰 Comfynaut API Server starting...")
  api_logger.info("📡 ComfyUI connection: %s (WebSocket: %s)", COMFYUI_API, COMFYUI_WS_URL)
  api_logger.info("🌐 API server listening on http://0.0.0.0:8000/")
  uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# Function to run the Telegram bot in a separate process
def run_telegram_bot():
  """Run the Telegram bot in a separate process.
  This imports the bot logic from telegram_bot.py and sets up command handlers.
  """
  import telegram_bot
  from telegram import Update
  from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
  
  logging.info("🦜 Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(telegram_bot.TELEGRAM_TOKEN).build()
  # Register command handlers for bot commands
  app.add_handler(CommandHandler("start", telegram_bot.start))
  app.add_handler(CommandHandler("dream", telegram_bot.dream))
  app.add_handler(CommandHandler("workflows", telegram_bot.workflows))
  app.add_handler(CommandHandler("img2img", telegram_bot.img2img))
  app.add_handler(CommandHandler("img2vid", telegram_bot.img2vid))
  # Handler for photos with /img2img as caption
  app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/img2img'), telegram_bot.img2img))
  # Handler for photos with /img2vid as caption
  app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/img2vid'), telegram_bot.img2vid))
  # Handler for standalone photos (without /img2img or /img2vid caption)
  app.add_handler(MessageHandler(filters.PHOTO & ~filters.CaptionRegex(r'^/img2img') & ~filters.CaptionRegex(r'^/img2vid'), telegram_bot.handle_photo))
  app.add_handler(CallbackQueryHandler(telegram_bot.button))
  logging.info("🎩🦜 Comfynaut Telegram Parrot listening for orders!")
  app.run_polling()

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
  """Handle shutdown signals gracefully.
  This function is called when a termination signal is received (e.g., Ctrl+C).
  It logs the shutdown and exits the program.
  """
  logger.info("🛑 Shutdown signal received. Stopping Comfynaut...")
  sys.exit(0)

if __name__ == "__main__":
  # Print a launch banner for the user
  print("""
  ⚓🧙‍♂️ COMFYNAUT LAUNCHING! 🧙‍♂️⚓
  ══════════════════════════════════════
  "All we have to decide is what to do 
   with the prompts that are given to us."
  ══════════════════════════════════════
  """)
  
  # Register signal handlers for graceful shutdown (Ctrl+C, SIGTERM)
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  
  # Create separate processes for the API server and Telegram bot
  api_process = multiprocessing.Process(target=run_api_server, name="api_server")
  bot_process = multiprocessing.Process(target=run_telegram_bot, name="telegram_bot")
  
  try:
    # Start both services
    logger.info("🚀 Starting API Server...")
    api_process.start()
    
    logger.info("🦜 Starting Telegram Bot...")
    bot_process.start()
    
    logger.info("✨ Comfynaut is fully operational! Press Ctrl+C to stop.")
    
    # Wait for both processes to finish (blocks until both exit)
    api_process.join()
    bot_process.join()
    
  except KeyboardInterrupt:
    # Handle manual interruption (Ctrl+C)
    logger.info("🛑 Shutting down Comfynaut...")
    api_process.terminate()
    bot_process.terminate()
    api_process.join()
    bot_process.join()
    logger.info("👋 Comfynaut has stopped. Safe travels, captain!")

