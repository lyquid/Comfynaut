# 🏰 api_server.py - Comfynaut FastAPI Portal, wielding JSON spellbooks with 2-space ninja tabs!
# -----------------------------------------------------------------------------
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
import json
import time
import copy

app = FastAPI()

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")
DEFAULT_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "default.json")
COMFYUI_API = "http://127.0.0.1:8188"

class DreamRequest(BaseModel):
  prompt: str

def load_workflow(path=DEFAULT_WORKFLOW_PATH):
  """
  Loads the ComfyUI workflow from disk.
  """
  with open(path, "r") as f:
    return json.load(f)

def build_workflow(prompt: str, base_workflow=None):
  """
  Create a workflow dict ready for ComfyUI, swapping in the user prompt.
  NOTE: You may need to adjust the "node_id" and input keys to match your exported workflow!
  """
  if base_workflow is None:
    base_workflow = load_workflow()
  workflow = copy.deepcopy(base_workflow)
  # Find node with "positive" input (naive approach: first one)
  for node in workflow.get("prompt", {}).values():
    if "positive" in node.get("inputs", {}):
      node["inputs"]["positive"] = prompt
    # Optionally: random seed (so every dream's unique as a Hobbit breakfast!)
    if "seed" in node.get("inputs", {}):
      node["inputs"]["seed"] = int(time.time()) % 999999999
  return workflow

@app.post("/dream")
async def receive_dream(req: DreamRequest):
  print(f"✨ Prompt received: '{req.prompt}'")
  # 1. Load & prep the workflow
  base_workflow = load_workflow()
  payload = build_workflow(req.prompt, base_workflow)
  # 2. Send to ComfyUI API
  try:
    resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    prompt_id = result.get("prompt_id", None)
    if not prompt_id:
      return {"status": "error", "message": "No prompt_id from ComfyUI!", "echo": req.prompt}
  except Exception as e:
    return {"status": "error", "message": f"Error reaching ComfyUI: {e}", "echo": req.prompt}

  # 3. Poll the queue for art!
  image_url = None
  for _ in range(60):  # wait up to 60s
    try:
      queue_resp = requests.get(f"{COMFYUI_API}/queue")
      if queue_resp.status_code == 200:
        queue_data = queue_resp.json()
        for item in queue_data.get("queue_running", []) + queue_data.get("queue_done", []):
          if item.get("prompt_id") == prompt_id and "outputs" in item:
            outputs = item["outputs"]
            if outputs:
              for node_output in outputs.values():
                images = node_output.get("images", [])
                if images:
                  # Take the first image path as the result
                  imginfo = images[0]
                  image_url = f"{COMFYUI_API}/view?filename={imginfo['filename']}&subfolder={imginfo['subfolder']}"
                  break
        if image_url:
          break
    except Exception as e:
      print("Polling queue error:", e)
    time.sleep(2)  # Wait before checking again

  # 4. Report results
  if image_url:
    return {
      "status": "success",
      "echo": req.prompt,
      "image_url": image_url,
      "message": "✨ Art conjured! See the attached image (URL only, for now)."
    }
  else:
    return {
      "status": "error",
      "echo": req.prompt,
      "message": "Ran out of wizarding patience waiting for ComfyUI image! Try again?",
    }

@app.get("/")
async def root():
  return {"message": "Welcome to Comfynaut GPU Wizardry Portal, with JSON-powered workflows!"}

if __name__ == "__main__":
  import uvicorn
  print("🧙‍♂️ Portals open on http://localhost:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)