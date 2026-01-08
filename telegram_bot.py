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
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from io import BytesIO
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_SERVER = os.getenv("COMFY_API_HOST")

# Timeout constants for API requests (in seconds)
IMG2IMG_TIMEOUT = 120.0  # 2 minutes for image-to-image generation
IMG2VID_TIMEOUT = 900.0  # 15 minutes for video generation

# Telegram caption length limit
# The Telegram Bot API enforces a maximum of 1024 characters for photo and video captions
MAX_CAPTION_LENGTH = 1024

# Configure logging for the bot
logging.basicConfig(
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  level=logging.INFO
)

logging.info("Parrot-bot awakens and flaps its wings...")

# Utility: Truncate caption to fit Telegram's 1024 character limit
def truncate_caption(caption: str, max_length: int = MAX_CAPTION_LENGTH) -> str:
  """Truncate caption to fit within Telegram's character limit.
  
  If the caption exceeds the maximum length, it will be truncated and
  an ellipsis (...) will be added at the end to indicate truncation.
  
  Args:
    caption: The caption text to truncate
    max_length: Maximum allowed length (default: 1024 for Telegram)
    
  Returns:
    Truncated caption string that fits within the limit
  """
  if len(caption) <= max_length:
    return caption
  
  # Reserve space for ellipsis
  ellipsis = "..."
  truncated_length = max_length - len(ellipsis)
  
  return caption[:truncated_length] + ellipsis

# Utility: Replace localhost with actual API server hostname for Telegram delivery
def make_url_visible(url: str) -> str:
  """Replace localhost in URL with actual API server hostname for Telegram delivery."""
  parsed_api = urlparse(API_SERVER)
  if parsed_api.hostname:
    return url.replace("127.0.0.1", parsed_api.hostname)
  return url

