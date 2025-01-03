import logging
from logging import getLogger
from pprint import pprint
from typing import Dict, Any

import googlemaps
from googlemaps.client import Client as GoogleMapsClient
from langchain_community.chat_models import ChatOpenAI
from langgraph.graph import StateGraph

from app.models import RouteRequest, RouteResponse, RoutePoint, RouteState
from app.nodes import Nodes

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)

class RouteAgent:
    def __init__(self, openai_api_key: str, google_maps_api_key: str):
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
