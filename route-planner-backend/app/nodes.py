import json
from pprint import pprint

from googlemaps import geocoding, directions
from langchain_core.prompts import ChatPromptTemplate

from app.models import RouteState


class Nodes:
    def __init__(self, llm, gmaps):
        self.llm = llm
        self.gmaps = gmaps


    def parse_route_request(self, state: RouteState) -> RouteState:
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
            try:
                print("---------debug4--------")
                pprint(llm_response)
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


    def extract_locations(self, state: RouteState) -> RouteState:
        print("---------debug5--------")
        print("extract_locations")
        """Extract coordinates for all locations."""
        if state.get("errors"):
            return state

        try:
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
                        # route_locations.append(location)
                extracted_locations.append({
                    "route_index": len(extracted_locations) - 1,
                    "locations": route_locations
                })

            return {**state, "extracted_locations": extracted_locations}
        except Exception as e:
            return {**state, "errors": state.get("errors", []) + [str(e)]}

    def get_route_details(self, state: RouteState) -> RouteState:
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
                    try:
                        origin = f"{start_point['lat']},{start_point['lng']}"
                        destination = f"{route_data['locations'][-1]['lat']},{route_data['locations'][-1]['lng']}"
                        waypoints = [f"{p['lat']},{p['lng']}" for p in route_data['locations'][:-1]]

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
