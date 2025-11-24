# 🏰 api_server.py - Comfynaut Pirate-Ninja Portal
# Refactored by Gandalf the Pirate-Ninja, Slayer of NodeID Monsters!

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
IMG2IMG_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "i2i - CyberRealistic Pony.json")
IMG2VID_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "i2v - WAN 2.2 Smooth Workflow v2.0.json")
COMFYUI_API = "http://127.0.0.1:8188"
PROMPT_HELPERS = ", high quality, masterpiece, best quality, 8k"

# Video generation timeout settings (videos can take 10+ minutes)
VIDEO_POLL_INTERVAL = 10  # seconds between polling
VIDEO_MAX_POLL_ATTEMPTS = 90  # 90 * 10 seconds = 15 minutes max wait
VIDEO_PROGRESS_LOG_INTERVAL = 60  # Log progress every 60 seconds

class DreamRequest(BaseModel):
  prompt: str
  workflow: str = None

class Img2ImgRequest(BaseModel):
  prompt: str
  image_data: str  # Base64 encoded image

class Img2VidRequest(BaseModel):
  image_data: str  # Base64 encoded image

def load_workflow(path=DEFAULT_WORKFLOW_PATH):
  with open(path, "r") as f:
    return json.load(f)

def find_positive_prompt_node(workflow):
  """Find the 'Positive Prompt' CLIPTextEncode node dynamically."""
  clip_text_encode_nodes = []
  for node_id, node_data in workflow.items():
    if isinstance(node_data, dict) and node_data.get("class_type") == "CLIPTextEncode":
      title = node_data.get("_meta", {}).get("title", "").lower()
      clip_text_encode_nodes.append((node_id, title))
  if not clip_text_encode_nodes:
    raise ValueError("No CLIPTextEncode nodes found in workflow!")
  for node_id, title in clip_text_encode_nodes:
    if "positive" in title:
      return node_id
  return clip_text_encode_nodes[0][0]

def find_image_load_node(workflow):
  """Find the node for loading the input image (usually `LoadImage`)."""
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "LoadImage":
      return node_id
  raise ValueError("Could not find LoadImage node in workflow!")

def find_ksampler_node(workflow):
  """Find the KSampler node dynamically."""
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "KSampler":
      return node_id
  raise ValueError("Could not find KSampler node in workflow!")

def find_seed_node(workflow):
  """Find the Seed (rgthree) node for video generation workflows."""
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "Seed (rgthree)":
      return node_id
  raise ValueError("Could not find Seed (rgthree) node in workflow!")

def find_video_combine_node(workflow, require_save_output=False):
  """Find the VHS_VideoCombine node for video output.
  
  If require_save_output is True, only return nodes with save_output=True.
  """
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "VHS_VideoCombine":
      if require_save_output:
        if node_data.get("inputs", {}).get("save_output", False):
          return node_id
      else:
        return node_id
  raise ValueError("Could not find VHS_VideoCombine node in workflow!")

def build_workflow(prompt: str, base_workflow=None):
  if base_workflow is None:
    base_workflow = load_workflow()
  workflow = copy.deepcopy(base_workflow)
  # Dynamically find the positive prompt node
  positive_prompt_node_id = find_positive_prompt_node(workflow)
  workflow[positive_prompt_node_id]["inputs"]["text"] = prompt + PROMPT_HELPERS
  # Find and update KSampler seed dynamically
  try:
    ksampler_node_id = find_ksampler_node(workflow)
    workflow[ksampler_node_id]["inputs"]["seed"] = int(time.time()) % 999999999
  except ValueError:
    # Fallback to node "3" if KSampler not found
    if "3" in workflow:
      workflow["3"]["inputs"]["seed"] = int(time.time()) % 999999999
  return {"prompt": workflow}

