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
- 🌐 **Two-Machine Support** - Separate internet-facing bot from GPU machine for security

## 🚀 Quick Start

### Single Machine Setup

If running everything on one machine:

```bash
# 1. Clone the repository
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your environment variables
cp .env.example .env
# Edit .env with your Telegram token
# Keep COMFY_API_HOST=http://localhost:8000

# 4. Launch the Comfynaut crew!
python api_server.py  # In one terminal
python telegram_bot.py  # In another terminal
```

### Two Machine Setup (Recommended)

For better security with separate machines:

**On the GPU Machine (Gaming PC):**
```bash
# 1. Clone and install on GPU machine
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut
pip install -r requirements.txt

# 2. Start only the API server (no .env needed)
python api_server.py  # Runs on port 8000
```

**On the Internet-Facing Machine (Ubuntu Server/VPS):**
```bash
# 1. Clone and install on Ubuntu server
git clone https://github.com/lyquid/Comfynaut.git
cd Comfynaut
pip install -r requirements.txt

# 2. Set up environment variables
cp .env.example .env
# Edit .env:
#   TELEGRAM_TOKEN=your_bot_token
#   COMFY_API_HOST=http://192.168.1.100:8000  # IP of your GPU machine

# 3. Start only the Telegram bot
python telegram_bot.py
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

Comfynaut supports two deployment scenarios:

### 🖥️ Single Machine Setup (Simple)

All components run on one machine with a GPU:

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

### 🌐 Two Machine Setup (Recommended for Security)

This is the **recommended setup** that separates internet-facing components from your GPU machine:

```
┌──────────────────────┐                    ┌──────────────────────┐
│  Ubuntu Server       │                    │  Gaming PC / GPU     │
│  (Internet-Facing)   │                    │  (Private Network)   │
│                      │                    │                      │
│  ┌────────────────┐  │                    │  ┌────────────────┐  │
│  │ Telegram Bot   │  │    HTTP Request    │  │ API Server     │  │
│  │ (Port 443/80)  │──┼───────────────────▶│  │ (Port 8000)    │  │
│  └────────────────┘  │                    │  └────────────────┘  │
│         ▲            │                    │         │            │
└─────────┼────────────┘                    │         ▼            │
          │                                 │  ┌────────────────┐  │
          │                                 │  │ ComfyUI        │  │
          │              Image URL          │  │ (Port 8188)    │  │
          └─────────────────────────────────┼──│                │  │
                                            │  └────────────────┘  │
                                            └──────────────────────┘
          
Internet ◀──────────▶ Ubuntu Server ◀──────────▶ Gaming PC (No Direct Internet)
                        (Firewall)              (GPU Processing)
```

**Why This Setup?**

- 🔒 **Security**: Your expensive GPU machine stays off the internet, protected from attacks
- 🎮 **Gaming PC Protection**: Keep your gaming rig isolated while still using it for AI
- 🌊 **Network Separation**: Only the lightweight Telegram bot faces the internet
- 🛡️ **Firewall Friendly**: Gaming PC can be behind NAT/firewall with no port forwarding
- 💰 **Cost Effective**: Use a cheap VPS/cloud server for the bot, GPU hardware at home

### Components

- **`telegram_bot.py`** 🦜 - The Telegram interface, your friendly parrot
  - Runs on the **internet-facing machine** (Ubuntu server, VPS, etc.)
  - Receives commands from Telegram users
  - Forwards requests to the API server
  
- **`api_server.py`** 🏰 - FastAPI server that talks to ComfyUI
  - Runs on the **GPU machine** (gaming PC, workstation, etc.)
  - Can be on a private network, not exposed to internet
  - Communicates with local ComfyUI instance
  
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
4. Make sure your workflow has a text input node (default is node ID "16")

### Prompt Enhancement

The API server automatically appends quality keywords to your prompts:
```python
", high quality, masterpiece, best quality, 8k"
```

You can customize this in `api_server.py` by modifying the `PROMPT_HELPERS` variable.

## 🔧 Configuration

### API Server Settings (`api_server.py`)

These settings apply to the machine running the API server (GPU machine):

- **`COMFYUI_API`** - ComfyUI API endpoint (default: `http://127.0.0.1:8188`)
  - This should always point to localhost since ComfyUI runs on the same machine
- **`POSITIVE_PROMPT_NODE_ID`** - Node ID for positive prompt injection (default: `"16"`)
- **`PROMPT_HELPERS`** - Quality keywords appended to prompts
- **`DEFAULT_WORKFLOW_PATH`** - Path to the workflow JSON file

### Telegram Bot Settings (`.env`)

These settings apply to the machine running the Telegram bot:

- **`TELEGRAM_TOKEN`** - Your bot token from BotFather
- **`COMFY_API_HOST`** - URL to reach your Comfynaut API server
  - **Single machine:** `http://localhost:8000`
  - **Two machines:** `http://192.168.1.100:8000` (replace with your GPU machine's IP)

### Network Configuration for Two-Machine Setup

When using separate machines:

1. **GPU Machine (api_server.py):**
   - Listens on `0.0.0.0:8000` (all interfaces)
   - Only needs to be reachable by Ubuntu server, NOT the internet
   - ComfyUI runs on the same machine at `127.0.0.1:8188`

2. **Ubuntu Server (telegram_bot.py):**
   - Connects to Telegram API (internet access required)
   - Connects to GPU machine via `COMFY_API_HOST`
   - Can be behind firewall (outbound connections only)

3. **Network Options:**
   - **Local Network:** Direct connection via LAN (192.168.x.x)
   - **VPN:** Connect machines via WireGuard, Tailscale, etc.
   - **SSH Tunnel:** `ssh -L 8000:localhost:8000 gpu-machine` on Ubuntu server
   - **Reverse Proxy:** Use nginx/caddy on GPU machine (advanced)

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

[⬆ Back to Top](#-comfynaut)

</div>
