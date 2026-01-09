<a id="top"></a>

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
- 🖼️ **Text-to-Image Generation** - Create stunning images from text prompts using `/dream` command with SDXL workflows and LoRA support
- 🎨 **Image-to-Image Transformation** - Transform existing images with text prompts via `/img2img` command
- 🎬 **Image-to-Video Generation** - Animate still images into videos using `/img2vid` command
- 🔧 **Dynamic Workflow Selection** - Choose from multiple workflows via `/workflows` command in Telegram
- 🎠 **Marathon Mode** - Endless auto-generation carousel with new seeds until you say stop!
- ⚡ **Fast & Asynchronous** - Async HTTP requests with httpx for smooth sailing
- 🔌 **WebSocket Communication** - Real-time, event-driven updates from ComfyUI (no polling!)
- 🧙 **Smart Node Detection** - Automatically finds positive prompt and image load nodes
- 🎲 **Random Seed Generation** - Each request generates unique variations
- 🎯 **Quality Prompts** - Automatically enhances prompts with quality keywords
- 🌊 **RESTful API** - FastAPI-based server for flexibility
- 🔒 **Environment-based Config** - Keep your secrets safe with `.env` files

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your environment variables
cp .env.example .env
# Edit .env with your Telegram token

# 4. Launch Comfynaut (runs both bot and API server)
python main.py
```

### Running as a Systemd Service

Create `/etc/systemd/system/comfynaut.service`:

> **⚠️ Important:** If you're using a virtual environment (recommended), you **must** use the venv's Python interpreter in `ExecStart`. Using the system Python (`/usr/bin/python3`) will cause import errors because the dependencies from `requirements.txt` won't be available unless installed globally.

**For Virtual Environment Setup (Recommended):**
```ini
[Unit]
Description=Comfynaut - Telegram Bot for ComfyUI
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Comfynaut
ExecStart=/path/to/Comfynaut/venv/bin/python main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
# Optional: Load environment variables from .env file
# EnvironmentFile=/path/to/Comfynaut/.env

[Install]
WantedBy=multi-user.target
```

**For Global Installation (System Python):**
```ini
[Unit]
Description=Comfynaut - Telegram Bot for ComfyUI
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/Comfynaut
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
# Optional: Load environment variables from .env file
# EnvironmentFile=/path/to/Comfynaut/.env

[Install]
WantedBy=multi-user.target
```

> 💡 **Note:** The `EnvironmentFile` directive allows systemd to load environment variables from your `.env` file. If you use this, make sure the `.env` file has appropriate permissions (`chmod 600 .env`) to protect sensitive tokens.

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable comfynaut
sudo systemctl start comfynaut
sudo systemctl status comfynaut  # Check status
sudo journalctl -u comfynaut -f  # View logs
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
pip install -r requirements.txt
```

#### 2️⃣ Configure Environment Variables

Copy the example `.env` file and edit it:
```bash
cp .env.example .env
```

Configure these variables:
```env
# .env file
TELEGRAM_TOKEN=your_telegram_bot_token_here
COMFYUI_HOST=127.0.0.1:8188
COMFY_API_HOST=http://localhost:8000
```

