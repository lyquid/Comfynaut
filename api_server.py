# 🏰 api_server.py - Comfynaut Pirate-Ninja Portal
# Now properly POSTs a "prompt" root-key to ComfyUI API!

# Import necessary libraries
from fastapi import FastAPI  # FastAPI framework for building APIs
from pydantic import BaseModel  # For data validation and parsing
import requests  # For making HTTP requests
import os  # For interacting with the operating system
import json  # For handling JSON data
import time  # For time-related operations
import copy  # For creating deep copies of objects

# Initialize FastAPI application
app = FastAPI()

# Define constants for workflow paths and API endpoints
WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "workflows")  # Directory containing workflow files
DEFAULT_WORKFLOW_PATH = os.path.join(WORKFLOWS_DIR, "text2img_LORA.json")  # Default workflow file path
COMFYUI_API = "http://127.0.0.1:8188"  # ComfyUI API endpoint
POSITIVE_PROMPT_NODE_ID = "16"  # Node ID for positive prompt in default workflow
PROMPT_HELPERS = ", high quality, masterpiece, best quality, 8k"  # Additional prompt helpers

# Define the request model for the API
class DreamRequest(BaseModel):
  prompt: str  # The prompt text provided by the user

# Function to load a workflow from a file
def load_workflow(path=DEFAULT_WORKFLOW_PATH):
  """
  Load the base (flat dict) ComfyUI API workflow.
  Parameters:
    path (str): Path to the workflow file.
  Returns:
    dict: The loaded workflow as a dictionary.
  """
  with open(path, "r") as f:
    return json.load(f)  # Returns a dictionary representation of the workflow

# Function to build a workflow with the user's prompt
def build_workflow(prompt: str, base_workflow=None):
  """
  Injects the user's prompt into the 'positive' node ('16' in default_api.json).
  Parameters:
    prompt (str): The user's input prompt.
    base_workflow (dict, optional): The base workflow to modify. Defaults to None.
  Returns:
    dict: A dictionary containing the modified workflow wrapped in a "prompt" key.
  """
  if base_workflow is None:
    base_workflow = load_workflow()
  workflow = copy.deepcopy(base_workflow)  # Create a deep copy to avoid mutating the original
  if POSITIVE_PROMPT_NODE_ID in workflow:
    workflow[POSITIVE_PROMPT_NODE_ID]["inputs"]["text"] = prompt + PROMPT_HELPERS  # Update the prompt text
  else:
    raise ValueError("Could not find node " + POSITIVE_PROMPT_NODE_ID + " for positive prompt in workflow!")
  if "3" in workflow:
    workflow["3"]["inputs"]["seed"] = int(time.time()) % 999999999  # Add a random seed
  return {"prompt": workflow}  # Wrap the workflow in a "prompt" key

# Define the POST endpoint to receive a dream request
@app.post("/dream")
async def receive_dream(req: DreamRequest):
  """
  Handle the dream request by injecting the prompt into the workflow and interacting with the ComfyUI API.
  Parameters:
    req (DreamRequest): The request object containing the user's prompt.
  Returns:
    dict: The response containing the status, prompt echo, and image URL or error message.
  """
  print(f"✨ Prompt received: '{req.prompt}'")
  base_workflow = load_workflow()  # Load the base workflow
  payload = build_workflow(req.prompt, base_workflow)  # Build the workflow with the user's prompt
  try:
    resp = requests.post(f"{COMFYUI_API}/prompt", json=payload, timeout=10)  # Send the workflow to the API
    resp.raise_for_status()
    result = resp.json()
    prompt_id = result.get("prompt_id", None)  # Extract the prompt ID from the response
    if not prompt_id:
      return {"status": "error", "message": "No prompt_id from ComfyUI!", "echo": req.prompt}
  except Exception as e:
    return {"status": "error", "message": f"Error reaching ComfyUI: {e}", "echo": req.prompt}

  # Poll the API for the result
  image_url = None
  for _ in range(60):  # Wait up to 60 seconds
    try:
      queue_resp = requests.get(f"{COMFYUI_API}/queue")
      if queue_resp.status_code == 200:
        queue_data = queue_resp.json()
        if isinstance(queue_data, list):
          queue_items = queue_data  # Handle list response
        else:
          queue_items = queue_data.get("queue_running", []) + queue_data.get("queue_done", [])  # Handle dict response
        for item in queue_items:
          if isinstance(item, dict) and item.get("prompt_id") == prompt_id and "outputs" in item:
            outputs = item["outputs"]
            if outputs:
              for node_output in outputs.values():
                images = node_output.get("images", [])
                if images:
                  imginfo = images[0]
                  image_url = f"{COMFYUI_API}/view?filename={imginfo['filename']}&subfolder={imginfo['subfolder']}"
                  break
        if image_url:
          break
    except Exception as e:
      print("Polling queue error:", e)
    time.sleep(2)  # Wait before retrying

  # Return the result
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
      "message": "Arrr, no image from ComfyUI—waited 60 seconds and got only goblins. Try again?"
    }

# Define the root endpoint
@app.get("/")
async def root():
  """
  Root endpoint to welcome users to the API.
  Returns:
    dict: A welcome message.
  """
  return {"message": "Welcome to Comfynaut GPU Wizardry Portal, now speaking true ComfyUI 'prompt' dialect!"}

# Entry point for running the application
if __name__ == "__main__":
  import uvicorn
  print("🧙‍♂️ Portals open on http://localhost:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)