import { useState } from 'react';
import { Map } from './components/Map';
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Loader2 } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { Toaster } from "@/components/ui/toaster"

function App() {
  const [routes, setRoutes] = useState<Array<Array<{ lat: number; lng: number; name?: string }>>>([]);
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  const handleSearch = async () => {
    setRoutes([])
    if (!prompt.trim()) {
      toast({
        title: "Error",
        description: "Please enter a route request",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/api/route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch routes');
      }

      const data = await response.json();
      setRoutes(data.routes);
      toast({
        title: "Success",
        description: `Found ${data.routes.length} routes`,
      });
    } catch (error) {
      console.error('Error fetching routes:', error);
      toast({
        title: "Error",
        description: "Failed to fetch routes. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="container mx-auto p-4">
        <Card>
          <CardHeader>
            <CardTitle>Route Planner</CardTitle>
            <CardDescription>
              Example: 現在地点：樟葉駅より100KM圏内のロードバイクが走りやすいルート候補を３つほどGoogleMapに表示してください。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 mb-4">
              <Input
                type="text"
                placeholder="Enter your route request..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="flex-1"
              />
              <Button 
                onClick={handleSearch} 
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  'Search'
                )}
              </Button>
            </div>
            <div className="h-96 rounded-lg overflow-hidden border">
              <Map routes={routes} />
            </div>
          </CardContent>
        </Card>
      </div>
      <Toaster />
    </>
  );
}

export default App;
