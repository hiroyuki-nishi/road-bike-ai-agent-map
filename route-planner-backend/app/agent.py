import json
import logging
from logging import getLogger
from pprint import pprint
from typing import List, Dict, Any

import googlemaps
from googlemaps import geocoding, directions
from googlemaps.client import Client as GoogleMapsClient
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph

from app.models import RouteRequest, RouteResponse, RoutePoint, RouteState
from app.nodes import Nodes

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

class RouteAgent:
    def __init__(self, openai_api_key: str, google_maps_api_key: str):
        self.openai_api_key = openai_api_key
        self.google_maps_api_key = google_maps_api_key
        self.llm = ChatOpenAI(api_key=openai_api_key)
        self.gmaps: GoogleMapsClient = googlemaps.Client(key=google_maps_api_key)
        self.nodes = Nodes(llm=self.llm, gmaps=self.gmaps)

    @staticmethod
    def convert_to_route_response(route_data: Dict[str, Any]) -> RouteResponse:
        """Convert route details to response format."""
        print("---------debug2--------")
        routes = []
        distances = []
        descriptions = []

        for route_detail in route_data["route_details"]:
            route_points = [
                RoutePoint(
                    lat=point["lat"],
                    lng=point["lng"],
                    name=point["name"]
                )
                for point in route_detail["points"]
            ]
            routes.append(route_points)
            distances.append(route_detail["distance"])
            descriptions.append(route_detail["description"])

        print("---------debug3--------")
        pprint(routes)

        return RouteResponse(
            routes=routes,
            distances=distances,
            descriptions=descriptions
        )

    async def process_route_request(self, request: RouteRequest) -> RouteResponse:
        """Process a route request and return cycling route suggestions using LangGraph workflow."""
        pprint(f"prompt: {request.prompt}")
        try:
            workflow = self.create_workflow()
            initial_state = {
                "prompt": request.prompt,
                "start_location": {},
                "constraints": {},
                "suggested_routes": [],
                "extracted_locations": [],
                "route_details": [],
                "errors": []
            }
            final_state = workflow.invoke(initial_state)
            print("---------debug1--------")
            pprint(final_state)
            return self.convert_to_route_response(route_data=final_state)
        except Exception as e:
            print(f"error: {e}")
            logger.error(f"Workflow execution error: {e}")
            return RouteResponse(
                routes=[],
                distances=[],
                descriptions=[]
            )


    def create_workflow(self):
        """Create a LangGraph workflow for route planning.
        
        Returns:
            A compiled LangGraph workflow for processing route requests.
        """
        workflow = StateGraph(RouteState)

        # Create the workflow graph
        workflow = StateGraph(RouteState)
        
        workflow.add_node("parse_request", self.nodes.parse_route_request)
        workflow.add_node("extract_locations", self.nodes.extract_locations)
        workflow.add_node("get_route_details", self.nodes.get_route_details)
        
        workflow.add_edge("parse_request", "extract_locations")
        workflow.add_edge("extract_locations", "get_route_details")
        
        workflow = workflow.set_entry_point("parse_request")
        workflow = workflow.set_finish_point("get_route_details")
        return workflow.compile()

    async def _extract_locations(self, text: str) -> List[Dict[str, Any]]:
        """Extract location coordinates using LLM and Google Maps API."""
        if not text:
            return []
        prompt_template = ChatPromptTemplate.from_template("""
場所の名前から正確な住所を抽出してください。

場所: {location}

以下の形式でJSONを返してください:
{
    "address": "完全な住所（都道府県から）"
}
""")
        
        # Get full address using LLM
        chain = prompt_template | self.llm
        llm_response = await chain.ainvoke({"location": text})
        try:
            address_data = json.loads(str(llm_response.content))
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response: {e}")
            return []
        
        try:
            # Use geocoding module function
            geocode_result = geocoding.geocode(self.gmaps, address_data["address"])
            if geocode_result:
                location = geocode_result[0]["geometry"]["location"]
                return [{
                    "name": text,
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "type": "waypoint"
                }]
        except Exception as e:
            print(f"Error geocoding {text}: {e}")
            return []
        
        return []

    async def _get_route_from_google_maps(self, points: List[RoutePoint]) -> Dict[str, Any]:
        """Get cycling route information from Google Maps Directions API."""
        try:
            # Convert points to waypoints format
            waypoints = points[1:-1]  # Exclude start and end points
            
            # Request directions using directions module function
            route_directions = directions.directions(
                self.gmaps,
                origin=f"{points[0].lat},{points[0].lng}",
                destination=f"{points[-1].lat},{points[-1].lng}",
                waypoints=[f"{p.lat},{p.lng}" for p in waypoints] if waypoints else None,
                mode="bicycling",
                alternatives=False
            )
            
            if route_directions:
                route = route_directions[0]
                # Convert distance from meters to kilometers
                distance = sum(leg["distance"]["value"] for leg in route["legs"]) / 1000
                duration = sum(leg["duration"]["value"] for leg in route["legs"])
                
                # Extract waypoints from route steps for more accurate path
                route_points = []
                for leg in route["legs"]:
                    for step in leg["steps"]:
                        route_points.append({
                            "lat": step["end_location"]["lat"],
                            "lng": step["end_location"]["lng"],
                            "name": step.get("html_instructions", ""),
                            "type": "waypoint"
                        })
                
                return {
                    "distance": distance,
                    "duration": duration,
                    "points": route_points
                }
        except Exception as e:
            print(f"Error getting directions: {e}")
        
        # Fallback: Calculate straight-line distances between points
        from math import radians, sin, cos, sqrt, atan2
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371  # Earth's radius in kilometers
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c

        # Calculate total distance through all points
        total_distance = sum(
            haversine_distance(
                points[i].lat, points[i].lng,
                points[i+1].lat, points[i+1].lng
            )
            for i in range(len(points)-1)
        )

        return {
            "distance": total_distance,
            "duration": int(total_distance * 300),  # Rough estimate: 20 km/h average speed
            "points": [point.dict() for point in points]
        }
