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
- ⚡ **Fast & Asynchronous** - Async HTTP requests with httpx for smooth sailing
- 🔌 **WebSocket Communication** - Real-time, event-driven updates from ComfyUI (no polling!)
- 🔧 **Dynamic Workflow Selection** - Choose from multiple workflows via inline menu
- 🧙 **Smart Node Detection** - Automatically finds positive prompt and image load nodes
- 🎲 **Random Seed Generation** - Each request generates unique variations
- 🎯 **Quality Prompts** - Automatically enhances prompts with quality keywords
- 🖼️ **img2img Support** - Transform existing images with text prompts
- 🎬 **img2vid Support** - Convert images to videos using Stable Video Diffusion
- 🌊 **RESTful API** - FastAPI-based server for flexibility
- 🔒 **Environment-based Config** - Keep your secrets safe with `.env` files
- 🌐 **Two-Machine Support** - Separate internet-facing bot from GPU machine for security

## 🚀 Quick Start

### Single Machine Setup

If running everything on one machine (including ComfyUI):

```bash
# 1. Clone the repository
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your environment variables
cp .env.example .env
# Edit .env with your Telegram token
# Keep defaults for COMFYUI_HOST and COMFY_API_HOST

# 4. Launch Comfynaut (runs both bot and API server)
python main.py
```

### Two Machine Setup (Recommended)

For better security, run Comfynaut on an Ubuntu server while ComfyUI stays isolated on your GPU machine:

**On the GPU Machine (Gaming PC):**
```bash
# Just run ComfyUI - no Comfynaut code needed!
# Make sure ComfyUI is accessible on port 8188 from your Ubuntu server
python main.py --listen 0.0.0.0  # In your ComfyUI directory
```

**On the Ubuntu Server (Internet-Facing):**
```bash
# 1. Clone and install on Ubuntu server
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut
pip install -r requirements.txt

# 2. Set up environment variables
cp .env.example .env
# Edit .env:
#   TELEGRAM_TOKEN=your_bot_token
#   COMFYUI_HOST=192.168.1.100:8188  # IP:port of your GPU machine's ComfyUI

# 3. Launch Comfynaut (runs both bot and API server)
python main.py
```

### Running as a Systemd Service

Create `/etc/systemd/system/comfynaut.service`:
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

[Install]
WantedBy=multi-user.target
```

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
pip install python-telegram-bot python-dotenv fastapi uvicorn httpx websocket-client
```

Or use the provided `requirements.txt`:
```txt
python-telegram-bot>=20.0
python-dotenv>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
requests>=2.31.0
websocket-client>=1.8.0
```

Then install with:
```bash
pip install -r requirements.txt
```

#### 2️⃣ Configure Environment Variables

The configuration differs based on your deployment:

**Single Machine Setup:**
```env
# .env file (used by telegram_bot.py)
TELEGRAM_TOKEN=your_telegram_bot_token_here
COMFY_API_HOST=http://localhost:8000
```

**Two Machine Setup:**

On the **Ubuntu Server** (internet-facing, runs telegram bot):
```env
# .env file
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Point to your GPU machine's IP address and port
# This can be a local network IP (192.168.x.x) or 
# a VPN/tunnel IP if machines are in different locations
COMFY_API_HOST=http://192.168.1.100:8000
```

On the **GPU Machine** (gaming PC, runs api_server and ComfyUI):
```
# No .env file needed!
# The api_server.py connects to ComfyUI at http://127.0.0.1:8188 (hardcoded)
# The api_server.py listens on port 8000 for requests from telegram_bot
```

