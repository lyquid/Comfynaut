# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# Now with a MAGIC WORKFLOWS MENU for epic ComfyUI style-switching!
# "The wise wizard speaks softly—his parrot yells in all caps...with BUTTONS!"
#    — Gandalf the Pirate, Keeper of the Parrot

import os
import logging
import httpx
import glob
from dotenv import load_dotenv
from io import BytesIO
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from urllib.parse import urljoin, urlparse

# Load thy sacred environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_SERVER = os.getenv("COMFY_API_HOST")  # Example: http://192.168.50.18:8000


logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

logging.info("Parrot-bot awakens and flaps its wings...")

def load_workflows():
  """Dynamically load workflows from the workflows directory."""
  workflows = {}
  workflow_files = glob.glob("workflows/*.json")
  for wf_file in workflow_files:
    # Use filename as the display name, removing extension
    name = os.path.basename(wf_file).replace(".json", "").replace("_", " ").title()
    workflows[name] = os.path.basename(wf_file)

  if not workflows:
    logging.warning("No workflows found in workflows/ directory!")
    return {"Default": "default.json"}  # Fallback
  return workflows

WORKFLOWS = load_workflows()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /start command from user: %s", update.effective_user.username)
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐\n\n"
    "Commands:\n"
    "• /workflows - Choose your favorite wizard spell style\n"
    "• /dream <prompt> - Generate an image from text\n"
    "• /img2vid - Convert a photo to video (reply to a photo)\n"
    "• Send a photo with a caption - Transform your image (img2img)\n\n"
    "⚠️ Note: Video generation can take 10+ minutes!"
  )

