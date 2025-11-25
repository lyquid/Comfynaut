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
import logging
import websocket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Logging setup
logging.basicConfig(
  format="%(asctime)s - %(levelname)s - %(message)s",
  level=logging.INFO
)
logger = logging.getLogger("comfynaut.api")

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
DEFAULT_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "text2img_LORA.json")
IMG2IMG_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "i2i - CyberRealistic Pony.json")
IMG2VID_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "i2v - WAN 2.2 Smooth Workflow v2.0.json")

# ComfyUI connection settings - configurable for remote connections
# Default to localhost for single-machine setup, or set COMFYUI_HOST for remote ComfyUI
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1:8188")
COMFYUI_API = f"http://{COMFYUI_HOST}"
COMFYUI_WS_URL = f"ws://{COMFYUI_HOST}/ws"

PROMPT_HELPERS = ", high quality, masterpiece, best quality, 8k"

# WebSocket settings for real-time communication with ComfyUI
# WebSocket is more efficient than polling - no wasted HTTP requests
WS_CONNECT_TIMEOUT = 10  # WebSocket connection timeout in seconds
WS_RECV_TIMEOUT = 5  # WebSocket receive timeout per message
WS_IMAGE_TIMEOUT = 60  # Total timeout for image generation
WS_VIDEO_TIMEOUT = 900  # Total timeout for video generation (15 min)

class DreamRequest(BaseModel):
  prompt: str
  workflow: str = None

class Img2ImgRequest(BaseModel):
  prompt: str
  image_data: str  # Base64 encoded image

class Img2VidRequest(BaseModel):
  image_data: str  # Base64 encoded image

def load_workflow(path=DEFAULT_WORKFLOW_PATH):
  """Load a ComfyUI workflow JSON with robust decoding & logging."""
  if not os.path.isfile(path):
    raise FileNotFoundError(f"Workflow file not found: {path}")
  encodings = ("utf-8", "utf-8-sig", "latin-1")
  last_error = None
  for enc in encodings:
    try:
      with open(path, "r", encoding=enc) as f:
        return json.load(f)
    except UnicodeDecodeError as e:
      logger.warning("Unicode decode error using %s for %s: %s", enc, path, e)
      last_error = e
      continue
    except json.JSONDecodeError as e:
      raise ValueError(f"Invalid JSON in workflow file {path}: {e}") from e
  raise UnicodeDecodeError("<multi>", b"", 0, 0, f"Failed to decode workflow file {path} with tried encodings: {encodings}. Last error: {last_error}")

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
  logger.info("Prompt received: '%s'", req.prompt)
  workflow_path = DEFAULT_WORKFLOW_PATH
  if req.workflow:
    candidate_path = os.path.join(WORKFLOWS_DIR, req.workflow)
    if os.path.isfile(candidate_path):
      workflow_path = candidate_path
      logger.info("Using workflow: %s", req.workflow)
    else:
      logger.warning("Workflow file not found: %s, using default.", candidate_path)
  else:
    logger.info("No workflow specified, using default.")
  base_workflow = load_workflow(workflow_path)
  payload = build_workflow(req.prompt, base_workflow)
  try:
    resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    prompt_id = result.get("prompt_id")
    if not prompt_id:
      logger.warning("No prompt_id from ComfyUI!")
      return {"status": "error", "message": "No prompt_id from ComfyUI!", "echo": req.prompt}
  except Exception as e:
    logger.error("Error reaching ComfyUI: %s", e)
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
  logger.info("img2img request received with prompt: '%s'", req.prompt)
  try:
    image_data = base64.b64decode(req.image_data)
  except Exception as e:
    logger.error("Error decoding img2img image: %s", e)
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
    logger.info("Image uploaded to ComfyUI: %s", upload_result)
  except Exception as e:
    logger.error("Error uploading img2img image to ComfyUI: %s", e)
    return {"status": "error", "message": f"Error uploading image to ComfyUI: {e}", "echo": req.prompt}
  base_workflow = load_workflow(IMG2IMG_WORKFLOW_PATH)
  try:
    payload = build_img2img_workflow(req.prompt, image_filename, base_workflow)
  except Exception as e:
    logger.error("Error building img2img workflow: %s", e)
    return {"status": "error", "message": f"Error building workflow: {e}", "echo": req.prompt}
  try:
    resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    prompt_id = result.get("prompt_id")
    if not prompt_id:
      logger.warning("No prompt_id from ComfyUI for img2img!")
      return {"status": "error", "message": "No prompt_id from ComfyUI!", "echo": req.prompt}
  except Exception as e:
    logger.error("Error reaching ComfyUI for img2img: %s", e)
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
  logger.info("img2vid request received")
  try:
    image_data = base64.b64decode(req.image_data)
  except Exception as e:
    logger.error("Error decoding img2vid image: %s", e)
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
    logger.info("Image uploaded for img2vid: %s", upload_result)
  except Exception as e:
    logger.error("Error uploading img2vid image to ComfyUI: %s", e)
    return {"status": "error", "message": f"Error uploading image to ComfyUI: {e}"}
  base_workflow = load_workflow(IMG2VID_WORKFLOW_PATH)
  try:
    payload = build_img2vid_workflow(image_filename, base_workflow)
  except Exception as e:
    logger.error("Error building img2vid workflow: %s", e)
    return {"status": "error", "message": f"Error building workflow: {e}"}
  try:
    resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    prompt_id = result.get("prompt_id")
    if not prompt_id:
      logger.warning("No prompt_id from ComfyUI for img2vid!")
      return {"status": "error", "message": "No prompt_id from ComfyUI!"}
  except Exception as e:
    logger.error("Error reaching ComfyUI for img2vid: %s", e)
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

