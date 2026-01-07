# Copilot Instructions for Comfynaut

## Project Overview
Comfynaut is a Telegram bot and API server for generating images (and videos) using ComfyUI workflows. It connects Telegram users to a local or remote ComfyUI instance, supporting dynamic workflow selection and real-time updates via WebSocket.

## Architecture & Key Components
- **`main.py`**: Unified entry point. Launches both the FastAPI server (`api_server.py`) and the Telegram bot (`telegram_bot.py`) in parallel.
- **`api_server.py`**: FastAPI app. Handles HTTP/WebSocket communication with ComfyUI. Loads and manages workflow JSONs from `workflows/`.
- **`telegram_bot.py`**: Handles Telegram commands, user interaction, and forwards requests to the API server.
- **`workflows/`**: Contains ComfyUI workflow JSON files. Users can add/replace workflows here; the bot detects and loads them dynamically.

## Developer Workflows
- **Start everything**: `python main.py` (recommended for production/systemd)
- **Run separately**: `python api_server.py` and `python telegram_bot.py` in different terminals
- **Custom API server**: Use `uvicorn api_server:app --reload` for development
- **Environment**: Copy `.env.example` to `.env` and set `TELEGRAM_TOKEN`, `COMFYUI_HOST`, and `COMFY_API_HOST`

## Project-Specific Patterns
- **Workflow selection**: Users select workflows via `/workflows` in Telegram; all `.json` files in `workflows/` are available.
- **Prompt enhancement**: Prompts are auto-appended with quality keywords (see `PROMPT_HELPERS` in `api_server.py`).
- **Node detection**: The system auto-detects `CLIPTextEncode` (positive prompt) and `KSampler` (seed) nodes in workflows.
- **WebSocket**: Real-time updates from ComfyUI, no polling.
- **Image-to-Image/Video**: Special commands `/img2img` and `/img2vid` use specific workflows.

## Integration Points
- **ComfyUI**: Expects ComfyUI running at `COMFYUI_HOST` (default: `127.0.0.1:8188`).
- **Telegram**: Requires a bot token from @BotFather.
- **API server**: Default at `http://localhost:8000` (configurable).

## Conventions & Tips
- **Workflows**: Add new workflows as `.json` files in `workflows/`. Restart the bot to load new workflows.
- **Workflow JSONs**: Must contain at least one `CLIPTextEncode` node and a `KSampler` node for full functionality.
- **Model paths**: Update `ckpt_name` and `lora_name` in workflow JSONs to match your ComfyUI setup.
- **.env**: All secrets and config are loaded from `.env`.
- **Logs**: Use `systemctl status comfynaut` and `journalctl -u comfynaut -f` for service logs if running as a systemd service.

## Example: Add a Custom Workflow
1. Export a workflow from ComfyUI as API JSON.
2. Place it in `workflows/` (e.g., `my_style.json`).
3. Restart the bot. Use `/workflows` in Telegram to select it.

---
For more, see `README.md` and comments in `api_server.py` and `telegram_bot.py`.
