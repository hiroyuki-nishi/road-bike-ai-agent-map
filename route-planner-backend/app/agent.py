import logging
from typing import List, Dict, Any, TypedDict, Sequence, Union, cast, Optional
import json
from logging import getLogger


from langgraph.graph import StateGraph
from pprint import pprint
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.models import RouteRequest, RouteResponse, RoutePoint
# from app.models import RouteRequest, RouteResponse, RoutePoint
import googlemaps
from googlemaps.client import Client as GoogleMapsClient
from googlemaps import geocoding, directions

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

class RouteAgent:
    def __init__(self, openai_api_key: str, google_maps_api_key: str):
        self.openai_api_key = openai_api_key
        self.google_maps_api_key = google_maps_api_key
        self.llm = ChatOpenAI(api_key=openai_api_key)
        self.gmaps: GoogleMapsClient = googlemaps.Client(key=google_maps_api_key)

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
            app = self._create_workflow()
            initial_state = {
                "prompt": request.prompt,
                "start_location": {},
                "constraints": {},
                "suggested_routes": [],
                "extracted_locations": [],
                "route_details": [],
                "errors": []
            }
            final_state = app.invoke(initial_state)
            print("---------debug1--------")
            pprint(final_state)
            return self.convert_to_route_response(route_data=final_state)
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            return RouteResponse(
                routes=[],
                distances=[],
                descriptions=[]
            )


    def _create_workflow(self):
        """Create a LangGraph workflow for route planning.
        
        Returns:
            A compiled LangGraph workflow for processing route requests.
        """
        # Define state types
        class RouteState(TypedDict):
            prompt: str
            start_location: dict
            constraints: dict
            suggested_routes: list
            extracted_locations: list
            route_details: list
            errors: list
            
        # Create the workflow graph
        workflow = StateGraph(RouteState)

        # Create nodes for the workflow
        def parse_route_request(state: RouteState) -> RouteState:
            """Parse the initial route request using LLM."""
            try:
                prompt_template = ChatPromptTemplate.from_template("""
あなたは自転車ルートプランナーです。以下の入力に基づいて、自転車での走行に適したルートを提案してください。

ユーザーのルート候補の入力: {user_input}

入力から出発地点を抽出し、その周辺の自転車で走りやすいルートを1つ提案してください。

以下の形式でJSONを返してください（必ず有効なJSONフォーマットで）:
{{
    "start_location": {{
        "name": {start_location_name}
    }},
    "constraints": {{
        "radius_km": 100,
        "route_count": 3
    }},
    "suggested_routes": [
        {{
            "direction": "方角（例：北東）",
            "waypoints": [
                {{
                    "name": "実在する経由地点の名前",
                    "description": "場所の説明や特徴"
                }}
            ],
            "description": "ルートの詳細な説明（距離、特徴、見所など）"
        }}
    ]
}}

注意：
1. 出発地点は必ずユーザー入力から抽出してください
2. 経由地点は必ず実在する場所を指定してください
3. 各ルートは100km圏内に収まるようにしてください
4. 説明は具体的に記載してください
""")
                chain = prompt_template | self.llm
                llm_response = chain.invoke({"user_input": state["prompt"], "start_location_name": "樟葉駅"})
                import json
                try:
                    route_data = json.loads(str(llm_response.content))
                except json.JSONDecodeError as e:
                    return {**state, "errors": state.get("errors", []) + [f"Failed to parse LLM response: {e}"]}
                
                return {
                    **state,
                    "start_location": route_data["start_location"],
                    "constraints": route_data["constraints"],
                    "suggested_routes": route_data["suggested_routes"]
                }
            except Exception as e:
                return {**state, "errors": state.get("errors", []) + [str(e)]}

        def extract_locations(state: RouteState) -> RouteState:
            """Extract coordinates for all locations."""
            if state.get("errors"):
                return state

            try:
                # Extract start location
                # Use Google Maps client for geocoding
                try:
                    # Use geocoding module function
                    start_result = geocoding.geocode(self.gmaps, state["start_location"]["name"])
                    if not start_result:
                        raise ValueError(f"Could not find coordinates for {state['start_location']['name']}")
                    
                    location = start_result[0]['geometry']['location']
                    start_location = {
                        "name": state["start_location"]["name"],
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "type": "start"
                    }
                except Exception as e:
                    print(f"Error geocoding start location: {e}")
                    raise
                
                # Extract waypoint locations
                extracted_locations = [start_location]
                for route in state["suggested_routes"]:
                    route_locations = []
                    for point in route["waypoints"]:
                        try:
                            # Use geocoding module function
                            result = geocoding.geocode(self.gmaps, point["name"])
                            if result:
                                location_data = result[0]['geometry']['location']
                                location = {
                                    "name": point["name"],
                                    "lat": location_data['lat'],
                                    "lng": location_data['lng'],
                                    "type": "waypoint"
                                }
                                route_locations.append(location)
                        except Exception as e:
                            print(f"Error geocoding waypoint {point['name']}: {e}")
                            continue
                            route_locations.append(location)
                    extracted_locations.append({
                        "route_index": len(extracted_locations) - 1,
                        "locations": route_locations
                    })
                
                return {**state, "extracted_locations": extracted_locations}
            except Exception as e:
                return {**state, "errors": state.get("errors", []) + [str(e)]}

        def get_route_details(state: RouteState) -> RouteState:
            """Get route details from Google Maps."""
            if state.get("errors"):
                return state

            try:
                route_details = []
                start_point = state["extracted_locations"][0]  # Start location is directly in the list
                
                for route_data in state["extracted_locations"][1:]:
                    if not route_data["locations"]:
                        continue
                        
                    try:
                        # Use Google Maps client for directions
                        try:
                            origin = f"{start_point['lat']},{start_point['lng']}"
                            destination = f"{route_data['locations'][-1]['lat']},{route_data['locations'][-1]['lng']}"
                            waypoints = [f"{p['lat']},{p['lng']}" for p in route_data['locations'][:-1]]
                            
                            # Use directions module function
                            route_directions = directions.directions(
                                self.gmaps,
                                origin=origin,
                                destination=destination,
                                waypoints=waypoints if waypoints else None,
                                mode="bicycling",
                                alternatives=False
                            )

                            if not route_directions:
                                raise ValueError("No route found")
                                
                        except Exception as e:
                            print(f"Error getting directions: {e}")
                            raise
                        
                        if route_directions:
                            route = route_directions[0] if isinstance(route_directions, list) else route_directions
                            distance = sum(leg.get("distance", {}).get("value", 0) for leg in route.get("legs", [])) / 1000
                            duration = sum(leg.get("duration", {}).get("value", 0) for leg in route.get("legs", []))
                            
                            route_details.append({
                                "distance": distance,
                                "duration": duration,
                                "points": [start_point] + route_data["locations"],
                                "description": state["suggested_routes"][route_data["route_index"]]["description"]
                            })
                    except Exception as e:
                        print(f"Error getting directions for route {route_data['route_index']}: {e}")
                        # Calculate straight-line distance as fallback
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
                        points = [start_point] + route_data["locations"]
                        total_distance = sum(
                            haversine_distance(
                                points[i]["lat"], points[i]["lng"],
                                points[i+1]["lat"], points[i+1]["lng"]
                            )
                            for i in range(len(points)-1)
                        )
                        
                        route_details.append({
                            "distance": total_distance,
                            "duration": int(total_distance * 300),  # Rough estimate: 20 km/h average speed
                            "points": points,
                            "description": state["suggested_routes"][route_data["route_index"]]["description"]
                        })
                
                return {**state, "route_details": route_details}
            except Exception as e:
                return {**state, "errors": state.get("errors", []) + [str(e)]}

        # Create the workflow graph
        workflow = StateGraph(RouteState)
        
        # Add nodes
        workflow.add_node("parse_request", parse_route_request)
        workflow.add_node("extract_locations", extract_locations)
        workflow.add_node("get_route_details", get_route_details)
        
        # Define edges
        workflow.add_edge("parse_request", "extract_locations")
        workflow.add_edge("extract_locations", "get_route_details")
        
        # Set entry and exit points
        # Set the entry point and exit point
        workflow = workflow.set_entry_point("parse_request")
        workflow = workflow.set_finish_point("get_route_details")
        
        # Return the compiled workflow
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
