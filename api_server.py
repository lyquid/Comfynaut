# 🏰 api_server.py - Comfynaut Pirate-Ninja Portal
# Refactored by Gandalf the Pirate-Ninja, Slayer of NodeID Monsters!
#
# This file implements the FastAPI backend for Comfynaut.
# It exposes endpoints for text-to-image, image-to-image, and image-to-video generation using ComfyUI workflows.
# The server communicates with ComfyUI via HTTP and WebSocket for efficient, real-time execution tracking.
#
# Key features:
# - Dynamic workflow loading and node identification
# - Robust error handling and logging
# - WebSocket-based event-driven execution (no polling)
# - Endpoints for /dream, /img2img, /img2vid
# - Utility functions for workflow manipulation and output retrieval

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

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Logging setup for API server
logging.basicConfig(
  format="%(asctime)s - %(levelname)s - %(message)s",
  level=logging.INFO
)
logger = logging.getLogger("comfynaut.api")

# Workflow file paths
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
DEFAULT_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "basic_sdxl_t2i.json")
IMG2IMG_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "i2i - CyberRealistic Pony.json")
IMG2VID_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "i2v - WAN 2.2 Smooth Workflow v2.0.json")

# ComfyUI connection settings (configurable for remote/local)
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1:8188")
COMFYUI_API = f"http://{COMFYUI_HOST}"
COMFYUI_WS_URL = f"ws://{COMFYUI_HOST}/ws"

PROMPT_HELPERS = ", high quality, masterpiece, best quality, 8k"

# WebSocket settings for real-time communication
WS_CONNECT_TIMEOUT = 10  # WebSocket connection timeout in seconds
WS_RECV_TIMEOUT = 5      # WebSocket receive timeout per message
WS_IMAGE_TIMEOUT = 60    # Total timeout for image generation
WS_VIDEO_TIMEOUT = 900   # Total timeout for video generation (15 min)

# Video encoder flush delay (in seconds)
# Workaround for VHS_VideoCombine encoder flush issue where last frame is sometimes dropped
ENCODER_FLUSH_DELAY = 2  # Delay in seconds after video generation to ensure encoder flushes last frame

# Request models for API endpoints
class DreamRequest(BaseModel):
  prompt: str
  workflow: str = None

class Img2ImgRequest(BaseModel):
  prompt: str
  image_data: str  # Base64 encoded image

class Img2VidRequest(BaseModel):
  image_data: str  # Base64 encoded image
  prompt: str = ""  # Optional positive prompt for video generation

# Utility: Load a workflow JSON file with robust decoding and error handling
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

# Utility: Find the 'Positive Prompt' CLIPTextEncode node dynamically
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

# Utility: Find the node for loading the input image
def find_image_load_node(workflow):
  """Find the node for loading the input image (usually `LoadImage`)."""
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "LoadImage":
      return node_id
  raise ValueError("Could not find LoadImage node in workflow!")

# Utility: Find the KSampler node dynamically
def find_ksampler_node(workflow):
  """Find the KSampler node dynamically."""
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "KSampler":
      return node_id
  raise ValueError("Could not find KSampler node in workflow!")

# Utility: Find the Seed (rgthree) node for video generation workflows
def find_seed_node(workflow):
  """Find the Seed (rgthree) node for video generation workflows."""
  for node_id, node_data in workflow.items():
    if node_data.get("class_type") == "Seed (rgthree)":
      return node_id
  raise ValueError("Could not find Seed (rgthree) node in workflow!")

# Utility: Find the PrimitiveStringMultiline node for positive prompt in video workflows
def find_primitive_prompt_node(workflow):
  """Find the PrimitiveStringMultiline node used for positive prompt input.
  This is used in video generation workflows where the prompt is stored in a
  PrimitiveStringMultiline node with title 'Positive'.
  """
  for node_id, node_data in workflow.items():
    if isinstance(node_data, dict) and node_data.get("class_type") == "PrimitiveStringMultiline":
      title = node_data.get("_meta", {}).get("title", "").lower()
      if "positive" in title:
        return node_id
  return None