def build_img2img_workflow(prompt: str, image_filename: str, base_workflow=None):
  if base_workflow is None:
    base_workflow = load_workflow(IMG2IMG_WORKFLOW_PATH)
  workflow = copy.deepcopy(base_workflow)
  # Find positive prompt node dynamically!
  positive_prompt_node_id = find_positive_prompt_node(workflow)
  workflow[positive_prompt_node_id]["inputs"]["text"] = prompt + PROMPT_HELPERS
  # Find image load node dynamically!
  image_load_node_id = find_image_load_node(workflow)
  workflow[image_load_node_id]["inputs"]["image"] = image_filename
  # Find and update KSampler seed dynamically
  try:
    ksampler_node_id = find_ksampler_node(workflow)
    workflow[ksampler_node_id]["inputs"]["seed"] = int(time.time()) % 999999999
  except ValueError:
    # Fallback to node "3" if KSampler not found
    if "3" in workflow:
      workflow["3"]["inputs"]["seed"] = int(time.time()) % 999999999
  return {"prompt": workflow}

def build_img2vid_workflow(image_filename: str, base_workflow=None):
  """Build the image-to-video workflow for WAN i2v."""
  if base_workflow is None:
    base_workflow = load_workflow(IMG2VID_WORKFLOW_PATH)
  workflow = copy.deepcopy(base_workflow)
  # Find and update LoadImage node
  image_load_node_id = find_image_load_node(workflow)
  workflow[image_load_node_id]["inputs"]["image"] = image_filename
  # Find and update Seed (rgthree) node for randomization
  try:
    seed_node_id = find_seed_node(workflow)
    workflow[seed_node_id]["inputs"]["seed"] = int(time.time() * 1000) % 999999999999999
  except ValueError:
    # Fallback: try KSampler if Seed node not found
    try:
      ksampler_node_id = find_ksampler_node(workflow)
      workflow[ksampler_node_id]["inputs"]["seed"] = int(time.time()) % 999999999
    except ValueError:
      print("⚠️ No seed node found, using workflow defaults")
  return {"prompt": workflow}

@app.post("/dream")
async def receive_dream(req: DreamRequest):
  print(f"✨ Prompt received: '{req.prompt}'")
  workflow_path = DEFAULT_WORKFLOW_PATH
  if req.workflow:
    candidate_path = os.path.join(WORKFLOWS_DIR, req.workflow)
    if os.path.isfile(candidate_path):
      workflow_path = candidate_path
      print(f"📄 Using workflow: {req.workflow}")
    else:
      print(f"⚠️ Workflow file not found: {candidate_path}, using default.")
  else:
    print("ℹ️ No workflow specified, using default.")
  base_workflow = load_workflow(workflow_path)
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
  print(f"🎨 img2img request received with prompt: '{req.prompt}'")
  try:
    image_data = base64.b64decode(req.image_data)
  except Exception as e:
    print(f"💥 Error decoding image: {e}")
    return {"status": "error", "message": f"Error decoding image: {e}", "echo": req.prompt}
  image_filename = f"input_img2img_{uuid.uuid4().hex}.png"
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
  base_workflow = load_workflow(IMG2IMG_WORKFLOW_PATH)
  try:
    payload = build_img2img_workflow(req.prompt, image_filename, base_workflow)
  except Exception as e:
    print(f"💥 Error building workflow: {e}")
    return {"status": "error", "message": f"Error building workflow: {e}", "echo": req.prompt}
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
      "message": "✨ Image transformed! Your modified masterpiece awaits at the image URL."
    }
  else:
    return {
      "status": "error",
      "echo": req.prompt,
      "message": "Arrr, no image from ComfyUI—checked the queue and the mists of history. Only goblins. Try again?"
    }

