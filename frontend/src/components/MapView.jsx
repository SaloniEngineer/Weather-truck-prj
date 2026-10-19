import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

// Fix standard Leaflet default icon paths if needed
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const METRIC_COLOR_SCALES = {
  risk: (score) => {
    if (score >= 5) return '#18181b'; // No Travel
    if (score >= 4) return '#ef4444'; // Severe
    if (score >= 3) return '#f97316'; // High
    if (score >= 2) return '#eab308'; // Moderate
    return '#10b981';                // Low
  },
  wind: (w) => {
    if (w >= 55) return '#991b1b';
    if (w >= 45) return '#ef4444';
    if (w >= 35) return '#f97316';
    if (w >= 25) return '#eab308';
    return '#38bdf8';
  },
  rain: (r) => {
    if (r >= 1.0) return '#4c1d95';
    if (r >= 0.5) return '#7c3aed';
    if (r >= 0.25) return '#2563eb';
    if (r >= 0.1) return '#06b6d4';
    return '#10b981';
  },
  snow: (s) => {
    if (s >= 3.0) return '#be185d';
    if (s >= 2.0) return '#ec4899';
    if (s >= 1.0) return '#818cf8';
    if (s >= 0.5) return '#a5b4fc';
    return '#38bdf8';
  },
};