> 💡 **Tip:** Get your Telegram bot token by talking to [@BotFather](https://t.me/botfather) on Telegram!

> 🔒 **Security Note:** In the two-machine setup, the GPU machine does NOT need to be exposed to the internet. Only ensure the Ubuntu server can reach it via local network, VPN, or secure tunnel.

#### 3️⃣ Set Up ComfyUI

Make sure ComfyUI is running and accessible at `http://127.0.0.1:8188` (or update the URL in `api_server.py`).

## 📖 Usage

### Starting the Services

The startup process depends on your deployment:

#### Single Machine Setup

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

#### Two Machine Setup

**On GPU Machine (Gaming PC):**
```bash
# Start the API server
python api_server.py
```
Output:
```
🧙‍♂️ Portals open on http://localhost:8000/
```

**On Ubuntu Server (Internet-Facing):**
```bash
# Start the Telegram bot
python telegram_bot.py
```
Output:
```
🎩🦜 Comfynaut Telegram Parrot listening for orders! Use /start or /dream
```

> 📡 **Network Note:** Ensure your Ubuntu server can reach the GPU machine on port 8000. Test with: `curl http://GPU_MACHINE_IP:8000/`

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

#### Photo + Caption - Transform an existing image 🎨🖼️

Simply send a photo to the bot with a caption describing how you want to transform it:

1. 📸 Send or forward any photo to the bot
2. ✏️ Add a caption describing the transformation you want
3. 🪄 The bot will apply your changes and send back the transformed image

**Examples:**
- Send a photo with caption: `change the color of the car to blue`
- Send a photo with caption: `make it look like a painting`
- Send a photo with caption: `add a sunset in the background`
- Send a photo with caption: `convert to anime style`

#### `/img2vid` - Convert an image to video 🎬

Reply to any photo with the `/img2vid` command to animate it using WAN image-to-video:

```
/img2vid
```

**How to use:**
1. 📸 Send a photo to the chat (or find an existing one)
2. 📝 Reply to that photo with `/img2vid`
3. ⏳ Wait patiently (video generation takes 10+ minutes!)
4. 🎬 Receive your animated video

⚠️ **Note:** Video generation is GPU-intensive and can take 10+ minutes depending on your hardware.

### Example Prompts

Try these magical prompts:

**Text-to-Image (/dream):**
- `/dream cyberpunk city at night with neon lights`
- `/dream cute robot reading a book in a cozy library`
- `/dream fantasy landscape with floating islands and waterfalls`
- `/dream portrait of a friendly dragon wearing glasses`

**Image-to-Image (photo + caption):**
- Send a landscape photo with caption: `make it look like sunset`
- Send a portrait with caption: `add glasses and a wizard hat`
- Send a car photo with caption: `change the color to red`
- Send any image with caption: `convert to cyberpunk style`

**Image-to-Video (/img2vid):**
- Reply to any photo with `/img2vid` to animate it
- ⚠️ Video generation can take 10+ minutes!

## 🏗️ Architecture

Comfynaut supports two deployment scenarios:

### 🖥️ Single Machine Setup (Simple)

All components run on one machine with a GPU:

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Telegram   │ /dream  │  Comfynaut   │  HTTP + │   ComfyUI   │
│    User     │────────▶│  API Server  │ WebSocket│   (Local)   │
│             │         │ (Port 8000)  │────────▶│ (Port 8188) │
└─────────────┘         └──────────────┘         └─────────────┘
      ▲                         │                         │
      │                         │                         │
      │                         ▼                         │
      │                 ┌──────────────┐                 │
      └─────────────────│   Telegram   │◀────────────────┘
                        │     Bot      │    Image URL
                        └──────────────┘
```

> 🔌 **Note**: The API server uses WebSocket for real-time, event-driven communication with ComfyUI instead of polling. This is more efficient as it eliminates unnecessary HTTP requests while waiting for generation to complete.

### 🌐 Two Machine Setup (Recommended for Security)

This is the **recommended setup** that keeps your GPU machine secure and isolated:

```
┌──────────────────────────────────────┐           ┌──────────────────────┐
│  Ubuntu Server (Internet-Facing)     │           │  Gaming PC / GPU     │
│                                      │           │  (Private Network)   │
│  ┌────────────────┐                  │           │                      │
│  │ Telegram Bot   │                  │           │                      │
│  │                │                  │           │                      │
│  └───────┬────────┘                  │           │                      │
│          │ HTTP                      │           │                      │
│          ▼                           │           │                      │
│  ┌────────────────┐    HTTP + WS     │           │  ┌────────────────┐  │
│  │ API Server     │──────────────────┼──────────▶│  │ ComfyUI        │  │
│  │ (Port 8000)    │                  │           │  │ (Port 8188)    │  │
│  └────────────────┘                  │           │  └────────────────┘  │
│          ▲                           │           │                      │
└──────────┼───────────────────────────┘           └──────────────────────┘
           │ Image URL                   
    ┌──────┴──────┐                      
    │  Telegram   │                      
    │    User     │                      
    └─────────────┘                      
          
Internet ◀──────────▶ Ubuntu Server ◀──────────▶ Gaming PC (No Internet)
                        (Firewall)              (Just ComfyUI running)
```

**Why This Setup?**

- 🔒 **Security**: Your GPU machine stays completely off the internet, protected from attacks
- 🎮 **Gaming PC Protection**: Keep your gaming rig isolated - only ComfyUI needs to run
- 🌊 **Simple GPU Setup**: No Comfynaut code on GPU machine - just ComfyUI
- 🛡️ **Firewall Friendly**: GPU machine can be behind NAT/firewall with no port forwarding to internet
- 💰 **Cost Effective**: Use a cheap VPS/cloud server for everything else, GPU hardware at home
- ⚡ **WebSocket Magic**: Real-time communication over the network - no polling overhead

### Components

- **`main.py`** 🚀 - Unified entry point that launches everything
  - Starts both the API server and Telegram bot in parallel
  - Perfect for running as a systemd service
  - Use `python main.py` to launch Comfynaut

- **`telegram_bot.py`** 🦜 - The Telegram interface, your friendly parrot
  - Runs on the **Ubuntu server** (or any internet-facing machine)
  - Receives commands from Telegram users
  - Forwards requests to the local API server
  
- **`api_server.py`** 🏰 - FastAPI server that talks to ComfyUI
  - Runs on the **Ubuntu server** (same machine as the bot)
  - Connects to ComfyUI remotely via HTTP and WebSocket
  - Uses `COMFYUI_HOST` env var to locate ComfyUI

- **`workflows/`** 📁 - ComfyUI workflow JSON files
  - Dynamically loaded at runtime - add any `.json` workflow here
  - `text2img_LORA.json` - Default text-to-image workflow with LoRA support
  - `img2img - CyberRealistic Pony.json` - Image-to-image workflow for transforming existing images
  - `img2vid.json` - Image-to-video workflow using WAN i2v
  - `default.json` - Basic workflow template
  - Users can select workflows via `/workflows` command in Telegram

## 🎯 Workflow Customization

Comfynaut uses ComfyUI workflow JSON files stored in the `workflows/` directory. The default workflows are:
- `text2img_LORA.json` - For text-to-image generation
- `img2img_LORA.json` - For image-to-image transformation
- `img2vid.json` - For image-to-video generation (uses WAN i2v)

> ⚠️ **Important**: The workflow files contain references to specific model files (e.g., `oneObsession_1424DNsfw.safetensors` and `22-nsfw-HIGH-e6.safetensors`). You will need to update these to match the models installed in your ComfyUI setup. Edit the workflow JSON files and replace the `ckpt_name` and `lora_name` values with your available models.

### Using Custom Workflows

1. Export your workflow from ComfyUI as API format JSON
2. Save it to the `workflows/` directory with a descriptive name (e.g., `my_custom_style.json`)
3. Restart the Telegram bot to load the new workflow
4. Use `/workflows` command in Telegram to select your new workflow
5. Make sure your workflow has:
   - At least one `CLIPTextEncode` node (preferably with "positive" in the title)
   - For img2img: A `LoadImage` node for the input image
   - For img2vid: A `LoadImage` node, `Seed (rgthree)` node, and `VHS_VideoCombine` node
   - A `KSampler` node for seed randomization

**Note:** The system automatically detects:
- Positive prompt nodes (looks for `CLIPTextEncode` with "positive" in title)
- Image load nodes (looks for `LoadImage` class type)
- KSampler nodes (for dynamic seed generation)
- Seed (rgthree) nodes (for video workflows)

### Prompt Enhancement

The API server automatically appends quality keywords to your prompts:
```python
", high quality, masterpiece, best quality, 8k"
```

You can customize this in `api_server.py` by modifying the `PROMPT_HELPERS` variable.

## 🔧 Configuration

### API Server Settings (`api_server.py`)

These settings control how the API server connects to ComfyUI:

- **`COMFYUI_HOST`** - ComfyUI host:port (env var, default: `127.0.0.1:8188`)
  - **Single machine:** Use default `127.0.0.1:8188`
  - **Remote ComfyUI:** Set to GPU machine IP, e.g., `192.168.1.100:8188`
- **`PROMPT_HELPERS`** - Quality keywords appended to prompts
- **`DEFAULT_WORKFLOW_PATH`** - Path to the text2img workflow JSON file
- **`IMG2IMG_WORKFLOW_PATH`** - Path to the img2img workflow JSON file
- **`WORKFLOWS_DIR`** - Directory containing all workflow files (default: `workflows/`)

**Note:** Node detection is fully automatic:
- **Positive prompt nodes** are detected by finding `CLIPTextEncode` nodes, prioritizing those with "positive" in the title
- **Image load nodes** are detected by finding `LoadImage` class types
- **KSampler nodes** are detected for dynamic seed generation on each request

### Telegram Bot Settings (`.env`)

These settings apply to the machine running the Telegram bot:

- **`TELEGRAM_TOKEN`** - Your bot token from BotFather
- **`COMFY_API_HOST`** - URL to reach your Comfynaut API server
  - **Single machine:** `http://localhost:8000`
  - **Remote API server:** `http://192.168.1.100:8000` (if api_server runs elsewhere)

### Environment Variables Summary

| Variable | Used By | Default | Description |
|----------|---------|---------|-------------|
| `TELEGRAM_TOKEN` | telegram_bot.py | (required) | Bot token from @BotFather |
| `COMFYUI_HOST` | api_server.py | `127.0.0.1:8188` | ComfyUI host:port |
| `COMFY_API_HOST` | telegram_bot.py | `http://localhost:8000` | API server URL |

### Network Configuration for Two-Machine Setup

When using separate machines (Ubuntu server + GPU machine):

1. **GPU Machine (ComfyUI only):**
   - Run ComfyUI with `--listen 0.0.0.0` to accept remote connections
   - Only needs to be reachable by Ubuntu server on port 8188
   - Does NOT need internet access or any Comfynaut code

2. **Ubuntu Server (Comfynaut):**
   - Runs both `api_server.py` and `telegram_bot.py`
   - Set `COMFYUI_HOST=<gpu-machine-ip>:8188` in `.env`
   - Connects to Telegram API (internet access required)
   - Can be behind firewall (outbound connections only)

3. **Network Options:**
   - **Local Network:** Direct connection via LAN (192.168.x.x)
   - **VPN:** Connect machines via WireGuard, Tailscale, etc.
   - **SSH Tunnel:** `ssh -L 8188:localhost:8188 gpu-machine` on Ubuntu server

## 🐛 Troubleshooting

### General Issues

#### Bot doesn't respond
- ✅ Check that both `api_server.py` and `telegram_bot.py` are running
- ✅ Verify your `TELEGRAM_TOKEN` in `.env` is correct
- ✅ Make sure ComfyUI is running at the specified port

#### "Unable to reach the wizard's castle"
- ✅ Ensure `api_server.py` is running on port 8000
- ✅ Check `COMFY_API_HOST` in your `.env` file
- ✅ Verify ComfyUI is accessible at `http://127.0.0.1:8188`

#### Images take too long or don't generate
- ✅ Check ComfyUI logs for errors
- ✅ Ensure your GPU drivers are properly installed
- ✅ Verify the workflow JSON file is valid
- ✅ Try a simpler prompt first

#### "Could not find node 16 for positive prompt"
- ✅ Your workflow file might have a different node ID
- ✅ Update `POSITIVE_PROMPT_NODE_ID` in `api_server.py` to match your workflow

### "No CLIPTextEncode nodes found in workflow"
- ✅ Your workflow file must have at least one `CLIPTextEncode` node for text prompts
- ✅ Verify the workflow JSON file is properly exported from ComfyUI in API format
- ✅ Check that the workflow contains nodes with `"class_type": "CLIPTextEncode"`

### Two-Machine Setup Issues

#### Telegram bot can't reach API server
```bash
# On Ubuntu server, test connectivity:
curl http://GPU_MACHINE_IP:8000/

# Should return: {"message": "Welcome to Comfynaut..."}
```

**If it fails:**
- ✅ Check `COMFY_API_HOST` in `.env` has the correct IP
- ✅ Verify GPU machine firewall allows port 8000
  ```bash
  # On GPU machine (Linux):
  sudo ufw allow 8000/tcp
  
  # On GPU machine (Windows):
  # Add inbound rule for port 8000 in Windows Firewall
  ```
- ✅ Ensure both machines are on the same network (or connected via VPN)
- ✅ Try pinging the GPU machine from Ubuntu server
  ```bash
  ping GPU_MACHINE_IP
  ```

#### Connection refused / timeout errors
- ✅ Verify `api_server.py` is listening on `0.0.0.0`, not just `127.0.0.1`
  - This is the default when using `uvicorn.run(..., host="0.0.0.0", port=8000)`
- ✅ Check if a router/NAT is between the machines
  - May need port forwarding or VPN solution
- ✅ Test with telnet:
  ```bash
  telnet GPU_MACHINE_IP 8000
  ```

#### API server can't reach ComfyUI
- ✅ Verify ComfyUI is running on the GPU machine
- ✅ Check ComfyUI is listening on port 8188
  ```bash
  # On GPU machine:
  netstat -tlnp | grep 8188  # Linux
  netstat -an | findstr 8188  # Windows
  ```
- ✅ ComfyUI must be on the same machine as `api_server.py`

### Network Security Tips

For the two-machine setup:

- 🔒 **Do NOT expose port 8000 to the internet** on your GPU machine
- 🔒 Only allow connections from your Ubuntu server's IP
- 🔒 Use firewall rules to restrict access:
  ```bash
  # On GPU machine, allow only from Ubuntu server:
  sudo ufw allow from UBUNTU_SERVER_IP to any port 8000
  ```
- 🔒 Consider using a VPN (WireGuard, Tailscale) for secure machine-to-machine communication
- 🔒 The Ubuntu server only needs outbound internet access (no inbound ports required)

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

[⬆ Back to Top](#comfynaut)

</div>
