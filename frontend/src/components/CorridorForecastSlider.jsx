import React, { useEffect } from 'react';
import { Play, Pause, CloudSun, Wind, CloudRain, Snowflake } from 'lucide-react';

export default function CorridorForecastSlider({
  sliderHour,
  setSliderHour,
  isPlaying,
  setIsPlaying,
  activeMetric,
  setActiveMetric,
  corridorHeatmap,
}) {
  const maxHours = Math.max(0, (corridorHeatmap?.hours_count || 48) - 1);

  // Auto-play interval animation
  useEffect(() => {
    let interval = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setSliderHour((prev) => (prev >= maxHours ? 0 : prev + 1));
      }, 350);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isPlaying, maxHours, setSliderHour]);

  // Current timestamp formatted
  const currentTimestamp = corridorHeatmap?.timestamps?.[sliderHour];
  let formattedTime = `+${sliderHour}h`;
  if (currentTimestamp) {
    try {
      const d = new Date(currentTimestamp);
      formattedTime = `+${sliderHour}h (${d.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })})`;
    } catch (e) {
      // fallback
    }
  }

  return (
    <div className="corridor-forecast-panel">
      <div className="forecast-header-row">
        <div className="forecast-title-badge">
          <CloudSun size={18} color="#38bdf8" />
          <span>Trip Corridor Weather Forecast</span>
        </div>

        <div className="metric-switcher">
          <button
            type="button"
            className={`metric-btn ${activeMetric === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveMetric('risk')}
          >
            Risk Heatmap
          </button>
          <button
            type="button"
            className={`metric-btn ${activeMetric === 'wind' ? 'active' : ''}`}
            onClick={() => setActiveMetric('wind')}
          >
            <Wind size={12} style={{ display: 'inline', marginRight: 4 }} />
            Wind
          </button>
          <button
            type="button"
            className={`metric-btn ${activeMetric === 'rain' ? 'active' : ''}`}
            onClick={() => setActiveMetric('rain')}
          >
            <CloudRain size={12} style={{ display: 'inline', marginRight: 4 }} />
            Rain
          </button>
          <button
            type="button"
            className={`metric-btn ${activeMetric === 'snow' ? 'active' : ''}`}
            onClick={() => setActiveMetric('snow')}
          >
            <Snowflake size={12} style={{ display: 'inline', marginRight: 4 }} />
            Snow
          </button>
        </div>

        <div className="hour-display-tag">{formattedTime}</div>
      </div>

      <div className="forecast-controls-row">
        <button
          type="button"
          className="play-toggle-btn"
          onClick={() => setIsPlaying(!isPlaying)}
          title={isPlaying ? 'Pause animation' : 'Play 48h weather progression'}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} fill="white" />}
        </button>

        <div className="slider-container">
          <input
            type="range"
            min={0}
            max={maxHours}
            value={sliderHour}
            onChange={(e) => {
              setSliderHour(Number(e.target.value));
              if (isPlaying) setIsPlaying(false);
            }}
            className="forecast-slider"
          />
          <div className="slider-ticks">
            <span>Depart (+0h)</span>
            <span>+12h</span>
            <span>+24h</span>
            <span>+36h</span>
            <span>+48h</span>
          </div>
        </div>
      </div>

      <div className="legend-bar">
        <span style={{ fontWeight: 600, color: '#e2e8f0' }}>Legend:</span>
        <div className="legend-item">
          <div className="legend-dot" style={{ background: '#10b981' }} />
          <span>Low</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot" style={{ background: '#eab308' }} />
          <span>Moderate</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot" style={{ background: '#f97316' }} />
          <span>High</span>
        </div>
        <div className="legend-item">
          <div className="legend-dot" style={{ background: '#ef4444' }} />
          <span>Severe</span>
        </div>
        <div className="legend-item">
          <div
            className="legend-dot"
            style={{ background: '#18181b', border: '1px solid #dc2626' }}
          />
          <span>No Travel</span>
        </div>
        <span style={{ marginLeft: 'auto', fontSize: '0.68rem', color: '#64748b' }}>
          *Instant slider switching powered by pre-fetched 48h temporal corridor matrix
        </span>
      </div>
    </div>
  );
}