async def workflows(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Reload workflows to catch any new files
  global WORKFLOWS
  WORKFLOWS = load_workflows()

  # Prepare an inline keyboard with fancy workflow choices
  keyboard = [
    [InlineKeyboardButton(wf_name, callback_data=f"workflow|{wf_file}")]
    for wf_name, wf_file in WORKFLOWS.items()
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text(
    "🧙‍♂️ Choose your ComfyUI workflow, young hobbit:",
    reply_markup=reply_markup
  )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data
  if data.startswith("workflow|"):
    _, workflow_file = data.split("|", 1)
    context.user_data["selected_workflow"] = workflow_file
    await query.edit_message_text(
      f"✨ You've equipped: `{workflow_file}`!\n"
      "All your /dreams will use this workflow until you change again using /workflows.",
      parse_mode="Markdown"
    )

async def dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
  prompt = " ".join(context.args)
  logging.info("Received /dream command with prompt: '%s' from user: %s", prompt, update.effective_user.username)

  # Retrieve the user's selected workflow or use default (first available)
  workflow_file = context.user_data.get("selected_workflow")
  if not workflow_file:
    workflow_file = list(WORKFLOWS.values())[0]
    context.user_data["selected_workflow"] = workflow_file

  logging.info("Using workflow file: %s", workflow_file)

  if not prompt:
    logging.warning("No prompt provided by user: %s", update.effective_user.username)
    await update.message.reply_text("⚡ Speak thy wishes: /dream <prompt>")
    return

  await update.message.reply_text(
    f"🦜 Taking yer dream to the GPU wizard's castle using `{workflow_file}`..."
  )

  # Show typing action
  await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_PHOTO)

  try:
    # Send both prompt and workflow to backend
    payload = {"prompt": prompt, "workflow": workflow_file}
    logging.info("Sending payload to API server: %s", payload)

    async with httpx.AsyncClient(timeout=60.0) as client:
      resp = await client.post(f"{API_SERVER}/dream", json=payload)
      resp.raise_for_status()
      data = resp.json()

      msg = data.get("message", "Hmmm, the castle gate is silent...")
      image_url = data.get("image_url")
      status = data.get("status")
      echo = data.get("echo")

      if status == "success" and image_url:
        try:
          # Fix URL if it's localhost
          parsed_api = urlparse(API_SERVER)
          image_url_visible = image_url.replace("127.0.0.1", parsed_api.hostname)

          img_resp = await client.get(image_url_visible)
          img_resp.raise_for_status()

          img_bytes = BytesIO(img_resp.content)
          img_bytes.name = "comfynaut_image.png"
          caption = f"{msg}\n(Prompt: {prompt})\n(Workflow: {workflow_file})"
          await update.message.reply_photo(photo=img_bytes, caption=caption)
          logging.info("Sent image to user %s!", update.effective_user.username)
        except Exception as img_err:
          logging.error("Error downloading or sending image for user %s: %s", update.effective_user.username, img_err)
          await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}\nBut alas, the art could not be delivered: {img_err}")
      else:
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}")
        logging.warning("No image to send for user: %s", update.effective_user.username)

  except httpx.RequestError as e:
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
    async with httpx.AsyncClient(timeout=90.0) as client:
      resp = await client.post(
        f"{API_SERVER}/img2img",
        json={"prompt": prompt, "image_data": image_base64}
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
          img_resp = await client.get(image_url_visible, timeout=60)
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
  
  except httpx.RequestError as e:
    logging.error("Request error while processing photo for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    logging.error("Unexpected error while processing photo for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

async def img2vid(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Handle /img2vid command - convert an image to video using WAN i2v.
  
  User should reply to a photo with /img2vid command.
  """
  logging.info("Received /img2vid command from user: %s", update.effective_user.username)
  
  # Check if this is a reply to a photo
  reply_message = update.message.reply_to_message
  if not reply_message or not reply_message.photo:
    await update.message.reply_text(
      "⚡ To create a video, reply to a photo with /img2vid\n\n"
      "⚠️ Video generation takes 10+ minutes!"
    )
    return
  
  await update.message.reply_text(
    "🎬 Converting image to video...\n\n"
    "⏳ This may take 10+ minutes. Please be patient!"
  )
  
  try:
    # Get the largest photo from the replied message
    photo = reply_message.photo[-1]
    
    # Download the photo
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Encode to base64
    image_base64 = base64.b64encode(photo_bytes).decode('utf-8')
    
    # Send to API server with extended timeout (15 minutes)
    logging.info("Sending img2vid request to API server: %s", API_SERVER)
    
    # Use extended timeout for video generation (15 minutes)
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=900.0)) as client:
      resp = await client.post(
        f"{API_SERVER}/img2vid",
        json={"image_data": image_base64}
      )
      resp.raise_for_status()
      data = resp.json()
    
      msg = data.get("message", "Hmmm, the castle gate is silent...")
      video_url = data.get("video_url")
      status = data.get("status")
    
      if status == "success" and video_url:
        try:
          # Fix URL if it's localhost
          parsed_api = urlparse(API_SERVER)
          video_url_visible = video_url.replace("127.0.0.1", parsed_api.hostname)
          
          vid_resp = await client.get(video_url_visible, timeout=300)
          vid_resp.raise_for_status()
          
          vid_bytes = BytesIO(vid_resp.content)
          vid_bytes.name = "comfynaut_video.mp4"
          
          caption = f"🎬 {msg}"
          await update.message.reply_video(video=vid_bytes, caption=caption)
          logging.info("Sent video to user %s!", update.effective_user.username)
        except Exception as vid_err:
          logging.error("Error downloading or sending video for user %s: %s", update.effective_user.username, vid_err)
          await update.message.reply_text(
            f"🏰 Wizard's castle: {msg}\n"
            f"But alas, the video could not be delivered: {vid_err}\n"
            f"Video URL: {video_url_visible}"
          )
      else:
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}")
        logging.warning("No video to send for user: %s", update.effective_user.username)
  
  except httpx.TimeoutException:
    logging.error("Timeout while processing img2vid for user %s", update.effective_user.username)
    await update.message.reply_text(
      "⏰ The video generation is taking too long.\n"
      "The wizard's castle might still be working on it. Try again later?"
    )
  except httpx.RequestError as e:
    logging.error("Request error while processing img2vid for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    logging.error("Unexpected error while processing img2vid for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

if __name__ == '__main__':
  logging.info("Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))
  app.add_handler(CommandHandler("workflows", workflows))
  app.add_handler(CommandHandler("img2vid", img2vid))
  app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
  app.add_handler(CallbackQueryHandler(button))
  logging.info("Bot is now polling for orders among the stars.")
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start, /dream, /workflows, or /img2vid")
  app.run_polling()