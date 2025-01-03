from pydantic import BaseModel
from typing import List, Optional, Tuple

class RouteRequest(BaseModel):
    start_location_name: str = "樟葉駅"
    prompt: str

class RoutePoint(BaseModel):
    lat: float
    lng: float
    name: Optional[str] = None

class RouteResponse(BaseModel):
    routes: List[List[RoutePoint]]
    distances: List[float]  # Distance in kilometers for each route
    descriptions: List[str]  # Description of each route
