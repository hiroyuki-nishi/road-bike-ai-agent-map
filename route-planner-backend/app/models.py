from typing import List, TypedDict, Optional

from pydantic import BaseModel


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

class RouteState(TypedDict):
    prompt: str
    start_location: dict
    constraints: dict
    suggested_routes: Optional[list]
    extracted_locations: Optional[list]
    route_details: Optional[list]
    errors: Optional[list]