export default function MapView({
  routes = [],
  selectedRouteId,
  onSelectRoute,
  corridorHeatmap,
  sliderHour = 0,
  activeMetric = 'risk',
  origin,
  destination,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const routesLayerGroupRef = useRef(null);
  const checkpointsLayerGroupRef = useRef(null);
  const heatmapLayerGroupRef = useRef(null);
  const markersLayerGroupRef = useRef(null);

  // 1. Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [39.8283, -98.5795], // Geographic center of contiguous US
      zoom: 5,
      zoomControl: false,
    });

    L.control.zoom({ position: 'topright' }).addTo(map);

    // High-contrast Dark Gray Canvas basemap for professional dispatch console
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      {
        attribution: '&copy; <a href="https://www.esri.com/">Esri</a> &mdash; GIS User Community',
        maxZoom: 16,
      }
    ).addTo(map);

    // Dark canvas labels layer (cities, states, major highways)
    L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}',
      {
        maxZoom: 16,
        opacity: 0.85,
      }
    ).addTo(map);

    routesLayerGroupRef.current = L.layerGroup().addTo(map);
    heatmapLayerGroupRef.current = L.layerGroup().addTo(map);
    checkpointsLayerGroupRef.current = L.layerGroup().addTo(map);
    markersLayerGroupRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // 2. Render Routes Polylines
  useEffect(() => {
    const map = mapInstanceRef.current;
    const routesLayer = routesLayerGroupRef.current;
    if (!map || !routesLayer) return;

    routesLayer.clearLayers();

    if (!routes || routes.length === 0) return;

    const allLatLngs = [];

    routes.forEach((route) => {
      const isSelected = route.id === selectedRouteId;
      const coords = route.geometry?.coordinates || [];
      const latLngs = coords.map((c) => [c[1], c[0]]);

      if (latLngs.length > 0) {
        allLatLngs.push(...latLngs);

        // Background shadow / glow for active route
        if (isSelected) {
          L.polyline(latLngs, {
            color: route.color || '#3b82f6',
            weight: 9,
            opacity: 0.35,
            lineCap: 'round',
            lineJoin: 'round',
          }).addTo(routesLayer);
        }

        // Main polyline
        const poly = L.polyline(latLngs, {
          color: route.color || '#3b82f6',
          weight: isSelected ? 5.5 : 3.5,
          opacity: isSelected ? 0.95 : 0.45,
          dashArray: isSelected ? null : '4, 6',
          lineCap: 'round',
          lineJoin: 'round',
        });

        poly.on('click', () => {
          if (onSelectRoute) onSelectRoute(route.id);
        });

        poly.bindTooltip(
          `<strong>${route.name}</strong><br/>${route.distance_miles} mi • ${route.duration_formatted}`,
          { sticky: true, className: 'route-tooltip' }
        );

        poly.addTo(routesLayer);
      }
    });

    // Fit map bounds to show all routes
    if (allLatLngs.length > 0) {
      const bounds = L.latLngBounds(allLatLngs);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
    }
  }, [routes, selectedRouteId, onSelectRoute]);

  // 3. Render Origin and Destination Map Pins
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerGroupRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();

    if (origin?.lat && origin?.lon) {
      const originIcon = L.divIcon({
        className: 'custom-pin origin-pin',
        html: `<div style="background:#2563eb;color:white;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;border:2px solid white;box-shadow:0 3px 8px rgba(0,0,0,0.5)">A</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });
      L.marker([origin.lat, origin.lon], { icon: originIcon })
        .bindPopup(`<strong>Origin:</strong> ${origin.name}`)
        .addTo(markersLayer);
    }

    if (destination?.lat && destination?.lon) {
      const destIcon = L.divIcon({
        className: 'custom-pin dest-pin',
        html: `<div style="background:#dc2626;color:white;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;border:2px solid white;box-shadow:0 3px 8px rgba(0,0,0,0.5)">B</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });
      L.marker([destination.lat, destination.lon], { icon: destIcon })
        .bindPopup(`<strong>Destination:</strong> ${destination.name}`)
        .addTo(markersLayer);
    }
  }, [origin, destination]);

  // 4. Render Checkpoints on Active Selected Route
  useEffect(() => {
    const map = mapInstanceRef.current;
    const cpLayer = checkpointsLayerGroupRef.current;
    if (!map || !cpLayer) return;

    cpLayer.clearLayers();

    const selectedRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];
    if (!selectedRoute || !selectedRoute.checkpoints) return;

    selectedRoute.checkpoints.forEach((cp) => {
      const risk = cp.risk || {};
      const weather = cp.weather || {};
      const level = risk.level || 'Low';
      const color = risk.color || '#10b981';

      // Format ETA readable
      let etaFormatted = cp.eta_iso || '';
      try {
        const d = new Date(cp.eta_iso);
        etaFormatted = d.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          timeZoneName: 'short',
        });
      } catch (e) {
        // keep raw
      }

      const circle = L.circleMarker([cp.latitude, cp.longitude], {
        radius: level === 'Severe' || level === 'No Travel' ? 7.5 : 5.5,
        fillColor: color,
        color: level === 'No Travel' ? '#ef4444' : '#ffffff',
        weight: level === 'No Travel' ? 2.5 : 1.5,
        opacity: 1,
        fillOpacity: 0.95,
      });

      // Rich Checkpoint Popup
      const popupHtml = `
        <div class="popup-card">
          <div class="popup-title-row">
            <span class="popup-title">Checkpoint #${cp.index + 1}</span>
            <span style="background:${color};color:${level === 'Moderate' ? '#000' : '#fff'};font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;text-transform:uppercase;">
              ${level}
            </span>
          </div>
          <div style="font-size:11px;color:#94a3b8;margin-top:2px;">
            <strong>ETA:</strong> ${etaFormatted}
          </div>
          <div style="font-size:11px;color:#94a3b8;">
            <strong>Distance:</strong> ${cp.distance_from_start_miles} mi (${cp.segment_miles} mi segment)
          </div>
          <div class="popup-metrics-grid">
            <div class="popup-metric">
              <span class="popup-metric-label">Wind</span>
              <span class="popup-metric-val">${weather.wind_speed_mph ?? 0} mph</span>
            </div>
            <div class="popup-metric">
              <span class="popup-metric-label">Rain</span>
              <span class="popup-metric-val">${weather.rain_in_hr ?? 0} in/hr</span>
            </div>
            <div class="popup-metric">
              <span class="popup-metric-label">Snow</span>
              <span class="popup-metric-val">${weather.snow_in_hr ?? 0} in/hr</span>
            </div>
            <div class="popup-metric">
              <span class="popup-metric-label">Duration</span>
              <span class="popup-metric-val">+${Math.round(cp.cumulative_duration_seconds / 60)} min</span>
            </div>
          </div>
          ${
            risk.explanation
              ? `<div class="popup-hazard-note">${risk.explanation}</div>`
              : ''
          }
        </div>
      `;

      circle.bindPopup(popupHtml);
      circle.addTo(cpLayer);
    });
  }, [routes, selectedRouteId]);

  // 5. Render 48-Hour Corridor Heatmap Overlay (0ms client scrubbing)
  useEffect(() => {
    const map = mapInstanceRef.current;
    const heatmapLayer = heatmapLayerGroupRef.current;
    if (!map || !heatmapLayer) return;

    heatmapLayer.clearLayers();

    if (!corridorHeatmap || !corridorHeatmap.points) return;

    const points = corridorHeatmap.points;
    const hourIdx = Math.min(sliderHour, (corridorHeatmap.hours_count || 48) - 1);

    points.forEach((pt) => {
      let val = 0;
      let color = '#38bdf8';
      let radius = 26;
      let label = '';

      if (activeMetric === 'risk') {
        const score = pt.risk_score?.[hourIdx] ?? 1;
        const level = pt.risk_level?.[hourIdx] ?? 'Low';
        color = METRIC_COLOR_SCALES.risk(score);
        radius = score >= 4 ? 34 : 24;
        label = `Risk: ${level} (Score ${score})`;
      } else if (activeMetric === 'wind') {
        val = pt.wind?.[hourIdx] ?? 0;
        color = METRIC_COLOR_SCALES.wind(val);
        radius = val > 40 ? 32 : 22;
        label = `Wind: ${val} mph`;
      } else if (activeMetric === 'rain') {
        val = pt.rain?.[hourIdx] ?? 0;
        color = METRIC_COLOR_SCALES.rain(val);
        radius = val > 0.5 ? 30 : 20;
        label = `Rain: ${val} in/hr`;
      } else if (activeMetric === 'snow') {
        val = pt.snow?.[hourIdx] ?? 0;
        color = METRIC_COLOR_SCALES.snow(val);
        radius = val > 1.0 ? 32 : 22;
        label = `Snow: ${val} in/hr`;
      }

      // Smooth translucent halo circle
      const halo = L.circle([pt.lat, pt.lon], {
        radius: radius * 1200, // meters in geographical coordinates
        fillColor: color,
        fillOpacity: 0.28,
        color: color,
        weight: 1,
        opacity: 0.4,
      });

      halo.bindTooltip(label, { sticky: true });
      halo.addTo(heatmapLayer);
    });
  }, [corridorHeatmap, sliderHour, activeMetric]);

  return (
    <div className="map-viewport">
      <div id="map-canvas" ref={mapContainerRef} />
    </div>
  );
}
