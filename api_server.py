# 🏰 api_server.py - Comfynaut Pirate-Ninja Portal, now with QUEST COMPLETION from /history!
# Upgraded to check ComfyUI /queue AND /history for finished treasures!

from fastapi import FastAPI  # FastAPI framework for building APIs
from pydantic import BaseModel  # For data validation and parsing
import requests  # For making HTTP requests
import os  # For interacting with the operating system
import json  # For handling JSON data
import time  # For time-related operations
import copy  # For creating deep copies of objects

# Initialize FastAPI application
app = FastAPI()

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
DEFAULT_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "text2img_LORA.json")
COMFYUI_API = "http://127.0.0.1:8188"
POSITIVE_PROMPT_NODE_ID = "16"  # Node ID for positive prompt in default workflow
PROMPT_HELPERS = ", high quality, masterpiece, best quality, 8k"

class DreamRequest(BaseModel):
    prompt: str

def load_workflow(path=DEFAULT_WORKFLOW_PATH):
    with open(path, "r") as f:
        return json.load(f)

def build_workflow(prompt: str, base_workflow=None):
    if base_workflow is None:
        base_workflow = load_workflow()
    workflow = copy.deepcopy(base_workflow)
    if POSITIVE_PROMPT_NODE_ID in workflow:
        workflow[POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = prompt + PROMPT_HELPERS
    else:
        raise ValueError("Could not find node " + POSITIVE_PROMPT_NODE_ID + " for positive prompt in workflow!")
    if "3" in workflow:
        workflow["3"]["inputs"]["seed"] = int(time.time()) % 999999999  # A sprinkle of Chaotic Randomness!
    return {"prompt": workflow}

@app.post("/dream")
async def receive_dream(req: DreamRequest):
    print(f"✨ Prompt received: '{req.prompt}' - Set sail for new dreams!")
    base_workflow = load_workflow()
    payload = build_workflow(req.prompt, base_workflow)
    try:
        resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            print("⚠️ No prompt_id from ComfyUI!")
            return {"status": "error", "message": "No prompt_id from ComfyUI!", "echo": req.prompt}
    except Exception as e:
        print(f"💥 Error reaching ComfyUI: {e}")
        return {"status": "error", "message": f"Error reaching ComfyUI: {e}", "echo": req.prompt}

    image_url = None
    # First, check /queue (just in case we are quick enough or ComfyUI is slow with migration)
    check_history_next = False
    for i in range(15):  # up to 30 sec, then check /history (queue tends to be quick to empty)
        try:
            queue_resp = requests.get(f"{COMFYUI_API}/queue")
            if queue_resp.status_code == 200:
                queue_data = queue_resp.json()
                if isinstance(queue_data, list):
                    queue_items = queue_data
                else:
                    queue_items = queue_data.get("queue_running", []) + queue_data.get("queue_done", [])
                for item in queue_items:
                    if (
                        isinstance(item, dict)
                        and item.get("prompt_id") == prompt_id
                        and "outputs" in item
                    ):
                        outputs = item["outputs"]
                        if outputs:
                            for node_output in outputs.values():
                                images = node_output.get("images", [])
                                if images:
                                    imginfo = images[0]
                                    image_url = f"{COMFYUI_API}/view?filename={imginfo['filename']}&subfolder={imginfo['subfolder']}"
                                    break
                if image_url:
                    print(f"🏴‍☠️ Found image in /queue in {2*i} seconds!")
                    break
        except Exception as e:
            print("Polling queue error:", e)
        time.sleep(2)
    else:
        # By Thror's Beard! Check /history for ghosts of finished quests...
        print("🧐 Nothing in /queue; seeking legends in /history...")
        try:
            hist_resp = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
            if hist_resp.status_code == 200:
                hist_data = hist_resp.json()
                if (
                    hist_data.get("status", {}).get("status_str") == "success"
                    and "outputs" in hist_data
                ):
                    for node_output in hist_data["outputs"].values():
                        images = node_output.get("images", [])
                        if images:
                            imginfo = images[0]
                            image_url = f"{COMFYUI_API}/view?filename={imginfo['filename']}&subfolder={imginfo['subfolder']}"
                            print("🏆 Image found in /history, the treasure is ours!")
                            break
                else:
                    print(f"History status: {hist_data.get('status')}, outputs: {hist_data.get('outputs')}")
            else:
                print(f"🛑 No luck fetching from /history/{prompt_id}, status {hist_resp.status_code}")
        except Exception as e:
            print("Polling /history error:", e)

    if image_url:
        return {
            "status": "success",
            "echo": req.prompt,
            "image_url": image_url,
            "message": "✨ Art conjured! A dragon (or maybe a car) awaits ye at the image URL."
        }
    else:
        return {
            "status": "error",
            "echo": req.prompt,
            "message": "Arrr, no image from ComfyUI—searched /queue and /history, got only goblins. Try again?"
        }

@app.get("/")
async def root():
    return {"message": "Welcome to Comfynaut GPU Wizardry Portal, now speaking true ComfyUI 'prompt' dialect!"}

if __name__ == "__main__":
    import uvicorn
    print("🧙‍♂️ Portals open on http://localhost:8000/")
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000)