# Utility: Find the VHS_VideoCombine node for video output
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

# Build a text-to-image workflow with the given prompt
def build_workflow(prompt: str, base_workflow=None):
  """Build a text-to-image workflow with the given prompt."""
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

# Build an image-to-image workflow with the given prompt and input image
def build_img2img_workflow(prompt: str, image_filename: str, base_workflow=None):
  """Build an image-to-image workflow with the given prompt and input image."""
  if base_workflow is None:
    base_workflow = load_workflow(IMG2IMG_WORKFLOW_PATH)
  workflow = copy.deepcopy(base_workflow)
  # Find positive prompt node dynamically
  positive_prompt_node_id = find_positive_prompt_node(workflow)
  workflow[positive_prompt_node_id]["inputs"]["text"] = prompt + PROMPT_HELPERS
  # Find image load node dynamically
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

# Build an image-to-video workflow for WAN i2v
def build_img2vid_workflow(image_filename: str, prompt: str = "", base_workflow=None):
  """Build the image-to-video workflow for WAN i2v."""
  if base_workflow is None:
    base_workflow = load_workflow(IMG2VID_WORKFLOW_PATH)
  workflow = copy.deepcopy(base_workflow)
  # Find and update LoadImage node
  image_load_node_id = find_image_load_node(workflow)
  workflow[image_load_node_id]["inputs"]["image"] = image_filename
  # Find and update the positive prompt node (PrimitiveStringMultiline)
  prompt_node_id = find_primitive_prompt_node(workflow)
  if prompt_node_id:
    if prompt:
      workflow[prompt_node_id]["inputs"]["value"] = prompt
      logger.info("Set positive prompt in node %s: '%s'", prompt_node_id, prompt)
    else:
      logger.info("Prompt node %s found but no prompt provided, using workflow default", prompt_node_id)
  else:
    logger.warning("No PrimitiveStringMultiline 'Positive' node found in workflow")
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

# Endpoint: /dream - text-to-image generation
@app.post("/dream")
async def receive_dream(req: DreamRequest):
  logger.info("Prompt received: '%s'", req.prompt)
  workflow_path = DEFAULT_WORKFLOW_PATH
  if req.workflow:
    candidate_path = os.path.join(WORKFLOWS_DIR, req.workflow)
    # Normalize and ensure the candidate path stays within WORKFLOWS_DIR
    base_dir = os.path.abspath(os.path.normpath(WORKFLOWS_DIR))
    safe_candidate_path = os.path.abspath(os.path.normpath(candidate_path))
    if safe_candidate_path == base_dir or safe_candidate_path.startswith(base_dir + os.sep):
      if os.path.isfile(safe_candidate_path):
        workflow_path = safe_candidate_path
        logger.info("Using workflow: %s", req.workflow)
      else:
        logger.warning("Workflow file not found: %s, using default.", safe_candidate_path)
    else:
      logger.warning(
        "Rejected workflow path outside base directory: %s (base: %s)",
        safe_candidate_path,
        base_dir,
      )
  else:
    logger.info("No workflow specified, using default.")
  base_workflow = load_workflow(workflow_path)
  payload = build_workflow(req.prompt, base_workflow)
  # Generate client_id to track this request via WebSocket
  client_id = str(uuid.uuid4())
  payload["client_id"] = client_id
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
  image_url = wait_for_image_generation(prompt_id, client_id)
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

# Endpoint: /img2img - image-to-image generation
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
  # Generate client_id to track this request via WebSocket
  client_id = str(uuid.uuid4())
  payload["client_id"] = client_id
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
  image_url = wait_for_image_generation(prompt_id, client_id)
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

