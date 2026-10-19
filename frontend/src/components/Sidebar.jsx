import React, { useState } from 'react';
import {
  Truck,
  MapPin,
  Navigation,
  Clock,
  Weight,
  Layers,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertOctagon,
} from 'lucide-react';
import RouteCard from './RouteCard';

const PRESET_TRIPS = [
  {
    name: 'Chicago ➔ Denver',
    origin: 'Chicago, IL',
    dest: 'Denver, CO',
    load: 35000,
    desc: 'High Plains Crosswinds',
  },
  {
    name: 'Seattle ➔ Dallas',
    origin: 'Seattle, WA',
    dest: 'Dallas, TX',
    load: 42000,
    desc: 'Heavy Freight Corridor',
  },
  {
    name: 'Salt Lake ➔ Kansas City',
    origin: 'Salt Lake City, UT',
    dest: 'Kansas City, MO',
    load: 28000,
    desc: 'Mountain Pass Route',
  },
];

export default function Sidebar({
  origin,
  setOrigin,
  destination,
  setDestination,
  departureTime,
  setDepartureTime,
  loadWeight,
  setLoadWeight,
  intervalMiles,
  setIntervalMiles,
  onAnalyze,
  loading,
  error,
  routes,
  selectedRouteId,
  onSelectRoute,
}) {
  const [showCheckpoints, setShowCheckpoints] = useState(false);

  const selectedRoute =
    routes.find((r) => r.id === selectedRouteId) || routes[0];

  const handlePresetSelect = (preset) => {
    setOrigin(preset.origin);
    setDestination(preset.dest);
    setLoadWeight(preset.load);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-badge">
          <div className="brand-logo-icon">
            <Truck size={18} />
          </div>
          <div>
            <h1 className="brand-title">Spotter Routing</h1>
            <span className="brand-sub">Weather-Aware Dispatch</span>
          </div>
        </div>
      </div>

      <div className="sidebar-content">
        {/* Preset Quick Actions */}
        <div>
          <span className="input-label" style={{ marginBottom: 6 }}>
            <Sparkles size={13} color="#38bdf8" /> Quick Test Corridors
          </span>
          <div className="preset-buttons">
            {PRESET_TRIPS.map((preset) => (
              <button
                key={preset.name}
                type="button"
                className="preset-chip"
                onClick={() => handlePresetSelect(preset)}
                title={preset.desc}
              >
                {preset.name}
              </button>
            ))}
          </div>
        </div>

        {/* Input Form Card */}
        <form
          className="form-card"
          onSubmit={(e) => {
            e.preventDefault();
            onAnalyze();
          }}
        >
          {/* Origin */}
          <div className="input-group">
            <label className="input-label" htmlFor="origin-input">
              <MapPin size={13} color="#3b82f6" /> Origin
            </label>
            <div className="input-wrapper">
              <MapPin size={15} className="input-icon" />
              <input
                id="origin-input"
                type="text"
                className="text-input"
                placeholder="City or lat, lon"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Destination */}
          <div className="input-group">
            <label className="input-label" htmlFor="destination-input">
              <Navigation size={13} color="#ef4444" /> Destination
            </label>
            <div className="input-wrapper">
              <Navigation size={15} className="input-icon" />
              <input
                id="destination-input"
                type="text"
                className="text-input"
                placeholder="City or lat, lon"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Depart Time & Load Weight */}
          <div className="two-col-grid">
            <div className="input-group">
              <label className="input-label" htmlFor="depart-input">
                <Clock size={13} color="#a855f7" /> Depart Time
              </label>
              <div className="input-wrapper">
                <input
                  id="depart-input"
                  type="datetime-local"
                  className="text-input"
                  style={{ paddingLeft: '10px' }}
                  value={departureTime}
                  onChange={(e) => setDepartureTime(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="input-group">
              <label className="input-label" htmlFor="load-input">
                <Weight size={13} color="#06b6d4" /> Load (lb)
              </label>
              <div className="input-wrapper">
                <input
                  id="load-input"
                  type="number"
                  min="0"
                  max="100000"
                  step="1000"
                  className="text-input"
                  style={{ paddingLeft: '10px' }}
                  value={loadWeight}
                  onChange={(e) => setLoadWeight(Number(e.target.value))}
                  required
                />
              </div>
            </div>
          </div>

          {/* Quick Weight Selectors */}
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.7rem', color: '#64748b' }}>Presets:</span>
            {[
              { label: 'Empty (15k)', val: 15000 },
              { label: 'Std (32k)', val: 32000 },
              { label: 'Heavy (42k)', val: 42000 },
            ].map((p) => (
              <button
                key={p.label}
                type="button"
                className="preset-chip"
                style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                onClick={() => setLoadWeight(p.val)}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Interval Selector */}
          <div className="input-group">
            <label className="input-label">
              <Layers size={13} color="#10b981" /> Sampling Interval
            </label>
            <div className="segmented-control">
              {[10, 25, 50].map((step) => (
                <button
                  key={step}
                  type="button"
                  className={`segmented-btn ${
                    intervalMiles === step ? 'active' : ''
                  }`}
                  onClick={() => setIntervalMiles(step)}
                >
                  {step} miles
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            id="find-routes-btn"
            type="submit"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? (
              <>
                <div
                  style={{
                    width: 16,
                    height: 16,
                    border: '2px solid white',
                    borderTopColor: 'transparent',
                    borderRadius: '50%',
                    animation: 'spin 0.8s linear infinite',
                  }}
                />
                Analyzing Weather & Corridors...
              </>
            ) : (
              <>
                <Navigation size={17} />
                Find Safe Routes
              </>
            )}
          </button>
        </form>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: 8,
              padding: '10px 14px',
              color: '#fca5a5',
              fontSize: '0.82rem',
              display: 'flex',
              gap: 8,
              alignItems: 'center',
            }}
          >
            <AlertOctagon size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Skeletons while loading */}
        {loading && (
          <div className="routes-list">
            <div className="skeleton-box" style={{ height: 110 }} />
            <div className="skeleton-box" style={{ height: 110 }} />
            <div className="skeleton-box" style={{ height: 110 }} />
          </div>
        )}

        {/* Routes List */}
        {!loading && routes.length > 0 && (
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 8,
              }}
            >
              <span className="input-label">3 Corridors Evaluated</span>
              <span style={{ fontSize: '0.72rem', color: '#64748b' }}>
                Sorted by Safety Priority
              </span>
            </div>

            <div className="routes-list">
              {routes.map((route) => (
                <RouteCard
                  key={route.id}
                  route={route}
                  isSelected={route.id === selectedRouteId}
                  onSelect={onSelectRoute}
                />
              ))}
            </div>

            {/* Checkpoints Drawer for Selected Route */}
            {selectedRoute?.checkpoints && (
              <div style={{ marginTop: 14 }}>
                <button
                  type="button"
                  onClick={() => setShowCheckpoints(!showCheckpoints)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#93c5fd',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                  }}
                >
                  {showCheckpoints ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  {showCheckpoints
                    ? 'Hide Checkpoint Weather Breakdown'
                    : `View ${selectedRoute.checkpoints.length} Checkpoints for ${selectedRoute.name}`}
                </button>

                {showCheckpoints && (
                  <div
                    style={{
                      maxHeight: 220,
                      overflowY: 'auto',
                      marginTop: 8,
                      background: 'rgba(0, 0, 0, 0.25)',
                      borderRadius: 8,
                      border: '1px solid var(--border-subtle)',
                      padding: '6px 8px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 4,
                    }}
                  >
                    {selectedRoute.checkpoints.map((cp) => (
                      <div
                        key={cp.index}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          fontSize: '0.72rem',
                          padding: '4px 6px',
                          borderBottom: '1px solid rgba(255,255,255,0.05)',
                        }}
                      >
                        <div>
                          <span style={{ fontWeight: 600, color: '#f8fafc' }}>
                            #{cp.index + 1} ({cp.distance_from_start_miles} mi)
                          </span>
                          <span style={{ color: '#94a3b8', marginLeft: 6 }}>
                            {cp.weather?.wind_speed_mph} mph wind • {cp.weather?.rain_in_hr} in rain
                          </span>
                        </div>
                        <span
                          style={{
                            background: cp.risk?.color,
                            color: cp.risk?.level === 'Moderate' ? '#000' : '#fff',
                            padding: '1px 6px',
                            borderRadius: 4,
                            fontWeight: 700,
                            fontSize: '0.65rem',
                          }}
                        >
                          {cp.risk?.level}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