def wait_for_execution_via_websocket(prompt_id: str, client_id: str, timeout: int = WS_IMAGE_TIMEOUT):
  """Wait for ComfyUI execution completion using WebSocket (event-driven, no polling).
  
  This is more efficient than polling because:
  1. No wasted HTTP requests
  2. Immediate notification when execution completes
  3. Real-time progress tracking possible
  
  Args:
    prompt_id: The prompt ID to wait for
    client_id: The client ID used when queueing the prompt
    timeout: Maximum time to wait for execution in seconds
    
  Returns:
    True if execution completed successfully, False otherwise
  """
  ws = None
  try:
    ws_url = f"{COMFYUI_WS_URL}?clientId={client_id}"
    logger.info("Connecting to ComfyUI WebSocket at %s", ws_url)
    ws = websocket.create_connection(ws_url, timeout=WS_CONNECT_TIMEOUT)
    ws.settimeout(WS_RECV_TIMEOUT)  # Set recv timeout to avoid blocking
    
    start_time = time.time()
    while True:
      elapsed = time.time() - start_time
      if elapsed > timeout:
        logger.warning("WebSocket timeout after %ss waiting for prompt %s", timeout, prompt_id)
        return False
      
      try:
        message = ws.recv()
        if isinstance(message, str):
          data = json.loads(message)
          msg_type = data.get("type")
          msg_data = data.get("data", {})
          
          if msg_type == "executing":
            current_node = msg_data.get("node")
            current_prompt_id = msg_data.get("prompt_id")
            
            # When node is None and prompt_id matches, execution is complete
            if current_node is None and current_prompt_id == prompt_id:
              logger.info("Execution completed for prompt %s (took %.1fs)", prompt_id, elapsed)
              return True
            elif current_prompt_id == prompt_id:
              logger.debug("Executing node %s for prompt %s", current_node, prompt_id)
              
          elif msg_type == "execution_error":
            logger.error("Execution error for prompt %s: %s", prompt_id, msg_data)
            return False
            
          elif msg_type == "execution_interrupted":
            logger.warning("Execution interrupted for prompt %s", prompt_id)
            return False
            
      except websocket.WebSocketTimeoutException:
        # Timeout on recv - check if total timeout exceeded, then continue waiting
        continue
        
  except websocket.WebSocketException as e:
    logger.error("WebSocket error while waiting for prompt %s: %s", prompt_id, e)
    return False
  except Exception as e:
    logger.error("Unexpected error in WebSocket wait for prompt %s: %s", prompt_id, e)
    return False
  finally:
    if ws:
      try:
        ws.close()
      except Exception:
        pass

