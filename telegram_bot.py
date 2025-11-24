# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# ----------------------------------------------------------------
# "The wise wizard speaks softly—his parrot yells in all caps...with PICTURES!"
#    — Gandalf the Pirate, Keeper of the Parrot

import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from io import BytesIO
import base64

# Load thy sacred environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_SERVER = os.getenv("COMFY_API_HOST")  # Example: http://192.168.50.18:8000

logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

logging.info("Parrot-bot awakens and flaps its wings...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /start command from user: %s", update.effective_user.username)
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐\n\n"
    "Commands:\n"
    "• /dream <prompt> - Generate an image from text\n"
    "• Send a photo with a caption - Transform your image (img2img)"
  )

async def dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
  prompt = " ".join(context.args)
  logging.info("Received /dream command with prompt: '%s' from user: %s", prompt, update.effective_user.username)

  if not prompt:
    logging.warning("No prompt provided by user: %s", update.effective_user.username)
    await update.message.reply_text("⚡ Speak thy wishes: /dream <prompt>")
    return

  await update.message.reply_text("🦜 Taking yer dream to the GPU wizard's castle...")
  try:
    logging.info("Sending prompt to API server: %s", API_SERVER)
    resp = requests.post(f"{API_SERVER}/dream", json={"prompt": prompt}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    msg = data.get("message", "Hmmm, the castle gate is silent...")
    image_url = data.get("image_url")
    status = data.get("status")
    echo = data.get("echo")

    if status == "success" and image_url:
      try:
        # Yarrr: Always use the LAN IP for image delivery, not 127.0.0.1!
        image_url_visible = image_url.replace("127.0.0.1", API_SERVER.split("//")[1].split(":")[0])
        img_resp = requests.get(image_url_visible, timeout=60)
        img_resp.raise_for_status()
        img_bytes = BytesIO(img_resp.content)
        img_bytes.name = "comfynaut_image.png"
        caption = f"{msg}\n(Prompt: {prompt})"
        await update.message.reply_photo(photo=img_bytes, caption=caption)
        logging.info("Sent image to user %s!", update.effective_user.username)
      except Exception as img_err:
        logging.error("Error downloading or sending image for user %s: %s", update.effective_user.username, img_err)
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}\nBut alas, the art could not be delivered: {img_err}")
    else:
      await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}")
      logging.warning("No image to send for user: %s", update.effective_user.username)
  except requests.exceptions.RequestException as e:
    logging.error("Request error while processing /dream command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    logging.error("Unexpected error while processing /dream command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Handle photo messages with captions for img2img generation."""
  logging.info("Received photo from user: %s", update.effective_user.username)
  
  # Get the caption as the prompt
  prompt = update.message.caption or ""
  
  if not prompt:
    logging.warning("No caption provided with photo by user: %s", update.effective_user.username)
    await update.message.reply_text("⚡ Please include a caption with your image to describe the transformation!\nExample: 'change the color of the car to blue'")
    return
  
  logging.info("Photo caption (prompt): '%s'", prompt)
  await update.message.reply_text("🎨 Transforming your image with the wizard's magic...")
  
  try:
    # Get the largest photo
    photo = update.message.photo[-1]
    
    # Download the photo
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Encode to base64
    image_base64 = base64.b64encode(photo_bytes).decode('utf-8')
    
    # Send to API server
    logging.info("Sending img2img request to API server: %s", API_SERVER)
    resp = requests.post(
      f"{API_SERVER}/img2img",
      json={"prompt": prompt, "image_data": image_base64},
      timeout=90
    )
    resp.raise_for_status()
    data = resp.json()
    
    msg = data.get("message", "Hmmm, the castle gate is silent...")
    image_url = data.get("image_url")
    status = data.get("status")
    echo = data.get("echo")
    
    if status == "success" and image_url:
      try:
        # Yarrr: Always use the LAN IP for image delivery, not 127.0.0.1!
        image_url_visible = image_url.replace("127.0.0.1", API_SERVER.split("//")[1].split(":")[0])
        img_resp = requests.get(image_url_visible, timeout=60)
        img_resp.raise_for_status()
        img_bytes = BytesIO(img_resp.content)
        img_bytes.name = "comfynaut_img2img.png"
        caption = f"{msg}\n(Transformation: {prompt})"
        await update.message.reply_photo(photo=img_bytes, caption=caption)
        logging.info("Sent transformed image to user %s!", update.effective_user.username)
      except Exception as img_err:
        logging.error("Error downloading or sending image for user %s: %s", update.effective_user.username, img_err)
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}\nBut alas, the art could not be delivered: {img_err}")
    else:
      await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}")
      logging.warning("No image to send for user: %s", update.effective_user.username)
  
  except requests.exceptions.RequestException as e:
    logging.error("Request error while processing photo for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    logging.error("Unexpected error while processing photo for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

if __name__ == '__main__':
  logging.info("Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))
  app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
  logging.info("Bot is now polling for orders among the stars.")
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start or /dream")
  print("📸 Now with img2img support! Send a photo with a caption to transform it.")
  app.run_polling()