# Endpoint: /img2vid - image-to-video generation
@app.post("/img2vid")
async def receive_img2vid(req: Img2VidRequest):
  logger.info("img2vid request received with prompt: '%s'", req.prompt)
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
    payload = build_img2vid_workflow(image_filename, req.prompt, base_workflow)
  except Exception as e:
    logger.error("Error building img2vid workflow: %s", e)
    return {"status": "error", "message": f"Error building workflow: {e}"}
  # Generate client_id to track this request via WebSocket
  client_id = str(uuid.uuid4())
  payload["client_id"] = client_id
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
  # Wait for video generation with extended timeout and get both video and last frame
  outputs = wait_for_video_generation(prompt_id, client_id, include_last_frame=True)
  video_url = outputs.get("video_url")
  last_frame_url = outputs.get("last_frame_url")
  if video_url:
    response = {
      "status": "success",
      "video_url": video_url,
      "message": "🎬 Video conjured! Your moving masterpiece awaits at the video URL."
    }
    if last_frame_url:
      response["last_frame_url"] = last_frame_url
      response["message"] = "🎬 Video conjured! Your moving masterpiece and its last frame await."
    return response
  else:
    return {
      "status": "error",
      "message": "Arrr, no video from ComfyUI—the animation eluded us. Try again, brave wizard?"
    }

# Endpoint: / - root endpoint for health check
@app.get("/")
async def root():
  return {"message": "Welcome to Comfynaut GPU Wizardry Portal, now speaking true ComfyUI 'prompt' dialect!"}

# Utility: Wait for execution completion using WebSocket (event-driven, no polling)
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

# Utility: Fetch outputs from ComfyUI history after execution completes
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
        # Collect all outputs of the requested type from all nodes
        all_outputs = []
        for node_id, node_output in data["outputs"].items():
          outputs = node_output.get(output_type, [])
          if outputs:
            # Store each output with its node_id for potential debugging
            for output in outputs:
              all_outputs.append((node_id, output))
        
        # If we found outputs, use the LAST one (final processed output)
        # This ensures we get the final video from workflows with multiple VHS_VideoCombine nodes
        if all_outputs:
          node_id, output_info = all_outputs[-1]
          if output_type == "images":
            url = f"{COMFYUI_API}/view?filename={output_info['filename']}&subfolder={output_info.get('subfolder', '')}"
          else:  # gifs/videos
            url = f"{COMFYUI_API}/view?filename={output_info['filename']}&subfolder={output_info.get('subfolder', '')}&type={output_info.get('type', 'output')}"
          logger.info("Found %s in /history from node %s: %s", output_type, node_id, url)
          return url
      else:
        logger.info("No finished outputs found in history for prompt %s", prompt_id)
    else:
      logger.warning("Could not fetch /history/%s, status %s", prompt_id, hist_resp.status_code)
  except Exception as e:
    logger.error("Error fetching history for prompt %s: %s", prompt_id, e)
  return None

# Utility: Fetch all outputs from ComfyUI history after execution completes
def get_all_outputs_from_history(prompt_id: str):
  """Fetch all outputs (images and videos) from ComfyUI history after execution completes.
  Args:
    prompt_id: The prompt ID to fetch results for
  Returns:
    Dictionary with 'images' and 'gifs' keys, each containing a list of URLs
  """
  result = {"images": [], "gifs": []}
  try:
    hist_resp = requests.get(f"{COMFYUI_API}/history/{prompt_id}", timeout=10)
    if hist_resp.status_code == 200:
      hist_json = hist_resp.json()
      data = hist_json.get(prompt_id)
      if data and "outputs" in data and data.get("status", {}).get("status_str") == "success":
        for node_output in data["outputs"].values():
          # Collect images
          for img_info in node_output.get("images", []):
            url = f"{COMFYUI_API}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}"
            result["images"].append(url)
            logger.info("Found image in /history: %s", url)
          # Collect videos/gifs
          for gif_info in node_output.get("gifs", []):
            url = f"{COMFYUI_API}/view?filename={gif_info['filename']}&subfolder={gif_info.get('subfolder', '')}&type={gif_info.get('type', 'output')}"
            result["gifs"].append(url)
            logger.info("Found video/gif in /history: %s", url)
      else:
        logger.info("No finished outputs found in history for prompt %s", prompt_id)
    else:
      logger.warning("Could not fetch /history/%s, status %s", prompt_id, hist_resp.status_code)
  except Exception as e:
    logger.error("Error fetching history for prompt %s: %s", prompt_id, e)
  return result

