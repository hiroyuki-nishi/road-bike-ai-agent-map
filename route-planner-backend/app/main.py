from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
import os
from dotenv import load_dotenv

from app.models import RouteRequest, RouteResponse
from app.agent import RouteAgent

load_dotenv()

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@lru_cache()
def get_route_agent() -> RouteAgent:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not openai_api_key or not google_maps_api_key:
        raise ValueError("Missing required API keys in .env file")
    return RouteAgent(openai_api_key, google_maps_api_key)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/api/route", response_model=RouteResponse)
async def get_route(request: RouteRequest, agent: RouteAgent = Depends(get_route_agent)):
    """
    Get route suggestions based on the input prompt.
    Example prompt: "現在地点：樟葉駅より100KM圏内のロードバイクが走りやすいルート候補を３つほどGoogleMapに表示してください。"
    """
    return await agent.process_route_request(request)
