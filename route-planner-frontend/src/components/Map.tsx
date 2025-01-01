import { useCallback, useRef, useState, useEffect } from 'react';
import { GoogleMap, LoadScript, Polyline, Marker, InfoWindow } from '@react-google-maps/api';

const containerStyle = {
  width: '100%',
  height: '100%'
};

// Kusugaoka Station coordinates
const center = {
  lat: 34.859034,
  lng: 135.677555
};

interface MapProps {
  routes: Array<Array<{
    lat: number;
    lng: number;
    name?: string;
  }>>;
}

// Different colors for different routes
const routeColors = ['#FF0000', '#0000FF', '#00FF00'];

export function Map({ routes }: MapProps) {
  const mapRef = useRef<google.maps.Map>();
  const [selectedMarker, setSelectedMarker] = useState<{
    position: { lat: number; lng: number };
    name: string;
    routeIndex: number;
  } | null>(null);

  const onLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
  }, []);

  const onUnmount = useCallback(() => {
    mapRef.current = undefined;
  }, []);

  // Fit bounds to show all routes
  const fitBounds = useCallback(() => {
    if (mapRef.current && routes.length > 0) {
      const bounds = new google.maps.LatLngBounds();
      routes.forEach(route => {
        route.forEach(point => {
          bounds.extend(point);
        });
      });
      mapRef.current.fitBounds(bounds);
    }
  }, [routes]);

  useEffect(() => {
    fitBounds();
  }, [fitBounds]);

  return (
    <LoadScript googleMapsApiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY}>
      <GoogleMap
        mapContainerStyle={containerStyle}
        center={center}
        zoom={11}
        onLoad={onLoad}
        onUnmount={onUnmount}
      >
        {routes.map((route, routeIndex) => (
          <>
            <Polyline
              key={`route-${routeIndex}`}
              path={route}
              options={{
                strokeColor: routeColors[routeIndex % routeColors.length],
                strokeOpacity: 0.8,
                strokeWeight: 3,
              }}
            />
            {route.map((point, pointIndex) => (
              <Marker
                key={`marker-${routeIndex}-${pointIndex}`}
                position={point}
                icon={{
                  path: google.maps.SymbolPath.CIRCLE,
                  scale: 7,
                  fillColor: routeColors[routeIndex % routeColors.length],
                  fillOpacity: 1,
                  strokeWeight: 2,
                  strokeColor: '#FFFFFF',
                }}
                onClick={() => setSelectedMarker({
                  position: point,
                  name: point.name || `Point ${pointIndex + 1}`,
                  routeIndex,
                })}
              />
            ))}
          </>
        ))}
        {selectedMarker && (
          <InfoWindow
            position={selectedMarker.position}
            onCloseClick={() => setSelectedMarker(null)}
          >
            <div>
              <h3 className="font-semibold">Route {selectedMarker.routeIndex + 1}</h3>
              <p>{selectedMarker.name}</p>
            </div>
          </InfoWindow>
        )}
      </GoogleMap>
    </LoadScript>
  );
}
