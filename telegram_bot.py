# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# Now with a MAGIC WORKFLOWS MENU for epic ComfyUI style-switching!
# "The wise wizard speaks softly—his parrot yells in all caps...with BUTTONS!"
#    — Gandalf the Pirate, Keeper of the Parrot
#
# This file implements the Telegram bot for Comfynaut.
# It provides a chat interface for users to send prompts and receive generated images.
# Users can select different workflows (styles) for image generation using inline buttons.
# The bot communicates with the backend API server to process prompts and deliver results.

import os
import logging
import httpx
import glob
import base64
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from io import BytesIO
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_SERVER = os.getenv("COMFY_API_HOST")

# Configure logging for the bot
logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

logging.info("Parrot-bot awakens and flaps its wings...")

# Dynamically load available workflows from the workflows directory
def load_workflows():
  """Dynamically load workflows from the workflows directory.
  Returns a dictionary mapping display names to workflow filenames.
  """
  workflows = {}
  workflow_files = glob.glob("workflows/*.json")
  for wf_file in workflow_files:
    # Use filename as the display name, removing extension and formatting
    name = os.path.basename(wf_file).replace(".json", "").replace("_", " ").title()
    workflows[name] = os.path.basename(wf_file)
  
  if not workflows:
    logging.warning("No workflows found in workflows/ directory!")
    return {"Default": "default.json"}  # Fallback if no workflows found
  return workflows

WORKFLOWS = load_workflows()

# Handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /start command from user: %s", update.effective_user.username)
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐\n" +
    "Use /workflows to choose your favorite wizard spell style."
  )

# Handler for the /workflows command
async def workflows(update: Update, context: ContextTypes.DEFAULT_TYPE):
  # Reload workflows to catch any new files
  global WORKFLOWS
  WORKFLOWS = load_workflows()
  
  # Prepare an inline keyboard with workflow choices for the user
  keyboard = [
    [InlineKeyboardButton(wf_name, callback_data=f"workflow|{wf_file}")]
    for wf_name, wf_file in WORKFLOWS.items()
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)
  await update.message.reply_text(
    "🧙‍♂️ Choose your ComfyUI workflow, young hobbit:",
    reply_markup=reply_markup
  )

# Handler for button presses (inline keyboard)
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  data = query.data
  if data.startswith("workflow|"):
    # User selected a workflow; store it in user_data
    _, workflow_file = data.split("|", 1)
    context.user_data["selected_workflow"] = workflow_file
    await query.edit_message_text(
      f"✨ You've equipped: `{workflow_file}`!\n"
      "All your /dreams will use this workflow until you change again using /workflows.",
      parse_mode="Markdown"
    )

# Handler for the /dream command
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
  
  # Show typing action to indicate image is being prepared
  await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_PHOTO)

  try:
    # Send both prompt and workflow to backend API server
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
          # Replace localhost in image URL with actual API server hostname for Telegram delivery
          parsed_api = urlparse(API_SERVER)
          image_url_visible = image_url.replace("127.0.0.1", parsed_api.hostname)
          
          # Download the generated image
          img_resp = await client.get(image_url_visible)
          img_resp.raise_for_status()
          
          img_bytes = BytesIO(img_resp.content)
          img_bytes.name = "comfynaut_image.png"
          caption = f"{msg}\n(Prompt: {prompt})\n(Workflow: {workflow_file})"
          # Send the image to the user
          await update.message.reply_photo(photo=img_bytes, caption=caption)
          logging.info("Sent image to user %s!", update.effective_user.username)
        except Exception as img_err:
          logging.error("Error downloading or sending image for user %s: %s", update.effective_user.username, img_err)
          await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}\nBut alas, the art could not be delivered: {img_err}")
      else:
        # No image to send, reply with message and echo
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nEcho: {echo}")
        logging.warning("No image to send for user: %s", update.effective_user.username)

  except httpx.RequestError as e:
    # Handle network errors when contacting the API server
    logging.error("Request error while processing /dream command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    # Handle unexpected errors
    logging.error("Unexpected error while processing /dream command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

# Handler for the /img2vid command
async def img2vid(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /img2vid command from user: %s", update.effective_user.username)
  
  # Check if the message is a reply to a photo or contains a photo
  photo = None
  if update.message.reply_to_message and update.message.reply_to_message.photo:
    # User replied to a message containing a photo
    photo = update.message.reply_to_message.photo[-1]  # Get highest quality photo
  elif update.message.photo:
    # User sent a photo with /img2vid as caption
    photo = update.message.photo[-1]
  
  if not photo:
    await update.message.reply_text(
      "🎬 To create a video, please:\n"
      "1. Reply to an image with /img2vid, or\n"
      "2. Send an image with /img2vid as the caption"
    )
    return
  
  await update.message.reply_text("🎬 Preparing your image for video generation...")
  
  try:
    # Download the photo from Telegram
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)
    
    # Encode the image as base64
    image_data = base64.b64encode(photo_bytes.read()).decode('utf-8')
    
    await update.message.reply_text(
      "🦜 Taking yer image to the GPU wizard's castle for video magic...\n"
      "⏳ Video generation takes several minutes, please be patient!"
    )
    
    # Show typing action to indicate video is being prepared
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_VIDEO)
    
    # Send to backend API server with extended timeout for video generation
    payload = {"image_data": image_data}
    logging.info("Sending img2vid request to API server")
    
    async with httpx.AsyncClient(timeout=900.0) as client:  # 15 min timeout for video
      resp = await client.post(f"{API_SERVER}/img2vid", json=payload)
      resp.raise_for_status()
      data = resp.json()
      
      msg = data.get("message", "Hmmm, the castle gate is silent...")
      video_url = data.get("video_url")
      status = data.get("status")

      if status == "success" and video_url:
        try:
          # Replace localhost in video URL with actual API server hostname for Telegram delivery
          parsed_api = urlparse(API_SERVER)
          video_url_visible = video_url
          if parsed_api.hostname:
            video_url_visible = video_url.replace("127.0.0.1", parsed_api.hostname)
          
          # Download the generated video
          vid_resp = await client.get(video_url_visible)
          vid_resp.raise_for_status()
          
          vid_bytes = BytesIO(vid_resp.content)
          vid_bytes.name = "comfynaut_video.mp4"
          # Send the video to the user
          await update.message.reply_video(video=vid_bytes, caption=msg)
          logging.info("Sent video to user %s!", update.effective_user.username)
        except Exception as vid_err:
          logging.error("Error downloading or sending video for user %s: %s", update.effective_user.username, vid_err)
          await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nBut alas, the video could not be delivered: {vid_err}")
      else:
        # No video to send, reply with message
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}")
        logging.warning("No video to send for user: %s", update.effective_user.username)

  except httpx.RequestError as e:
    # Handle network errors when contacting the API server
    logging.error("Request error while processing /img2vid command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    # Handle unexpected errors
    logging.error("Unexpected error while processing /img2vid command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

# Entry point for running the bot directly
if __name__ == '__main__':
  logging.info("Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  # Register command and callback handlers
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))
  app.add_handler(CommandHandler("img2vid", img2vid))
  app.add_handler(CommandHandler("workflows", workflows))
  app.add_handler(CallbackQueryHandler(button))
  # Handler for photos with /img2vid as caption
  app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/img2vid'), img2vid))
  logging.info("Bot is now polling for orders among the stars.")
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start, /dream, /img2vid, or /workflows")
  app.run_polling()