# Utility: Wait for image generation using WebSocket (event-driven)
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

# Utility: Extract video and last frame URLs from history outputs
def extract_video_and_frame_urls(prompt_id: str):
  """Extract video URL and last frame URL from ComfyUI history outputs.
  Args:
    prompt_id: The prompt ID to fetch results for
  Returns:
    Dictionary with 'video_url' and 'last_frame_url' keys (may be None if not found)
  """
  all_outputs = get_all_outputs_from_history(prompt_id)
  result = {}
  
  # Get the last video from gifs list (check for non-empty list)
  gifs = all_outputs.get("gifs", [])
  result["video_url"] = gifs[-1] if gifs else None
  
  # Get the last image (last frame) from images list (check for non-empty list)
  images = all_outputs.get("images", [])
  result["last_frame_url"] = images[-1] if images else None
  
  return result

# Utility: Wait for video generation using WebSocket with extended timeout
def wait_for_video_generation(prompt_id: str, client_id: str = None, include_last_frame: bool = False):
  """Wait for video generation using WebSocket with extended timeout.
  Videos take much longer to generate than images (10+ minutes),
  so we use a longer timeout. Uses WebSocket for efficient event-driven
  waiting instead of polling.
  Args:
    prompt_id: The prompt ID to wait for
    client_id: The client ID used when queueing (optional, creates new if not provided)
    include_last_frame: If True, returns dict with both video_url and last_frame_url
  Returns:
    If include_last_frame is False: URL to video or None
    If include_last_frame is True: dict with 'video_url' and 'last_frame_url' keys
  """
  if client_id is None:
    client_id = str(uuid.uuid4())
  logger.info("Waiting for video generation via WebSocket (timeout: %ss)", WS_VIDEO_TIMEOUT)
  # Try WebSocket-based wait (more efficient)
  if wait_for_execution_via_websocket(prompt_id, client_id, timeout=WS_VIDEO_TIMEOUT):
    # Add a short delay after video generation completes to ensure the encoder
    # properly flushes the last frame. This is a workaround for VHS_VideoCombine
    # encoder flush issues where the last frame is sometimes dropped.
    # Note: This blocks the calling thread but ensures video file is complete.
    logger.info("Video generation completed, waiting %ss for encoder to flush...", ENCODER_FLUSH_DELAY)
    time.sleep(ENCODER_FLUSH_DELAY)
    
    # Handle include_last_frame parameter
    if include_last_frame:
      return extract_video_and_frame_urls(prompt_id)
    else:
      # Backward compatibility: return just the video URL string
      return get_output_from_history(prompt_id, "gifs")
  
  # Fallback: check history directly
  logger.info("WebSocket wait unsuccessful, checking history directly...")
  
  if include_last_frame:
    return extract_video_and_frame_urls(prompt_id)
  else:
    # Backward compatibility: return just the video URL string
    return get_output_from_history(prompt_id, "gifs")

# Entry point for running the API server directly
if __name__ == "__main__":
  import uvicorn
  logger.info("🏰 Comfynaut API Server starting...")
  logger.info("📡 ComfyUI connection: %s (WebSocket: %s)", COMFYUI_API, COMFYUI_WS_URL)
  logger.info("🌐 API server listening on http://0.0.0.0:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)