@app.post("/img2vid")
async def receive_img2vid(req: Img2VidRequest):
  print("🎬 img2vid request received")
  try:
    image_data = base64.b64decode(req.image_data)
  except Exception as e:
    print(f"💥 Error decoding image: {e}")
    return {"status": "error", "message": f"Error decoding image: {e}"}
  image_filename = f"input_img2vid_{uuid.uuid4().hex}.png"
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
    return {"status": "error", "message": f"Error uploading image to ComfyUI: {e}"}
  base_workflow = load_workflow(IMG2VID_WORKFLOW_PATH)
  try:
    payload = build_img2vid_workflow(image_filename, base_workflow)
  except Exception as e:
    print(f"💥 Error building workflow: {e}")
    return {"status": "error", "message": f"Error building workflow: {e}"}
  try:
    resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    prompt_id = result.get("prompt_id")
    if not prompt_id:
      print("⚠️ No prompt_id from ComfyUI!")
      return {"status": "error", "message": "No prompt_id from ComfyUI!"}
  except Exception as e:
    print(f"💥 Error reaching ComfyUI: {e}")
    return {"status": "error", "message": f"Error reaching ComfyUI: {e}"}
  # Wait for video generation with extended timeout
  video_url = wait_for_video_generation(prompt_id)
  if video_url:
    return {
      "status": "success",
      "video_url": video_url,
      "message": "🎬 Video conjured! Your moving masterpiece awaits at the video URL."
    }
  else:
    return {
      "status": "error",
      "message": "Arrr, no video from ComfyUI—the animation eluded us. Try again, brave wizard?"
    }

@app.get("/")
async def root():
  return {"message": "Welcome to Comfynaut GPU Wizardry Portal, now speaking true ComfyUI 'prompt' dialect!"}

def wait_for_image_generation(prompt_id: str):
  image_url = None
  for i in range(15):
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

def wait_for_video_generation(prompt_id: str):
  """Wait for video generation with extended timeout (up to 15 minutes).
  
  Videos take much longer to generate than images, so we poll less frequently
  but for a longer total duration.
  """
  video_url = None
  print(f"⏳ Waiting for video generation (polling every {VIDEO_POLL_INTERVAL}s for up to {VIDEO_MAX_POLL_ATTEMPTS * VIDEO_POLL_INTERVAL // 60} minutes)...")
  
  for i in range(VIDEO_MAX_POLL_ATTEMPTS):
    elapsed = i * VIDEO_POLL_INTERVAL
    progress_log_polls = VIDEO_PROGRESS_LOG_INTERVAL // VIDEO_POLL_INTERVAL
    if i % progress_log_polls == 0:  # Log progress every VIDEO_PROGRESS_LOG_INTERVAL seconds
      print(f"🎬 Video generation in progress... ({elapsed}s elapsed)")
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
                # Check for video output (gifs array from VHS_VideoCombine)
                gifs = node_output.get("gifs", [])
                if gifs:
                  vidinfo = gifs[0]
                  video_url = f"{COMFYUI_API}/view?filename={vidinfo['filename']}&subfolder={vidinfo.get('subfolder', '')}&type={vidinfo.get('type', 'output')}"
                  print(f"🎬 Found video in /queue at {elapsed}s: {video_url}")
                  return video_url
    except Exception as e:
      print(f"Polling queue error at {elapsed}s:", e)
    time.sleep(VIDEO_POLL_INTERVAL)
  
  # If not found in queue, check history
  print("🧐 Searched /queue in vain... Seeking video treasure in /history.")
  try:
    hist_resp = requests.get(f"{COMFYUI_API}/history/{prompt_id}")
    if hist_resp.status_code == 200:
      hist_json = hist_resp.json()
      data = hist_json.get(prompt_id)
      if data and "outputs" in data and data.get("status", {}).get("status_str") == "success":
        for node_output in data["outputs"].values():
          # Check for video output
          gifs = node_output.get("gifs", [])
          if gifs:
            vidinfo = gifs[0]
            video_url = f"{COMFYUI_API}/view?filename={vidinfo['filename']}&subfolder={vidinfo.get('subfolder', '')}&type={vidinfo.get('type', 'output')}"
            print(f"🏆 Found video in /history: {video_url}")
            return video_url
      else:
        print("ℹ️ No finished outputs found in history for this prompt_id.")
    else:
      print(f"🛑 Could not fetch /history/{prompt_id}, status {hist_resp.status_code}")
  except Exception as e:
    print("Polling history error:", e)
  return video_url

if __name__ == "__main__":
  import uvicorn
  print("🧙‍♂️ Portals open on http://localhost:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)
