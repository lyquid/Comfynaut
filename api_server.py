# 🏰 api_server.py - Comfynaut FastAPI Portal
# ---------------------------------------------------------------------------
# "Speak friend, and enter!" — Ancient Door of Art Mines of Moria

from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

# The shape of dream payloads arriving from the Telegram minion
class DreamRequest(BaseModel):
  prompt: str

@app.post("/dream")
async def receive_dream(req: DreamRequest):
  # For now, just log and respond—no wizard-level painting yet
  print(f"✨ Prompt received: '{req.prompt}'")
  return {
    "status": "received",
    "echo": req.prompt,
    "message": "Hold fast, Captain! The dream machine heard thee."
  }

@app.get("/")
async def root():
  return {"message": "Welcome to Comfynaut GPU Wizardry Portal!"}

if __name__ == "__main__":
  import uvicorn
  print("🧙‍♂️ Portals open! Awaiting dreamers on http://localhost:8000/")
  uvicorn.run("api_server:app", host="0.0.0.0", port=8000)