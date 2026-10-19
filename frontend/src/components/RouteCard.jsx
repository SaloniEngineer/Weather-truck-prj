import React from 'react';
import { Star, ShieldAlert, AlertTriangle, CheckCircle2, Clock, Navigation } from 'lucide-react';

export default function RouteCard({ route, isSelected, onSelect }) {
  const p = route.risk_profile || {};
  const isRecommended = route.is_recommended;
  const isNoTravel = !p.is_travelable;

  const getRiskDot = (level) => {
    switch (level) {
      case 'Severe':
        return { color: '#ef4444', label: '🔴 Severe Risk', dot: '🔴' };
      case 'High':
        return { color: '#f97316', label: '🟠 High Risk', dot: '🟠' };
      case 'Moderate':
        return { color: '#eab308', label: '🟡 Moderate Risk', dot: '🟡' };
      case 'No Travel':
        return { color: '#18181b', label: '⚫ No Travel', dot: '⚫' };
      default:
        return { color: '#10b981', label: '🟢 Low Risk', dot: '🟢' };
    }
  };

  const riskDotInfo = getRiskDot(p.overall_risk_level);

  return (
    <div
      className={`route-card ${isSelected ? 'selected' : ''} ${
        isRecommended ? 'recommended' : ''
      }`}
      style={{ '--route-color': route.color }}
      onClick={() => onSelect(route.id)}
    >
      <div className="route-card-header">
        <div className="route-letter-badge">
          <div
            className="letter-circle"
            style={{ backgroundColor: route.color || '#3b82f6' }}
          >
            {route.route_letter || 'A'}
          </div>
          <span className="route-name">
            {isRecommended ? `★ ${route.name}` : route.name}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span title={riskDotInfo.label} style={{ fontSize: '1.1rem' }}>
            {riskDotInfo.dot}
          </span>
          {isRecommended && (
            <div className="rec-star-badge">
              <Star size={11} fill="#34d399" />
              Recommended
            </div>
          )}
        </div>
      </div>

      <div className="route-stats-grid">
        <div className="stat-item">
          <span className="stat-label">Duration</span>
          <span className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {route.duration_formatted}
          </span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Distance</span>
          <span className="stat-value">{route.distance_miles} mi</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Severe Exposure</span>
          <span
            className="stat-value"
            style={{
              color: p.severe_miles > 0 ? '#ef4444' : '#10b981',
              fontWeight: 700,
            }}
          >
            Sev {p.severe_miles} mi
          </span>
        </div>
      </div>

      <div className="risk-chips-row">
        {p.no_travel_miles > 0 && (
          <span className="risk-chip notravel">
            <ShieldAlert size={12} />
            {p.no_travel_miles} mi No Travel
          </span>
        )}
        {p.severe_miles > 0 && (
          <span className="risk-chip severe">
            <AlertTriangle size={12} />
            {p.severe_miles} mi Severe
          </span>
        )}
        {p.severe_miles === 0 && (
          <span className="risk-chip low">
            <CheckCircle2 size={12} />0 Severe mi
          </span>
        )}
        {p.high_miles > 0 && (
          <span className="risk-chip high">
            {p.high_miles} mi High
          </span>
        )}
        {p.moderate_miles > 0 && (
          <span className="risk-chip moderate">
            {p.moderate_miles} mi Mod
          </span>
        )}
      </div>

      {route.recommendation_why && (
        <div
          className={`route-why-banner ${
            isNoTravel || p.severe_miles > 30 ? 'warning' : ''
          }`}
        >
          {route.recommendation_why}
        </div>
      )}
    </div>
  );
}
