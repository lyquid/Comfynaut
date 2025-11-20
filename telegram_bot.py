# 🦜 telegram_bot.py - Comfynaut Parrot Listener
# Now with a MAGIC WORKFLOWS MENU for epic ComfyUI style-switching!
# "The wise wizard speaks softly—his parrot yells in all caps...with BUTTONS!"
#    — Gandalf the Pirate, Keeper of the Parrot

import os
import logging
import httpx
import glob
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
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
    "Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐\n" +
    "Use /workflows to choose your favorite wizard spell style."
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

if __name__ == '__main__':
  logging.info("Initializing the Parrot-bot's Telegram mind-link...")
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CommandHandler("dream", dream))
  app.add_handler(CommandHandler("workflows", workflows))
  app.add_handler(CallbackQueryHandler(button))
  logging.info("Bot is now polling for orders among the stars.")
  print("🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start, /dream, or /workflows")
  app.run_polling()