def get_output_from_history(prompt_id: str, output_type: str = "images"):
  """Fetch outputs from ComfyUI history after execution completes.
  
  Args:
    prompt_id: The prompt ID to fetch results for
    output_type: Type of output to fetch ("images" or "gifs" for videos)
    
  Returns:
    URL to the output file or None if not found
  """
  try:
    hist_resp = requests.get(f"{COMFYUI_API}/history/{prompt_id}", timeout=10)
    if hist_resp.status_code == 200:
      hist_json = hist_resp.json()
      data = hist_json.get(prompt_id)
      if data and "outputs" in data and data.get("status", {}).get("status_str") == "success":
        for node_output in data["outputs"].values():
          outputs = node_output.get(output_type, [])
          if outputs:
            output_info = outputs[0]
            if output_type == "images":
              url = f"{COMFYUI_API}/view?filename={output_info['filename']}&subfolder={output_info.get('subfolder', '')}"
            else:  # gifs/videos
              url = f"{COMFYUI_API}/view?filename={output_info['filename']}&subfolder={output_info.get('subfolder', '')}&type={output_info.get('type', 'output')}"
            logger.info("Found %s in /history: %s", output_type, url)
            return url
      else:
        logger.info("No finished outputs found in history for prompt %s", prompt_id)
    else:
      logger.warning("Could not fetch /history/%s, status %s", prompt_id, hist_resp.status_code)
  except Exception as e:
    logger.error("Error fetching history for prompt %s: %s", prompt_id, e)
  return None

def wait_for_image_generation(prompt_id: str, client_id: str = None):
  """Wait for image generation using WebSocket (event-driven).
  
  Uses WebSocket to receive real-time execution updates from ComfyUI,
  eliminating the need for polling. Falls back to history check if 
  WebSocket fails.
  
  Args:
    prompt_id: The prompt ID to wait for
    client_id: The client ID used when queueing (optional, creates new if not provided)
  """
  if client_id is None:
    client_id = str(uuid.uuid4())
    
  # Try WebSocket-based wait first (more efficient)
  if wait_for_execution_via_websocket(prompt_id, client_id, timeout=WS_IMAGE_TIMEOUT):
    return get_output_from_history(prompt_id, "images")
  
  # Fallback: check history directly (execution might have completed before we connected)
  logger.info("WebSocket wait unsuccessful, checking history directly...")
  return get_output_from_history(prompt_id, "images")

def wait_for_video_generation(prompt_id: str, client_id: str = None):
  """Wait for video generation using WebSocket with extended timeout.
  
  Videos take much longer to generate than images (10+ minutes),
  so we use a longer timeout. Uses WebSocket for efficient event-driven
  waiting instead of polling.
  
  Args:
    prompt_id: The prompt ID to wait for
    client_id: The client ID used when queueing (optional, creates new if not provided)
  """
  if client_id is None:
    client_id = str(uuid.uuid4())
  
  logger.info("Waiting for video generation via WebSocket (timeout: %ss)", WS_VIDEO_TIMEOUT)
  
  # Try WebSocket-based wait (more efficient)
  if wait_for_execution_via_websocket(prompt_id, client_id, timeout=WS_VIDEO_TIMEOUT):
    return get_output_from_history(prompt_id, "gifs")
  
  # Fallback: check history directly
  logger.info("WebSocket wait unsuccessful, checking history directly...")
  return get_output_from_history(prompt_id, "gifs")

if __name__ == "__main__":
  import uvicorn
  logger.info("🏰 Comfynaut API Server starting...")
  logger.info("📡 ComfyUI connection: %s (WebSocket: %s)", COMFYUI_API, COMFYUI_WS_URL)
  logger.info("🌐 API server listening on http://0.0.0.0:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)
