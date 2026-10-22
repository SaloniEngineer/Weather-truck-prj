import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import MapView from './components/MapView';
import CorridorForecastSlider from './components/CorridorForecastSlider';

// Backend (Render) ka live URL
const API_URL = 'https://truck-weather-api.onrender.com';

function getInitialDateTime() {
  const now = new Date();
  // round to next hour
  now.setMinutes(0, 0, 0);
  now.setHours(now.getHours() + 1);
  const pad = (n) => String(n).padStart(2, '0');
  const yyyy = now.getFullYear();
  const mm = pad(now.getMonth() + 1);
  const dd = pad(now.getDate());
  const hh = pad(now.getHours());
  const min = pad(now.getMinutes());
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`;
}

export default function App() {
  const [origin, setOrigin] = useState('Chicago, IL');
  const [destination, setDestination] = useState('Denver, CO');
  const [departureTime, setDepartureTime] = useState(getInitialDateTime);
  const [loadWeight, setLoadWeight] = useState(35000);
  const [intervalMiles, setIntervalMiles] = useState(25);

  const [routes, setRoutes] = useState([]);
  const [selectedRouteId, setSelectedRouteId] = useState(null);
  const [corridorHeatmap, setCorridorHeatmap] = useState(null);
  const [originCoords, setOriginCoords] = useState(null);
  const [destCoords, setDestCoords] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Heatmap slider state
  const [sliderHour, setSliderHour] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeMetric, setActiveMetric] = useState('risk');

  const analyzeRoutes = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const depDate = new Date(departureTime);
      const isoDeparture = isNaN(depDate.getTime())
        ? new Date().toISOString()
        : depDate.toISOString();

      const response = await fetch(`${API_URL}/api/routes/analyze/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin,
          destination,
          departure_time: isoDeparture,
          load_weight: Number(loadWeight),
          interval_miles: Number(intervalMiles),
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.error || `Server responded with status ${response.status}`);
      }

      const data = await response.json();

      setRoutes(data.routes || []);
      setSelectedRouteId(data.recommended_route_id || data.routes?.[0]?.id || null);
      setCorridorHeatmap(data.corridor_heatmap || null);
      setOriginCoords(data.origin || null);
      setDestCoords(data.destination || null);
      setSliderHour(0);
      setIsPlaying(false);
    } catch (err) {
      console.error('Error analyzing routes:', err);
      if (err.name === 'TypeError' && String(err.message).toLowerCase().includes('fetch')) {
        setError('Cannot reach backend server. It may be waking up, please try again in a minute.');
      } else {
        setError(err.message || 'Failed to fetch weather routing analysis.');
      }
    } finally {
      setLoading(false);
    }
  }, [origin, destination, departureTime, loadWeight, intervalMiles]);

  // Initial fetch on mount for immediate rich presentation
  useEffect(() => {
    analyzeRoutes();
  }, []);

  return (
    <div className="app-container">
      <Sidebar
        origin={origin}
        setOrigin={setOrigin}
        destination={destination}
        setDestination={setDestination}
        departureTime={departureTime}
        setDepartureTime={setDepartureTime}
        loadWeight={loadWeight}
        setLoadWeight={setLoadWeight}
        intervalMiles={intervalMiles}
        setIntervalMiles={setIntervalMiles}
        onAnalyze={analyzeRoutes}
        loading={loading}
        error={error}
        routes={routes}
        selectedRouteId={selectedRouteId}
        onSelectRoute={setSelectedRouteId}
      />

      <div style={{ flex: 1, position: 'relative', height: '100%' }}>
        <MapView
          routes={routes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
          corridorHeatmap={corridorHeatmap}
          sliderHour={sliderHour}
          activeMetric={activeMetric}
          origin={originCoords}
          destination={destCoords}
        />

        {corridorHeatmap && corridorHeatmap.points?.length > 0 && (
          <CorridorForecastSlider
            sliderHour={sliderHour}
            setSliderHour={setSliderHour}
            isPlaying={isPlaying}
            setIsPlaying={setIsPlaying}
            activeMetric={activeMetric}
            setActiveMetric={setActiveMetric}
            corridorHeatmap={corridorHeatmap}
          />
        )}
      </div>
    </div>
  );
}