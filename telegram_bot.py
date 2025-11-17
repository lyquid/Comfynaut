# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# ----------------------------------------------------------------
# "The wise wizard speaks softly—his parrot yells in all caps."
#    — Gandalf the Discordant, after too much Red Bull

import os
from dotenv import load_dotenv
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Pop yer Telegram Bot Token here, ye scurvy dog!
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  level=logging.INFO
)

# When you send "/start" to the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐"
  )

# When you send "/dream <your prompt>" to the bot
async def dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
  prompt = " ".join(context.args)
  if not prompt:
    await update.message.reply_text("⚡ Speak thy wishes: /dream <prompt>")
    return
  # Here’s where we’ll forward the prompt to your GPU-wizard machine later!
  await update.message.reply_text(
    f"🧙‍♂️ Received: \"{prompt}\"\nHold fast, Captain! Art summoning soon."
  )

if __name__ == '__main__':
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))

  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start or /dream")
  app.run_polling()