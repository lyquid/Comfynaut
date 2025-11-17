# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# ----------------------------------------------------------------
# "The wise wizard speaks softly—his parrot yells in all caps."
#    — Gandalf the Discordant, after too much Red Bull

import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load secrets, shipmates!
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Replace with your GPU PC's IP address
API_SERVER = os.getenv("COMFY_API_HOST", "http://192.168.1.123:8000")  # Set your actual IP & port

logging.basicConfig(
  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
  level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐"
  )

async def dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
  prompt = " ".join(context.args)
  if not prompt:
    await update.message.reply_text("⚡ Speak thy wishes: /dream <prompt>")
    return

  await update.message.reply_text("🦜 Taking yer dream to the GPU wizard's castle...")
  try:
    resp = requests.post(f"{API_SERVER}/dream", json={"prompt": prompt}, timeout=10)
    data = resp.json()
    msg = data.get("message", "Hmmm, the castle gate is silent...")
    await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {data.get('echo')}")
  except Exception as e:
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")

if __name__ == '__main__':
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start or /dream")
  app.run_polling()