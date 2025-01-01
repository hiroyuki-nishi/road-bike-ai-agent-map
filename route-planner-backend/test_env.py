from app.main import get_route_agent

try:
    agent = get_route_agent()
    print("Environment variables loaded successfully!")
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
