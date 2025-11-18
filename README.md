# 🧙‍♂️⚓ Comfynaut

> *"All we have to decide is what to do with the prompts that are given to us."*  
> — Gandalfrond the Whitebeard, 2025

<div align="center">

🦜 **Your Magical Telegram Parrot for ComfyUI Image Generation** 🎨

[Features](#-features) • [Quick Start](#-quick-start) • [Setup](#-setup) • [Usage](#-usage) • [Architecture](#-architecture) • [Contributing](#-contributing)

</div>

---

## 🌟 What is Comfynaut?

Comfynaut is your friendly **Telegram bot companion** that transforms text prompts into stunning AI-generated images using [ComfyUI](https://github.com/comfyanonymous/ComfyUI). Think of it as a pirate-ninja-wizard hybrid that sails through the digital seas, wielding GPU-powered magic! ⚔️🪐

Simply send a message to your Telegram bot, and watch as your imagination comes to life through the power of Stable Diffusion workflows.

## ✨ Features

- 🦜 **Telegram Integration** - Control everything from your favorite messaging app
- 🎨 **ComfyUI Powered** - Leverage the full power of ComfyUI workflows
- ⚡ **Fast & Asynchronous** - Queue-based processing for smooth sailing
- 🔧 **Customizable Workflows** - Support for custom ComfyUI workflow JSON files
- 🎯 **Quality Prompts** - Automatically enhances prompts with quality keywords
- 🌊 **RESTful API** - FastAPI-based server for flexibility
- 🔒 **Environment-based Config** - Keep your secrets safe with `.env` files

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut

# 2. Install dependencies
pip install python-telegram-bot python-dotenv fastapi uvicorn requests

# 3. Set up your environment variables
cp .env.example .env
# Edit .env with your tokens and settings

# 4. Launch the Comfynaut crew!
python api_server.py  # In one terminal
python telegram_bot.py  # In another terminal
```

## 🛠️ Setup

### Prerequisites

Before you embark on this magical journey, ensure you have:

- 🐍 **Python 3.8+** installed
- 🤖 **Telegram Bot Token** from [@BotFather](https://t.me/botfather)
- 🎨 **ComfyUI** running locally or on a server
- 🖥️ **GPU** (recommended) for faster image generation

### Installation

#### 1️⃣ Install Dependencies

```bash
pip install python-telegram-bot python-dotenv fastapi uvicorn requests
```

Or create a `requirements.txt`:
```txt
python-telegram-bot>=20.0
python-dotenv>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
requests>=2.31.0
```

Then install with:
```bash
pip install -r requirements.txt
```

#### 2️⃣ Configure Environment Variables

Create a `.env` file in the root directory:

```env
# Telegram Bot Configuration
TELEGRAM_TOKEN=your_telegram_bot_token_here

# ComfyUI API Configuration
COMFY_API_HOST=http://localhost:8000
```

> 💡 **Tip:** Get your Telegram bot token by talking to [@BotFather](https://t.me/botfather) on Telegram!

#### 3️⃣ Set Up ComfyUI

Make sure ComfyUI is running and accessible at `http://127.0.0.1:8188` (or update the URL in `api_server.py`).

## 📖 Usage

### Starting the Services

You'll need **two terminals** (or use a process manager):

**Terminal 1 - API Server:**
```bash
python api_server.py
```
You should see:
```
🧙‍♂️ Portals open on http://localhost:8000/
```

**Terminal 2 - Telegram Bot:**
```bash
python telegram_bot.py
```
You should see:
```
🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start or /dream
```

### Telegram Commands

Once your bot is running, open Telegram and:

#### `/start` - Wake up the parrot 🦜
```
/start
```
Response: *"Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐"*

#### `/dream` - Generate an image 🎨
```
/dream a majestic dragon flying over a medieval castle at sunset
```

The bot will:
1. 🦜 Acknowledge your request
2. 🏰 Send it to the GPU wizard's castle (ComfyUI)
3. ⏳ Wait for the image to be generated
4. 🖼️ Send you the image URL

### Example Prompts

Try these magical prompts:

- `/dream cyberpunk city at night with neon lights`
- `/dream cute robot reading a book in a cozy library`
- `/dream fantasy landscape with floating islands and waterfalls`
- `/dream portrait of a friendly dragon wearing glasses`

## 🏗️ Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Telegram   │ /dream  │  Comfynaut   │  HTTP   │   ComfyUI   │
│    User     │────────▶│  API Server  │────────▶│   (Local)   │
│             │         │ (Port 8000)  │         │ (Port 8188) │
└─────────────┘         └──────────────┘         └─────────────┘
      ▲                         │                         │
      │                         │                         │
      │                         ▼                         │
      │                 ┌──────────────┐                 │
      └─────────────────│   Telegram   │◀────────────────┘
                        │     Bot      │    Image URL
                        └──────────────┘
```

### Components

- **`telegram_bot.py`** 🦜 - The Telegram interface, your friendly parrot
- **`api_server.py`** 🏰 - FastAPI server that talks to ComfyUI
- **`main.py`** 🚀 - Entry point (currently a simple launcher)
- **`workflows/`** 📁 - ComfyUI workflow JSON files
  - `text2img_LORA.json` - Default text-to-image workflow with LoRA support
  - `default.json` - Basic workflow template

## 🎯 Workflow Customization

Comfynaut uses ComfyUI workflow JSON files stored in the `workflows/` directory. The default workflow is `text2img_LORA.json`.

### Using Custom Workflows

1. Export your workflow from ComfyUI as API format JSON
2. Save it to the `workflows/` directory
3. Update `DEFAULT_WORKFLOW_PATH` in `api_server.py` to point to your workflow
4. Make sure your workflow has at least one `CLIPTextEncode` node (the system will automatically detect the positive prompt node)

### Prompt Enhancement

The API server automatically appends quality keywords to your prompts:
```python
", high quality, masterpiece, best quality, 8k"
```

You can customize this in `api_server.py` by modifying the `PROMPT_HELPERS` variable.

## 🔧 Configuration

### API Server Settings (`api_server.py`)

- **`COMFYUI_API`** - ComfyUI API endpoint (default: `http://127.0.0.1:8188`)
- **`PROMPT_HELPERS`** - Quality keywords appended to prompts
- **`DEFAULT_WORKFLOW_PATH`** - Path to the workflow JSON file

**Note:** The positive prompt node is automatically detected from your workflow. The system looks for `CLIPTextEncode` nodes and prioritizes those with "positive" in their title.

### Telegram Bot Settings (`.env`)

- **`TELEGRAM_TOKEN`** - Your bot token from BotFather
- **`COMFY_API_HOST`** - Your Comfynaut API server URL (default: `http://localhost:8000`)

## 🐛 Troubleshooting

### Bot doesn't respond
- ✅ Check that both `api_server.py` and `telegram_bot.py` are running
- ✅ Verify your `TELEGRAM_TOKEN` in `.env` is correct
- ✅ Make sure ComfyUI is running at the specified port

### "Unable to reach the wizard's castle"
- ✅ Ensure `api_server.py` is running on port 8000
- ✅ Check `COMFY_API_HOST` in your `.env` file
- ✅ Verify ComfyUI is accessible at `http://127.0.0.1:8188`

### Images take too long or don't generate
- ✅ Check ComfyUI logs for errors
- ✅ Ensure your GPU drivers are properly installed
- ✅ Verify the workflow JSON file is valid
- ✅ Try a simpler prompt first

### "No CLIPTextEncode nodes found in workflow"
- ✅ Your workflow file must have at least one `CLIPTextEncode` node for text prompts
- ✅ Verify the workflow JSON file is properly exported from ComfyUI in API format
- ✅ Check that the workflow contains nodes with `"class_type": "CLIPTextEncode"`

## 🎨 Advanced Usage

### Running with Uvicorn Options

```bash
# Custom host and port
uvicorn api_server:app --host 0.0.0.0 --port 5000 --reload

# With auto-reload for development
uvicorn api_server:app --reload
```

### Using Docker (Coming Soon! 🚢)

We're working on Docker support for even easier deployment!

## 🤝 Contributing

Contributions are welcome, fellow adventurers! Whether you're a pirate, ninja, or wizard:

1. 🍴 Fork the repository
2. 🌿 Create a feature branch (`git checkout -b feature/amazing-feature`)
3. 💫 Make your changes
4. ✅ Test your changes
5. 📝 Commit with a descriptive message
6. 🚀 Push to your branch
7. 🎉 Open a Pull Request

## 📜 License

This project is open source and available for all who seek adventure in the realm of AI art! 

---

## 🙏 Acknowledgments

- 🎨 **[ComfyUI](https://github.com/comfyanonymous/ComfyUI)** - The amazing workflow-based UI for Stable Diffusion
- 🤖 **[python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)** - Excellent Telegram bot framework
- ⚡ **[FastAPI](https://fastapi.tiangolo.com/)** - Modern, fast web framework for building APIs

## 🌊 Support

Having trouble? Found a bug? Have a feature request?

- 📫 Open an issue on GitHub
- 💬 Check existing issues for solutions
- 🦜 Remember: Even the wisest wizards were once apprentices!

---

<div align="center">

**Made with ❤️ by the Pirate-Ninjas Guild**

*May your prompts be creative and your GPUs be cool!* 🧙‍♂️⚓

[⬆ Back to Top](#-comfynaut)

</div>
