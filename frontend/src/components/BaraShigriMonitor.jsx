

import { useState } from "react";
import {
  Activity,
  Satellite,
  Eye,
  EyeOff,
  CalendarDays,
  MapPin,
} from "lucide-react";

const layers = {
  velocity: {
    label: "Horizontal velocity",
    file: "nisar_velocity_m_per_year.png",
    unit: "m/year",
    min: "11.41",
    max: "52.46",
    median: "25.54",
  },
  uncertainty: {
    label: "Velocity uncertainty",
    file: "nisar_velocity_uncertainty_m_per_year.png",
    unit: "m/year",
    min: "0.57",
    max: "3.63",
    median: "1.54",
  },
  daily: {
    label: "Daily horizontal velocity",
    file: "nisar_velocity_m_per_day.png",
    unit: "m/day",
    min: "0.031",
    max: "0.144",
    median: "0.0699",
  },
};

export default function BaraShigriMonitor() {
  const [selected, setSelected] = useState("velocity");
  const [showMask, setShowMask] = useState(false);

  const layer = layers[selected];

  return (
    <div className="nisar-page">
      <div className="nisar-heading">
        <div>
          <span className="section-kicker">
            SATELLITE GLACIER MONITORING
          </span>
          <h2>Bara Shigri Glacier</h2>
          <p>
            NISAR L2 GOFF · Frequency A/HH · EPSG:32643
          </p>
        </div>
        <span className="nisar-source-tag">
          <Satellite size={15} /> NISAR
        </span>
      </div>

      <div className="nisar-metrics">
        <div className="nisar-card">
          <span>MEDIAN HORIZONTAL VELOCITY</span>
          <strong>25.54 <small>m/year</small></strong>
          <p>Mean: 27.67 m/year</p>
        </div>

        <div className="nisar-card">
          <span>MEDIAN UNCERTAINTY</span>
          <strong>1.54 <small>m/year</small></strong>
          <p>Covariance-based estimate</p>
        </div>

        <div className="nisar-card">
          <span>VALID PIXELS</span>
          <strong>6,898</strong>
          <p>Final candidate mask</p>
        </div>

        <div className="nisar-card">
          <span>ACQUISITION INTERVAL</span>
          <strong>12 <small>days</small></strong>
          <p>04 Oct – 16 Oct 2026</p>
        </div>
      </div>

      <div className="nisar-layout">
        <section className="panel nisar-map-panel">
          <div className="nisar-map-heading">
            <div>
              <span className="section-kicker">
                SPATIAL DATA VISUALIZATION
              </span>
              <h3>{layer.label}</h3>
            </div>
            <Activity size={19} />
          </div>

          <div className="nisar-map">
            <img
              key={layer.file}
              src={`/data/bara_shigri/${layer.file}`}
              alt={`${layer.label} NISAR raster`}
            />

            {showMask && (
              <img
                className="nisar-mask"
                src="/data/bara_shigri/nisar_candidate_mask.png"
                alt="NISAR final candidate mask"
              />
            )}
          </div>

          <div className="nisar-colorbar">
            <div className={`colorbar-gradient ${selected}`} />
            <div className="colorbar-labels">
              <span>{layer.min} {layer.unit}</span>
              <strong>Median: {layer.median} {layer.unit}</strong>
              <span>{layer.max} {layer.unit}</span>
            </div>
          </div>

          <div className="nisar-map-footer">
            <span><MapPin size={14}/> EPSG:32643</span>
            <span>80 m resolution</span>
            <span>317 × 246 pixels</span>
          </div>
        </section>

        <aside className="panel nisar-controls">
          <span className="section-kicker">VISUALIZATION</span>
          <h3>Data layers</h3>

          <div className="nisar-layer-list">
            {Object.entries(layers).map(([key, item]) => (
              <button
                key={key}
                className={selected === key ? "active" : ""}
                onClick={() => setSelected(key)}
              >
                {item.label}
                {selected === key && <Eye size={16}/>}
              </button>
            ))}
          </div>

          <button
            className="nisar-mask-toggle"
            onClick={() => setShowMask(!showMask)}
          >
            Final candidate mask
            {showMask ? <Eye size={16}/> : <EyeOff size={16}/>}
          </button>

          <div className="nisar-acquisition">
            <CalendarDays size={17}/>
            <div>
              <strong>Acquisition dates</strong>
              <p>Reference: 04 October 2026</p>
              <p>Secondary: 16 October 2026</p>
            </div>
          </div>

          <div className="nisar-note">
            Horizontal velocity is derived from the 12-day
            NISAR observation interval and annualized.
            Vertical motion is not included.
          </div>
        </aside>
      </div>
    </div>
  );
}