> 💡 **Tip:** Get your Telegram bot token by talking to [@BotFather](https://t.me/botfather) on Telegram!

#### 3️⃣ Set Up ComfyUI

Make sure ComfyUI is running and accessible at `http://127.0.0.1:8188` (or update `COMFYUI_HOST` in your `.env` file).

## 📖 Usage

### Starting Comfynaut

Launch both the API server and Telegram bot with a single command:

```bash
python main.py
```

You should see:
```
⚓🧙‍♂️ COMFYNAUT LAUNCHING! 🧙‍♂️⚓
══════════════════════════════════════
"All we have to decide is what to do 
 with the prompts that are given to us."
══════════════════════════════════════
```

### Telegram Commands

Once your bot is running, open Telegram and:

#### `/start` - Wake up the parrot 🦜
```
/start
```
Response: *"Arrr, Captain! Comfynaut is ready to ferry your prompt wishes to the stars! 🦜🪐"*

#### `/workflows` - Choose your workflow style 🧙‍♂️
```
/workflows
```
Displays an interactive menu of all available workflows from your `workflows/` directory. Select one to use for all subsequent `/dream` commands.

#### `/dream` - Generate an image from text 🎨
```
/dream a majestic dragon flying over a medieval castle at sunset
```

The bot will:
1. 🦜 Acknowledge your request
2. 🏰 Send it to the GPU wizard's castle (ComfyUI)
3. ⏳ Wait for the image to be generated
4. 🖼️ Send you the generated image

#### `/marathon` - Endless Auto-Generation Carousel 🎠
```
/marathon a majestic dragon in various poses
```

Start an endless image-generation voyage! The bot will continuously generate images with new random seeds until you stop it.

Features:
- 🎲 Each image uses a different random seed
- 🔄 Continues until you say stop
- 📊 Progress updates every 5 images
- 🧙 Works with any selected workflow
- ⚡ Perfect for exploring variations and finding the perfect generation

To stop the marathon:
```
/stop
```

This is ideal for:
- Artists exploring different variations of a concept
- Finding the perfect seed for your prompt
- Creating a large collection of similar but unique images
- Experimenting with prompt effects across multiple generations

#### `/stop` - Stop the Marathon 🛑
```
/stop
```

Stops the currently running image marathon. Shows you how many images were generated.

#### `/img2img` - Transform an existing image 🖼️➡️🎨
```
/img2img make it look like a watercolor painting
```

To use this command:
1. **Reply to an image** with `/img2img <prompt>`, or
2. **Send an image** with `/img2img <prompt>` as the caption

The bot will transform the image based on your prompt using the CyberRealistic Pony workflow.

### Example Prompts

Try these magical prompts:

- `/dream cyberpunk city at night with neon lights`
- `/dream cute robot reading a book in a cozy library`
- `/dream fantasy landscape with floating islands and waterfalls`
- `/dream portrait of a friendly dragon wearing glasses`
- `/marathon cyberpunk warrior in different action poses` (endless generation!)
- `/img2img make her smile` (reply to a portrait)
- `/img2img turn into an oil painting` (with an image)

## 🏗️ Architecture

```
┌─────────────┐    Commands    ┌──────────────┐     HTTP      ┌──────────────┐
│             │   (/dream,     │   Telegram   │   Request     │   Comfynaut  │
│  Telegram   │   /img2img,    │     Bot      │──────────────▶│  API Server  │
│    User     │   /img2vid)    │              │               │ (Port 8000)  │
│             │───────────────▶│              │◀──────────────│              │
└─────────────┘                └──────────────┘  Image/Video  └──────────────┘
      ▲                              │                              │
      │                              │                              │ HTTP +
      │           Image/Video        │                              │ WebSocket
      └──────────────────────────────┘                              │
                                                                    ▼
                                                             ┌──────────────┐
                                                             │   ComfyUI    │
                                                             │   (Local)    │
                                                             │ (Port 8188)  │
                                                             └──────────────┘
```

> 🔌 **Note**: The API server uses WebSocket for real-time, event-driven communication with ComfyUI instead of polling. This is more efficient as it eliminates unnecessary HTTP requests while waiting for generation to complete.

### Components

- **`main.py`** 🚀 - Unified entry point that launches everything
  - Starts both the API server and Telegram bot in parallel
  - Perfect for running as a systemd service
  - Use `python main.py` to launch Comfynaut

- **`telegram_bot.py`** 🦜 - The Telegram interface, your friendly parrot
  - Receives commands from Telegram users
  - Forwards requests to the API server
  
- **`api_server.py`** 🏰 - FastAPI server that talks to ComfyUI
  - Connects to ComfyUI via HTTP and WebSocket
  - Uses `COMFYUI_HOST` env var to locate ComfyUI

- **`workflows/`** 📁 - ComfyUI workflow JSON files
  - Dynamically loaded at runtime - add any `.json` workflow here
  - `t2i - SDXL.json` - Default text-to-image workflow with SDXL
  - `i2i - CyberRealistic Pony 14.1.json` - Image-to-image transformation workflow
  - `i2v - WAN 2.2 Smooth Workflow v2.0.json` - Image-to-video animation workflow
  - Users can select workflows via `/workflows` command in Telegram

## 🎯 Workflow Customization

Comfynaut uses ComfyUI workflow JSON files stored in the `workflows/` directory. The included workflows are:
- `t2i - SDXL.json` - Text-to-image generation with SDXL (default for `/dream` command)
- `t2i - CyberRealistic Pony 14.1.json` - CyberRealistic Pony text-to-image workflow
- `t2i - One obsession 14 2.4D_nsfw.json` - One Obsession text-to-image workflow
- `i2i - CyberRealistic Pony 14.1.json` - Image-to-image transformation workflow (used by `/img2img`)
- `i2v - WAN 2.2 Smooth Workflow v2.0.json` - Image-to-video animation workflow (used by `/img2vid`)

> ⚠️ **Important**: The workflow files contain references to specific model files. You may need to update these to match the models installed in your ComfyUI setup. Edit the workflow JSON files and replace the `ckpt_name` and `lora_name` values with your available models.

### Using Custom Workflows

1. Export your workflow from ComfyUI as API format JSON
2. Save it to the `workflows/` directory with a descriptive name (e.g., `my_custom_style.json`)
3. Restart the Telegram bot to load the new workflow
4. Use `/workflows` command in Telegram to select your new workflow
5. Make sure your workflow has:
   - At least one `CLIPTextEncode` node (preferably with "positive" in the title)
   - A `KSampler` node for seed randomization

**Note:** The system automatically detects:
- Positive prompt nodes (looks for `CLIPTextEncode` with "positive" in title)
- KSampler nodes (for dynamic seed generation)

### Prompt Enhancement

The API server automatically appends quality keywords to your prompts:
```python
", high quality, masterpiece, best quality, 8k"
```

You can customize this in `api_server.py` by modifying the `PROMPT_HELPERS` variable.

## 🔧 Configuration

### Environment Variables

| Variable | Used By | Default | Description |
|----------|---------|---------|-------------|
| `TELEGRAM_TOKEN` | telegram_bot.py | (required) | Bot token from @BotFather |
| `COMFYUI_HOST` | api_server.py | `127.0.0.1:8188` | ComfyUI host:port |
| `COMFY_API_HOST` | telegram_bot.py | `http://localhost:8000` | API server URL |

## 🐛 Troubleshooting

### Common Issues

#### Bot doesn't respond
- ✅ Check that `python main.py` is running
- ✅ Verify your `TELEGRAM_TOKEN` in `.env` is correct
- ✅ Make sure ComfyUI is running at the specified port

#### "Unable to reach the wizard's castle"
- ✅ Ensure the API server is running on port 8000
- ✅ Check `COMFY_API_HOST` in your `.env` file
- ✅ Verify ComfyUI is accessible at the configured `COMFYUI_HOST`

#### Images take too long or don't generate
- ✅ Check ComfyUI logs for errors
- ✅ Ensure your GPU drivers are properly installed
- ✅ Verify the workflow JSON file is valid
- ✅ Try a simpler prompt first

#### "No CLIPTextEncode nodes found in workflow"
- ✅ Your workflow file must have at least one `CLIPTextEncode` node for text prompts
- ✅ Verify the workflow JSON file is properly exported from ComfyUI in API format
- ✅ Check that the workflow contains nodes with `"class_type": "CLIPTextEncode"`

## 🎨 Advanced Usage

### Running Components Separately

If you prefer to run the components separately:

```bash
# Terminal 1 - API Server
python api_server.py

# Terminal 2 - Telegram Bot
python telegram_bot.py
```

### Running with Custom Uvicorn Options

```bash
# Custom host and port
uvicorn api_server:app --host 0.0.0.0 --port 5000 --reload

# With auto-reload for development
uvicorn api_server:app --reload
```

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

[⬆ Back to Top](#top)

</div>
