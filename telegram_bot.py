# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# ----------------------------------------------------------------
# "The wise wizard speaks softly—his parrot yells in all caps."
#    — Gandalf the Discordant, after too much Red Bull

# Import necessary libraries
import os  # For interacting with the operating system
import logging  # For logging messages
import requests  # For making HTTP requests
from dotenv import load_dotenv  # For loading environment variables from a .env file
from telegram import Update  # Telegram Update object for handling messages
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes  # Telegram bot framework

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Telegram bot token

# Define the API server endpoint
API_SERVER = os.getenv("COMFY_API_HOST")  # local GPU server

# Configure logging for debugging and monitoring
logging.basicConfig(
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  level=logging.INFO
)

# Log the initialization of the bot
logging.info("Telegram bot is starting up...")

# Define the /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """
  Handle the /start command to greet the user.
  Parameters:
    update (Update): The incoming Telegram update.
    context (ContextTypes.DEFAULT_TYPE): The context for the command.
  """
  logging.info("Received /start command from user: %s", update.effective_user.username)
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐"
  )

# Define the /dream command handler
async def dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """
  Handle the /dream command to send a prompt to the API server.
  Parameters:
    update (Update): The incoming Telegram update.
    context (ContextTypes.DEFAULT_TYPE): The context for the command, including arguments.
  """
  prompt = " ".join(context.args)  # Combine arguments into a single prompt string
  logging.info("Received /dream command with prompt: '%s' from user: %s", prompt, update.effective_user.username)

  if not prompt:
    logging.warning("No prompt provided by user: %s", update.effective_user.username)
    await update.message.reply_text("⚡ Speak thy wishes: /dream <prompt>")
    return

  await update.message.reply_text("🦜 Taking yer dream to the GPU wizard's castle...")
  try:
    resp = requests.post(f"{API_SERVER}/dream", json={"prompt": prompt}, timeout=10)  # Send prompt to API
    resp.raise_for_status()
    data = resp.json()  # Parse the JSON response
    msg = data.get("message", "Hmmm, the castle gate is silent...")  # Extract message from response
    logging.info("API response for user %s: %s", update.effective_user.username, msg)
    await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {data.get('echo')}")
  except Exception as e:
    logging.error("Error while processing /dream command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")

# Entry point for the bot
if __name__ == '__main__':
  """
  Initialize the Telegram bot and start polling for updates.
  """
  logging.info("Initializing the Telegram bot application...")
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()  # Build the bot application
  app.add_handler(CommandHandler("start", start))  # Add handler for /start command
  app.add_handler(CommandHandler("dream", dream))  # Add handler for /dream command
  logging.info("Bot is now polling for updates.")
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start or /dream")
  app.run_polling()  # Start polling for updates