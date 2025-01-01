# saito_devin

# Route Planner Application

This application is a fullstack route planner that uses AI to generate cycling routes based on natural language prompts. It consists of a FastAPI backend with LangGraph for AI processing and a React frontend with Google Maps integration.

## Backend Setup

### Prerequisites
- Python 3.12 or higher
- Poetry (Python package manager)

### Installation

1. Clone the repository
2. Navigate to the backend directory:
```bash
cd route-planner-backend
```

3. Install dependencies using Poetry:
```bash
poetry install
```

4. Create a `.env` file in the backend directory with the following content:
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Starting the Backend Server

Run the development server using Poetry:
```bash
poetry run fastapi dev app/main.py
```

The backend server will start at `http://localhost:8000`.

## Frontend Setup

### Prerequisites
- Node.js 18 or higher
- npm (Node.js package manager)

### Installation

1. Navigate to the frontend directory:
```bash
cd route-planner-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file in the frontend directory with the following content:
```
VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
VITE_BACKEND_URL=http://localhost:8000
```

### Starting the Frontend Development Server

Run the development server:
```bash
npm run dev
```

The frontend application will start at `http://localhost:5173`.

## Usage Example

1. Start both the backend and frontend servers following the instructions above.
2. Open your browser and navigate to `http://localhost:5173`.
3. Enter a route request in the input field, for example:
```
現在地点：樟葉駅より100KM圏内のロードバイクが走りやすいルート候補を３つほどGoogleMapに表示してください。
```
4. Click the search button to generate and display the routes on the map.

## Development Requirements

### Backend
- FastAPI
- LangGraph
- Poetry for dependency management
- OpenAI API key for route generation

### Frontend
- React with TypeScript
- Vite for build tooling
- Google Maps JavaScript API
- shadcn/ui for UI components
- Tailwind CSS for styling

## Environment Variables

### Backend (.env)
```
OPENAI_API_KEY=your_openai_api_key_here
```

### Frontend (.env)
```
VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
VITE_BACKEND_URL=http://localhost:8000
```

Make sure to replace the API keys with your actual keys before running the application.
>
