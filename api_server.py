# 🏰 api_server.py - Comfynaut Pirate-Ninja Portal
# Now with ComfyUI /history support! Sails both /queue and /history to retrieve the finest plunder.
# If your image is conjured but lost to time in the queue... we'll fetch it from history, like a true spellcaster!

from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import time
import copy
import base64
import uuid

app = FastAPI()

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
DEFAULT_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "text2img_LORA.json")
IMG2IMG_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "img2img_LORA.json")
COMFYUI_API = "http://127.0.0.1:8188"
POSITIVE_PROMPT_NODE_ID = "16"  # Node ID for positive prompt in default workflow
IMAGE_LOAD_NODE_ID = "59"  # Node ID for loading input image in img2img workflow
PROMPT_HELPERS = ", high quality, masterpiece, best quality, 8k"

class DreamRequest(BaseModel):
  prompt: str

class Img2ImgRequest(BaseModel):
  prompt: str
  image_data: str  # Base64 encoded image

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
    workflow["3"]["inputs"]["seed"] = int(time.time()) % 999999999
  return {"prompt": workflow}

def build_img2img_workflow(prompt: str, image_filename: str, base_workflow=None):
  """Build an img2img workflow with image input and text prompt."""
  if base_workflow is None:
    base_workflow = load_workflow(IMG2IMG_WORKFLOW_PATH)
  workflow = copy.deepcopy(base_workflow)
  
  # Set the positive prompt
  if POSITIVE_PROMPT_NODE_ID in workflow:
    workflow[POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = prompt + PROMPT_HELPERS
  else:
    raise ValueError("Could not find node " + POSITIVE_PROMPT_NODE_ID + " for positive prompt in workflow!")
  
  # Set the input image
  if IMAGE_LOAD_NODE_ID in workflow:
    workflow[IMAGE_LOAD_NODE_ID]["inputs"]["image"] = image_filename
  else:
    raise ValueError("Could not find node " + IMAGE_LOAD_NODE_ID + " for image loading in workflow!")
  
  # Set random seed
  if "3" in workflow:
    workflow["3"]["inputs"]["seed"] = int(time.time()) % 999999999
  
  return {"prompt": workflow}

@app.post("/dream")
async def receive_dream(req: DreamRequest):
  print(f"✨ Prompt received: '{req.prompt}'")
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

  image_url = wait_for_image_generation(prompt_id)

  if image_url:
    return {
      "status": "success",
      "echo": req.prompt,
      "image_url": image_url,
      "message": "✨ Art conjured! A dragon (or maybe a truck) awaits ye at the image URL."
    }
  else:
    return {
      "status": "error",
      "echo": req.prompt,
      "message": "Arrr, no image from ComfyUI—checked the queue and the mists of history. Only goblins. Try again?"
    }

@app.post("/img2img")
async def receive_img2img(req: Img2ImgRequest):
  """Handle img2img requests with an input image and text prompt."""
  print(f"🎨 img2img request received with prompt: '{req.prompt}'")
  
  # Decode base64 image
  try:
    image_data = base64.b64decode(req.image_data)
  except Exception as e:
    print(f"💥 Error decoding image: {e}")
    return {"status": "error", "message": f"Error decoding image: {e}", "echo": req.prompt}
  
  # Generate a unique filename for the uploaded image
  image_filename = f"input_img2img_{uuid.uuid4().hex}.png"
  
  # Upload image to ComfyUI
  try:
    files = {
      'image': (image_filename, image_data, 'image/png'),
      'overwrite': (None, 'true')
    }
    upload_resp = requests.post(f"{COMFYUI_API}/upload/image", files=files, timeout=30)
    upload_resp.raise_for_status()
    upload_result = upload_resp.json()
    print(f"📤 Image uploaded to ComfyUI: {upload_result}")
  except Exception as e:
    print(f"💥 Error uploading image to ComfyUI: {e}")
    return {"status": "error", "message": f"Error uploading image to ComfyUI: {e}", "echo": req.prompt}
  
  # Build the img2img workflow
  base_workflow = load_workflow(IMG2IMG_WORKFLOW_PATH)
  payload = build_img2img_workflow(req.prompt, image_filename, base_workflow)
  
  # Submit the workflow to ComfyUI
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

  # Wait for the image to be generated
  image_url = wait_for_image_generation(prompt_id)

  if image_url:
    return {
      "status": "success",
      "echo": req.prompt,
      "image_url": image_url,
      "message": "✨ Image transformed! Your modified masterpiece awaits at the image URL."
    }
  else:
    return {
      "status": "error",
      "echo": req.prompt,
      "message": "Arrr, no image from ComfyUI—checked the queue and the mists of history. Only goblins. Try again?"
    }

@app.get("/")
async def root():
  return {"message": "Welcome to Comfynaut GPU Wizardry Portal, now speaking true ComfyUI 'prompt' dialect!"}

def wait_for_image_generation(prompt_id: str):
  """Common function to wait for image generation and retrieve the image URL."""
  image_url = None

  # First, check /queue for prompt_id and outputs
  for i in range(15):  # Up to 30 seconds in the queue
    try:
      queue_resp = requests.get(f"{COMFYUI_API}/queue")
      if queue_resp.status_code == 200:
        queue_data = queue_resp.json()
        queue_items = []
        if isinstance(queue_data, list):
          queue_items = queue_data
        elif isinstance(queue_data, dict):
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
                  print(f"🏴‍☠️ Found image in /queue at {2*i}s: {image_url}")
                  break
          if image_url:
            break
    except Exception as e:
      print("Polling queue error:", e)
    time.sleep(2)

  # If not in the queue, search for buried treasure in /history
  if not image_url:
    print("🧐 Searched /queue in vain... Seeking lost treasure in /history.")
    try:
      hist_resp = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
      if hist_resp.status_code == 200:
        hist_json = hist_resp.json()
        data = hist_json.get(prompt_id)
        if data and "outputs" in data and data.get("status", {}).get("status_str") == "success":
          for node_output in data["outputs"].values():
            images = node_output.get("images", [])
            if images:
              imginfo = images[0]
              image_url = f"{COMFYUI_API}/view?filename={imginfo['filename']}&subfolder={imginfo['subfolder']}"
              print(f"🏆 Found it in /history: {image_url}")
              break
        else:
          print("ℹ️ No finished outputs found in history for this prompt_id.")
      else:
        print(f"🛑 Could not fetch /history/{prompt_id}, status {hist_resp.status_code}")
    except Exception as e:
      print("Polling history error:", e)

  return image_url

if __name__ == "__main__":
  import uvicorn
  print("🧙‍♂️ Portals open on http://localhost:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)