# Dynamically load available workflows from the workflows directory
def load_workflows():
  """Dynamically load workflows from the workflows directory.
  Returns a dictionary mapping display names to workflow filenames,
  sorted alphabetically by display name.
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
  # Sort workflows alphabetically by display name
  return dict(sorted(workflows.items()))

WORKFLOWS = load_workflows()

# Handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /start command from user: %s", update.effective_user.username)
  await update.message.reply_text(
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐\n\n" +
    "🎨 Use /dream to create a single image\n" +
    "🎠 Use /marathon to start an endless auto-generation carousel\n" +
    "🛑 Use /stop to halt the marathon\n" +
    "🧙 Use /workflows to choose your favorite wizard spell style"
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
          image_url_visible = make_url_visible(image_url)
          
          # Download the generated image
          img_resp = await client.get(image_url_visible)
          img_resp.raise_for_status()
          
          img_bytes = BytesIO(img_resp.content)
          img_bytes.name = "comfynaut_image.png"
          caption = f"{msg}\n(Prompt: {prompt})\n(Workflow: {workflow_file})"
          # Truncate caption to fit Telegram's 1024 character limit
          caption = truncate_caption(caption)
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

# Utility: Generate a single image (used by both /dream and /marathon)
async def generate_single_image(chat_id, bot, prompt: str, workflow_file: str, username: str = None):
  """Generate a single image and send it to the chat.
  
  Args:
    chat_id: The Telegram chat ID to send the image to
    bot: The bot instance to use for sending
    prompt: The prompt to generate image from
    workflow_file: The workflow file to use
    username: Username for logging purposes
    
  Returns:
    True if successful, False otherwise
  """
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
          image_url_visible = make_url_visible(image_url)
          
          # Download the generated image
          img_resp = await client.get(image_url_visible)
          img_resp.raise_for_status()
          
          img_bytes = BytesIO(img_resp.content)
          img_bytes.name = "comfynaut_image.png"
          caption = f"{msg}\n(Prompt: {prompt})\n(Workflow: {workflow_file})"
          # Truncate caption to fit Telegram's 1024 character limit
          caption = truncate_caption(caption)
          # Send the image to the user
          await bot.send_photo(chat_id=chat_id, photo=img_bytes, caption=caption)
          logging.info("Sent image to user %s!", username)
          return True
        except Exception as img_err:
          logging.error("Error downloading or sending image for user %s: %s", username, img_err)
          await bot.send_message(chat_id=chat_id, text=f"🏰 Wizard's castle: {msg}\nEcho: {echo}\nBut alas, the art could not be delivered: {img_err}")
          return False
      else:
        # No image to send, reply with message and echo
        await bot.send_message(chat_id=chat_id, text=f"🏰 Wizard's castle: {msg}\nEcho: {echo}")
        logging.warning("No image to send for user: %s", username)
        return False

  except httpx.RequestError as e:
    # Handle network errors when contacting the API server
    logging.error("Request error while generating image for user %s: %s", username, e)
    await bot.send_message(chat_id=chat_id, text=f"⚠️ Unable to reach the wizard's castle: {e}")
    return False
  except Exception as e:
    # Handle unexpected errors
    logging.error("Unexpected error while generating image for user %s: %s", username, e)
    await bot.send_message(chat_id=chat_id, text=f"⚠️ An unexpected error occurred: {e}")
    return False

# Handler for the /marathon command - endless auto-generation carousel
async def marathon(update: Update, context: ContextTypes.DEFAULT_TYPE):
  prompt = " ".join(context.args)
  logging.info("Received /marathon command with prompt: '%s' from user: %s", prompt, update.effective_user.username)

  if not prompt:
    logging.warning("No prompt provided by user: %s", update.effective_user.username)
    await update.message.reply_text(
      "🎠 **Image Marathon Mode** 🎠\n\n"
      "Start an endless auto-generation carousel! Images keep coming with new seeds until you say STOP!\n\n"
      "Usage: `/marathon <prompt>`\n\n"
      "Example: `/marathon a majestic dragon in various poses`\n\n"
      "To stop: Use `/stop` command",
      parse_mode="Markdown"
    )
    return

  # Stop any existing marathon for this user
  if context.user_data.get("marathon_active"):
    context.user_data["marathon_active"] = False
    await asyncio.sleep(1)  # Give time for the previous marathon to stop

  # Retrieve the user's selected workflow or use default
  workflow_file = context.user_data.get("selected_workflow")
  if not workflow_file:
    workflow_file = list(WORKFLOWS.values())[0]
    context.user_data["selected_workflow"] = workflow_file
  
  logging.info("Starting marathon with workflow file: %s", workflow_file)

  # Set marathon state
  context.user_data["marathon_active"] = True
  context.user_data["marathon_prompt"] = prompt
  context.user_data["marathon_workflow"] = workflow_file
  context.user_data["marathon_count"] = 0

  await update.message.reply_text(
    f"🎠 **MARATHON MODE ACTIVATED!** 🎠\n\n"
    f"🦜 Setting sail on an endless image-generating voyage!\n"
    f"📜 Prompt: {prompt}\n"
    f"🧙 Workflow: `{workflow_file}`\n\n"
    f"Images will keep flowing with new seeds until you use `/stop`\n"
    f"⚡ The winds are favorable, Captain! Let the carousel begin!",
    parse_mode="Markdown"
  )

  # Start the generation loop
  chat_id = update.effective_chat.id
  username = update.effective_user.username
  
  while context.user_data.get("marathon_active", False):
    # Increment counter
    context.user_data["marathon_count"] = context.user_data.get("marathon_count", 0) + 1
    count = context.user_data["marathon_count"]
    
    logging.info("Marathon generation #%d for user %s", count, username)
    
    # Show typing action to indicate image is being prepared
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_PHOTO)
    
    # Send a progress message every 5 images
    if count % 5 == 1 and count > 1:
      await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎨 Marathon Progress: Generated {count-1} images so far! The dice keep rolling... 🎲"
      )
    
    # Generate the image
    success = await generate_single_image(
      chat_id=chat_id,
      bot=context.bot,
      prompt=prompt,
      workflow_file=workflow_file,
      username=username
    )
    
    if not success:
      # If generation failed, stop the marathon
      logging.warning("Marathon generation failed for user %s, stopping marathon", username)
      context.user_data["marathon_active"] = False
      await context.bot.send_message(
        chat_id=chat_id,
        text="⚠️ Marathon stopped due to generation error. Use `/marathon` to start again!",
        parse_mode="Markdown"
      )
      break
    
    # Small delay between generations to avoid overwhelming the system
    await asyncio.sleep(2)
  
  # Marathon stopped
  final_count = context.user_data.get("marathon_count", 0)
  # Only send completion message if the marathon wasn't stopped by the /stop command
  # (the /stop command sends its own message)
  if not context.user_data.get("marathon_stopped_by_command", False):
    logging.info("Marathon naturally ended for user %s after %d images", username, final_count)
    await context.bot.send_message(
      chat_id=chat_id,
      text=f"🏁 **MARATHON COMPLETE!** 🏁\n\n"
           f"Generated {final_count} unique images with your prompt!\n"
           f"May the seeds ever be in your favor! 🎲✨",
      parse_mode="Markdown"
    )
  
  # Clean up the flag
  context.user_data.pop("marathon_stopped_by_command", None)

# Handler for the /stop command - stops the marathon
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /stop command from user: %s", update.effective_user.username)
  
  if context.user_data.get("marathon_active"):
    context.user_data["marathon_active"] = False
    context.user_data["marathon_stopped_by_command"] = True
    count = context.user_data.get("marathon_count", 0)
    await update.message.reply_text(
      f"🛑 **STOP!** You shall not pass... any further! 🧙‍♂️\n\n"
      f"Marathon stopped after {count} images.\n"
      f"Use `/marathon <prompt>` to start a new voyage!",
      parse_mode="Markdown"
    )
  else:
    await update.message.reply_text(
      "🤔 No marathon is currently running.\n"
      "Use `/marathon <prompt>` to start one!",
      parse_mode="Markdown"
    )

# Handler for the /img2vid command
async def img2vid(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /img2vid command from user: %s", update.effective_user.username)
  
  # Get prompt from command arguments or caption
  prompt = ""
  if context.args:
    prompt = " ".join(context.args)
  elif update.message.caption:
    # Remove the /img2vid command from caption to get the prompt
    caption = update.message.caption.strip()
    if caption.startswith("/img2vid"):
      prompt = caption[len("/img2vid"):].strip()
  
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
      "1. Reply to an image with /img2vid <prompt>, or\n"
      "2. Send an image with /img2vid <prompt> as the caption\n\n"
      "Example: /img2vid the person walks forward slowly"
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
    
    prompt_info = f"\nPrompt: {prompt}" if prompt else ""
    await update.message.reply_text(
      f"🦜 Taking yer image to the GPU wizard's castle for video magic...{prompt_info}\n"
      "⏳ Video generation takes several minutes, please be patient!"
    )
    
    # Show typing action to indicate video is being prepared
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_VIDEO)
    
    # Send to backend API server with extended timeout for video generation
    payload = {"image_data": image_data, "prompt": prompt}
    logging.info("Sending img2vid request to API server with prompt: '%s'", prompt)
    
    async with httpx.AsyncClient(timeout=IMG2VID_TIMEOUT) as client:
      resp = await client.post(f"{API_SERVER}/img2vid", json=payload)
      resp.raise_for_status()
      data = resp.json()
      
      msg = data.get("message", "Hmmm, the castle gate is silent...")
      video_url = data.get("video_url")
      last_frame_url = data.get("last_frame_url")
      status = data.get("status")

      if status == "success" and video_url:
        try:
          # Replace localhost in video URL with actual API server hostname for Telegram delivery
          video_url_visible = make_url_visible(video_url)
          
          # Download the generated video
          vid_resp = await client.get(video_url_visible)
          vid_resp.raise_for_status()
          
          vid_bytes = BytesIO(vid_resp.content)
          vid_bytes.name = "comfynaut_video.mp4"
          # Build caption with optional prompt
          caption = msg
          if prompt:
            caption = f"{msg}\n(Prompt: {prompt})"
          # Truncate caption to fit Telegram's 1024 character limit
          caption = truncate_caption(caption)
          # Send the video to the user
          await update.message.reply_video(video=vid_bytes, caption=caption)
          logging.info("Sent video to user %s!", update.effective_user.username)
          
          # Send the last frame image if available (allows continuing with the video)
          if last_frame_url:
            try:
              last_frame_url_visible = make_url_visible(last_frame_url)
              
              # Download the last frame image
              frame_resp = await client.get(last_frame_url_visible)
              frame_resp.raise_for_status()
              
              frame_bytes = BytesIO(frame_resp.content)
              frame_bytes.name = "comfynaut_lastframe.png"
              # Send the last frame image to the user
              last_frame_caption = "🖼️ Last frame of your video - use this to continue the story with /img2vid!"
              await update.message.reply_photo(
                photo=frame_bytes, 
                caption=truncate_caption(last_frame_caption)
              )
              logging.info("Sent last frame to user %s!", update.effective_user.username)
            except Exception as frame_err:
              logging.error("Error downloading or sending last frame for user %s: %s", update.effective_user.username, frame_err)
              # Don't fail the whole operation if just the last frame fails
              
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

# Handler for the /img2img command
async def img2img(update: Update, context: ContextTypes.DEFAULT_TYPE):
  logging.info("Received /img2img command from user: %s", update.effective_user.username)
  
  # Get prompt from command arguments or caption
  prompt = ""
  if context.args:
    prompt = " ".join(context.args)
  elif update.message.caption:
    # Remove the /img2img command from caption to get the prompt
    caption = update.message.caption
    if caption.startswith("/img2img"):
      prompt = caption[len("/img2img"):].strip()
  
  # Check if the message is a reply to a photo or contains a photo
  photo = None
  if update.message.reply_to_message and update.message.reply_to_message.photo:
    # User replied to a message containing a photo
    photo = update.message.reply_to_message.photo[-1]  # Get highest quality photo
  elif update.message.photo:
    # User sent a photo with /img2img as caption
    photo = update.message.photo[-1]
  
  if not photo:
    await update.message.reply_text(
      "🎨 To transform an image, please:\n"
      "1. Reply to an image with /img2img <prompt>, or\n"
      "2. Send an image with /img2img <prompt> as the caption\n\n"
      "Example: /img2img make it look like a painting"
    )
    return
  
  if not prompt:
    await update.message.reply_text(
      "⚡ Please include a prompt describing the transformation!\n"
      "Example: /img2img make it look like a watercolor painting"
    )
    return
  
  await update.message.reply_text("🎨 Preparing your image for transformation...")
  
  try:
    # Download the photo from Telegram
    photo_file = await context.bot.get_file(photo.file_id)
    photo_bytes = BytesIO()
    await photo_file.download_to_memory(photo_bytes)
    photo_bytes.seek(0)
    
    # Encode the image as base64
    image_data = base64.b64encode(photo_bytes.read()).decode('utf-8')
    
    await update.message.reply_text(
      f"🦜 Taking yer image to the GPU wizard's castle...\n"
      f"Transformation prompt: {prompt}"
    )
    
    # Show typing action to indicate image is being prepared
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.UPLOAD_PHOTO)
    
    # Send to backend API server
    payload = {"prompt": prompt, "image_data": image_data}
    logging.info("Sending img2img request to API server with prompt: '%s'", prompt)
    
    async with httpx.AsyncClient(timeout=IMG2IMG_TIMEOUT) as client:
      resp = await client.post(f"{API_SERVER}/img2img", json=payload)
      resp.raise_for_status()
      data = resp.json()
      
      msg = data.get("message", "Hmmm, the castle gate is silent...")
      image_url = data.get("image_url")
      status = data.get("status")

      if status == "success" and image_url:
        try:
          # Replace localhost in image URL with actual API server hostname for Telegram delivery
          image_url_visible = make_url_visible(image_url)
          
          # Download the generated image
          img_resp = await client.get(image_url_visible)
          img_resp.raise_for_status()
          
          img_bytes = BytesIO(img_resp.content)
          img_bytes.name = "comfynaut_img2img.png"
          caption = f"{msg}\n(Prompt: {prompt})"
          # Truncate caption to fit Telegram's 1024 character limit
          caption = truncate_caption(caption)
          # Send the image to the user
          await update.message.reply_photo(photo=img_bytes, caption=caption)
          logging.info("Sent img2img result to user %s!", update.effective_user.username)
        except Exception as img_err:
          logging.error("Error downloading or sending img2img image for user %s: %s", update.effective_user.username, img_err)
          await update.message.reply_text(f"🏰 Wizard's castle: {msg}\nBut alas, the art could not be delivered: {img_err}")
      else:
        # No image to send, reply with message
        await update.message.reply_text(f"🏰 Wizard's castle: {msg}")
        logging.warning("No img2img image to send for user: %s", update.effective_user.username)

  except httpx.RequestError as e:
    # Handle network errors when contacting the API server
    logging.error("Request error while processing /img2img command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ Unable to reach the wizard's castle: {e}")
  except Exception as e:
    # Handle unexpected errors
    logging.error("Unexpected error while processing /img2img command for user %s: %s", update.effective_user.username, e)
    await update.message.reply_text(f"⚠️ An unexpected error occurred: {e}")

# Handler for photos sent without /img2vid or /img2img caption
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Handle photos sent without command captions.
  
  Provides usage instructions for available image processing commands
  (/img2img and /img2vid).
  """
  logging.info("Received photo from user: %s", update.effective_user.username)
  await update.message.reply_text(
    "📸 Nice picture! Here's what you can do with it:\n\n"
    "🎨 **Transform the image:**\n"
    "• Reply to this image with /img2img <prompt>\n"
    "• Send another image with /img2img <prompt> as caption\n\n"
    "🎬 **Create a video:**\n"
    "• Reply to this image with /img2vid\n"
    "• Send another image with /img2vid as caption",
    parse_mode="Markdown"
  )

# Entry point for running the bot directly
if __name__ == '__main__':
  logging.info("Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  # Register command and callback handlers
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))
  app.add_handler(CommandHandler("marathon", marathon))
  app.add_handler(CommandHandler("stop", stop))
  app.add_handler(CommandHandler("img2img", img2img))
  app.add_handler(CommandHandler("img2vid", img2vid))
  app.add_handler(CommandHandler("workflows", workflows))
  app.add_handler(CallbackQueryHandler(button))
  # Handler for photos with /img2img as caption
  app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/img2img'), img2img))
  # Handler for photos with /img2vid as caption
  app.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex(r'^/img2vid'), img2vid))
  # Handler for standalone photos (without /img2img or /img2vid caption)
  app.add_handler(MessageHandler(filters.PHOTO & ~filters.CaptionRegex(r'^/img2img') & ~filters.CaptionRegex(r'^/img2vid'), handle_photo))
  logging.info("Bot is now polling for orders among the stars.")
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start, /dream, /marathon, /stop, /img2img, /img2vid, or /workflows")
  app.run_polling()