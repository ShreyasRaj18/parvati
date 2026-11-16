import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertTriangle, ArrowUpRight, BarChart3, BrainCircuit,
  CheckCircle2, ChevronRight, Database, Eye, EyeOff, Gauge,
  Layers3, LayoutDashboard, MapPin, Menu, Mountain, Radio, Maximize2, Minimize2,
  Satellite, ShieldAlert, Waves, X, Zap
} from "lucide-react";

import TerrainViewer from "./components/TerrainViewer.jsx";
import BaraShigriMonitor from "./components/BaraShigriMonitor.jsx";
import BaraShigri3DViewer from "./components/BaraShigri3DViewer.jsx";
import "./App.css";

const navigation = [
  { label: "Overview", icon: LayoutDashboard, group: "WORKSPACE" },
  { label: "3D Terrain Explorer", icon: Mountain, group: "WORKSPACE" },
  { label: "Lake Monitoring", icon: Waves, group: "WORKSPACE" },
  { label: "Glacier Monitoring", icon: Satellite, group: "WORKSPACE" },
  { label: "Bara Shigri 3D", icon: Activity, group: "WORKSPACE" },
  { label: "Predictive Analysis", icon: BrainCircuit, group: "INTELLIGENCE" },
  { label: "Scenario Explorer", icon: BarChart3, group: "INTELLIGENCE" },
];

const initialLayers = [
  { name: "Terrain surface", enabled: true },
  { name: "Lake water", enabled: true },
  { name: "Lake boundary", enabled: true },
  { name: "Catchment boundary", enabled: true },
  { name: "Drainage network", enabled: true },
  { name: "Potential flow corridor", enabled: true },
];

const modelMetrics = {
  accuracy: 99.27,
  balancedAccuracy: 51.09,
  precision: 25.0,
  recall: 2.22,
  f1: 4.08,
  rocAuc: 0.5767,
  prAuc: 0.024,
  baselineAp: 0.007,
};

function App() {
  const [activePage, setActivePage] = useState("Overview");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const navigate = (page) => {
    setActivePage(page);
    setMobileNavOpen(false);
    window.scrollTo?.({ top: 0, behavior: "smooth" });
  };

  const activeItem = navigation.find((item) => item.label === activePage);

  return (
    <div className="app-shell">
      {mobileNavOpen && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <aside className={`sidebar ${mobileNavOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Mountain size={22} strokeWidth={1.8} /></div>
          <div className="brand-copy">
            <strong>PARVATI</strong>
            <span>CRYOSPHERE INTELLIGENCE</span>
          </div>
          <button className="mobile-close" onClick={() => setMobileNavOpen(false)} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <div className="workspace-chip">
          <span className="workspace-chip-dot" />
          HIMALAYAN RESEARCH
          <ChevronRight size={13} />
        </div>

        <nav className="side-nav" aria-label="Main navigation">
          <div className="nav-group-label">WORKSPACE</div>
          {navigation.filter((item) => item.group === "WORKSPACE").map(({ label, icon: Icon }) => (
            <NavButton key={label} label={label} Icon={Icon} active={activePage === label} onClick={() => navigate(label)} />
          ))}
          <div className="nav-group-label nav-group-spaced">INTELLIGENCE</div>
          {navigation.filter((item) => item.group === "INTELLIGENCE").map(({ label, icon: Icon }) => (
            <NavButton key={label} label={label} Icon={Icon} active={activePage === label} onClick={() => navigate(label)} />
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-project-card">
            <div className="project-card-icon"><Database size={16} /></div>
            <div>
              <strong>PARVATI research build</strong>
              <span>Local project workspace</span>
            </div>
            <span className="project-card-status" />
          </div>
          <div className="sidebar-footnote">
            <span className="status-pulse" />
            Research prototype
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation">
              <Menu size={19} />
            </button>
            <div className="breadcrumb">
              <span>PARVATI</span><ChevronRight size={14} /><strong>{activePage}</strong>
            </div>
          </div>
          <div className="topbar-right">
            <div className="topbar-dataset"><span className="dataset-dot" /> PROJECT DATASET · 2026</div>
            <div className="topbar-divider" />
            <div className="topbar-location"><MapPin size={14} /> Himachal Pradesh, India</div>
          </div>
        </header>

        {activePage === "Bara Shigri 3D" ? (
          <PageFrame
            eyebrow="NISAR · GLACIER DYNAMICS"
            title="Bara Shigri 3D"
            description="Measured horizontal glacier motion rendered over Copernicus DEM terrain."
            tag="12-DAY ACQUISITION PAIR"
          >
            <BaraShigri3DViewer />
          </PageFrame>
        ) : activePage === "Glacier Monitoring" ? (
          <PageFrame
            eyebrow="SATELLITE OBSERVATION"
            title="Glacier monitoring"
            description="Bara Shigri glacier displacement, uncertainty and NISAR observation layers."
            tag="NISAR · OCT 2026"
          >
            <BaraShigriMonitor />
          </PageFrame>
        ) : activePage === "Predictive Analysis" ? (
          <PageFrame
            eyebrow="MACHINE LEARNING · HISTORICAL GLOF INVENTORY"
            title="Predictive analysis"
            description="Exploratory lake-level screening using historical GLOF records and lake morphology."
            tag="MODEL · RANDOM FOREST"
          >
            <PredictiveAnalysis />
          </PageFrame>
        ) : activePage === "3D Terrain Explorer" ? (
          <PageFrame
            eyebrow="GEOSPATIAL DIGITAL TERRAIN"
            title="3D terrain explorer"
            description="Explore Samudra Tapu terrain, lake boundary, catchment and drainage layers."
            tag="COPERNICUS DEM · 8 M GRID"
          >
            <TerrainWorkspace />
          </PageFrame>
        ) : activePage === "Lake Monitoring" ? (
          <PageFrame
            eyebrow="SENTINEL-2 · WATER EXTRACTION"
            title="Lake monitoring"
            description="Samudra Tapu lake-area observations and terrain context."
            tag="25 SEP — 05 OCT 2026"
          >
            <LakeMonitoring />
          </PageFrame>
        ) : activePage === "Scenario Explorer" ? (
          <PageFrame
            eyebrow="CONDITIONAL HAZARD ASSESSMENT"
            title="Scenario explorer"
            description="Review the NRSC reference scenario matrix and terrain-derived drainage context."
            tag="SCENARIO MATRIX · NOT SIMULATED"
          >
            <ScenarioExplorer />
          </PageFrame>
        ) : (
          <Overview onNavigate={navigate} />
        )}

        <footer className="app-footer">
          <span><span className="footer-mark">P</span> PARVATI · CRYOSPHERE INTELLIGENCE</span>
          <span>Research prototype · Not an operational warning system</span>
        </footer>
      </main>
    </div>
  );
}

function NavButton({ label, Icon, active, onClick }) {
  return (
    <button className={`nav-item ${active ? "active" : ""}`} onClick={onClick} type="button">
      <Icon size={17} strokeWidth={1.8} />
      <span>{label}</span>
      {active && <span className="nav-active-indicator" />}
    </button>
  );
}

function PageFrame({ eyebrow, title, description, tag, children }) {
  return (
    <section className="page-content">
      <PageHeading eyebrow={eyebrow} title={title} description={description} tag={tag} />
      {children}
    </section>
  );
}

function PageHeading({ eyebrow, title, description, tag }) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow"><span className="eyebrow-line" />{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {tag && <div className="heading-tag">{tag}</div>}
    </div>
  );
}

function Overview({ onNavigate }) {
  return (
    <section className="page-content overview-page">
      <div className="overview-welcome">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" />HIMALAYAN GLACIAL LAKE OUTBURST FLOOD RESEARCH</div>
          <h1>See the terrain.<br /><span>Understand the signals.</span></h1>
          <p>Satellite-derived glacier dynamics, lake observations and terrain intelligence in one research workspace.</p>
          <div className="welcome-actions">
            <button className="primary-action" onClick={() => onNavigate("3D Terrain Explorer")}>
              Explore 3D terrain <ArrowUpRight size={16} />
            </button>
            <button className="secondary-action" onClick={() => onNavigate("Predictive Analysis")}>
              View ML analysis <BrainCircuit size={16} />
            </button>
          </div>
        </div>
        <div className="welcome-orbit" aria-hidden="true">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit-core"><Mountain size={43} /></div>
          <span className="orbit-label orbit-label-top">HMA · 32° N</span>
          <span className="orbit-label orbit-label-bottom">GEOSPATIAL INTELLIGENCE</span>
        </div>
      </div>

      <div className="metrics-grid">
        <MetricCard label="SAMUDRA TAPU LAKE AREA" value="155.19" unit="ha" detail="Sentinel-2 · 05 Oct 2026" icon={Waves} tone="cyan" />
        <MetricCard label="CANDIDATE CATCHMENT" value="154.28" unit="km²" detail="DEM-derived catchment" icon={Mountain} tone="violet" />
        <MetricCard label="BARA SHIGRI MEDIAN SPEED" value="25.54" unit="m/yr" detail="NISAR · single 12-day pair" icon={Activity} tone="blue" />
        <MetricCard label="HISTORICAL EVENT LAKES" value="227" unit="lakes" detail="Matched within 1 km" icon={Database} tone="amber" />
      </div>

      <div className="overview-section-heading">
        <div><span className="section-kicker">SPATIAL WORKSPACE</span><h2>Terrain intelligence</h2></div>
        <button className="text-action" onClick={() => onNavigate("3D Terrain Explorer")}>Open full explorer <ArrowUpRight size={15} /></button>
      </div>

      <div className="overview-main-grid">
        <div className="panel terrain-panel">
          <div className="panel-heading">
            <div><span className="section-kicker">SAMUDRA TAPU · 3D DIGITAL TERRAIN</span><h2>Catchment and drainage model</h2></div>
            <span className="data-state"><span className="state-dot" /> LOCAL TERRAIN DATA</span>
          </div>
          <TerrainWorkspace compact />
        </div>

        <aside className="overview-side">
          <div className="panel insight-panel">
            <div className="panel-heading">
              <div><span className="section-kicker">RESEARCH SNAPSHOT</span><h2>Study area signals</h2></div>
              <Radio size={17} className="muted-icon" />
            </div>
            <InsightRow label="Lake area change" value="+0.149 ha" note="Threshold-sensitive" tone="amber" />
            <InsightRow label="D8 drainage trace" value="47.46 km" note="Provisional terrain pathway" tone="cyan" />
            <InsightRow label="Terrain pixels analysed" value="2.41 M" note="Unsupervised ML feature stack" tone="violet" />
            <InsightRow label="Historical inventory" value="764 events" note="Across 9 countries" tone="blue" />
            <div className="insight-callout"><AlertTriangle size={15} /><span>Drainage proximity is not a simulated flood extent. Hydraulic modelling remains outstanding.</span></div>
          </div>

          <div className="panel model-status-panel">
            <div className="model-status-top">
              <div className="model-status-icon"><BrainCircuit size={18} /></div>
              <span className="status-pill status-amber">EXPERIMENTAL</span>
            </div>
            <span className="section-kicker">SUPERVISED ML BASELINE</span>
            <h3>Historical GLOF screening</h3>
            <div className="model-status-score"><strong>0.5767</strong><span>ROC-AUC</span></div>
            <p>Weak discrimination using five morphology and elevation predictors. Not a calibrated event probability.</p>
            <button className="text-action" onClick={() => onNavigate("Predictive Analysis")}>Inspect model performance <ArrowUpRight size={15} /></button>
          </div>
        </aside>
      </div>

      <div className="overview-bottom-grid">
        <div className="panel pipeline-panel">
          <div className="panel-heading"><div><span className="section-kicker">DATA PIPELINE</span><h2>Research components</h2></div><CheckCircle2 size={18} className="success-icon" /></div>
          <PipelineRow label="NISAR displacement and velocity" status="Complete" />
          <PipelineRow label="Sentinel-2 lake extraction" status="Complete" />
          <PipelineRow label="DEM and hydrological analysis" status="Complete" />
          <PipelineRow label="Unsupervised terrain ML" status="Complete" />
          <PipelineRow label="Historical supervised ML" status="Evaluated" warning />
          <PipelineRow label="Hydrodynamic flood simulation" status="Outstanding" warning />
        </div>
        <div className="panel quick-links-panel">
          <span className="section-kicker">QUICK ACCESS</span>
          <h2>Explore the evidence</h2>
          <QuickLink icon={Satellite} title="Bara Shigri glacier dynamics" subtitle="NISAR velocity field in 3D" onClick={() => onNavigate("Bara Shigri 3D")} />
          <QuickLink icon={Waves} title="Samudra Tapu lake" subtitle="Sentinel-2 observations" onClick={() => onNavigate("Lake Monitoring")} />
          <QuickLink icon={BrainCircuit} title="Predictive analysis" subtitle="Historical model evaluation" onClick={() => onNavigate("Predictive Analysis")} />
        </div>
      </div>
    </section>
  );
}

function MetricCard({ label, value, unit, detail, icon: Icon, tone }) {
  return (
    <div className="metric-card panel">
      <div className="metric-card-top"><span>{label}</span><div className={`metric-icon ${tone}`}><Icon size={17} /></div></div>
      <div className="metric-value">{value}<small>{unit}</small></div>
      <div className="metric-detail">{detail}</div>
    </div>
  );
}

function TerrainWorkspace({ compact = false }) {
  const [layers, setLayers] = useState(initialLayers);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const terrainStageRef = useRef(null);

  useEffect(() => {
    const syncFullscreen = () => setIsFullscreen(document.fullscreenElement === terrainStageRef.current);
    document.addEventListener("fullscreenchange", syncFullscreen);
    return () => document.removeEventListener("fullscreenchange", syncFullscreen);
  }, []);

  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement === terrainStageRef.current) {
        await document.exitFullscreen();
      } else {
        await terrainStageRef.current?.requestFullscreen();
      }
    } catch (error) {
      console.error("Unable to toggle map fullscreen:", error);
    }
  };
  const [corridorThreshold, setCorridorThreshold] = useState(1000);

  const toggleLayer = (name) => setLayers((prev) =>
    prev.map((layer) => layer.name === name ? { ...layer, enabled: !layer.enabled } : layer)
  );
  const isEnabled = (name) => layers.find((layer) => layer.name === name)?.enabled ?? false;

  return (
    <div className={`terrain-workspace ${compact ? "terrain-workspace-compact" : ""}`}>
      <div className={`terrain-visual ${isFullscreen ? "terrain-visual-fullscreen" : ""}`} ref={terrainStageRef}>
        <button className="terrain-fullscreen-button" onClick={toggleFullscreen} type="button" aria-label={isFullscreen ? "Exit fullscreen map" : "View map fullscreen"} title={isFullscreen ? "Exit fullscreen (Esc)" : "View fullscreen"}>
          {isFullscreen ? <><Minimize2 size={16} /> Exit full screen</> : <><Maximize2 size={16} /> Full screen</>}
        </button>
        <div className="terrain-viewer-container">
          <TerrainViewer
            showTerrain={isEnabled("Terrain surface")}
            showLakeWater={isEnabled("Lake water")}
            showLakeBoundary={isEnabled("Lake boundary")}
            showCatchment={isEnabled("Catchment boundary")}
            showDrainage={isEnabled("Drainage network")}
            showCorridor={isEnabled("Potential flow corridor")}
            corridorThreshold={corridorThreshold}
          />
        </div>
        <div className="terrain-legend">
          <span><i className="legend-dot terrain-dot" /> Terrain</span>
          <span><i className="legend-dot lake-dot" /> Lake boundary / water</span>
          <span><i className="legend-dot drainage-dot" /> Drainage network</span>
          <span><i className="legend-dot corridor-dot" /> Potential corridor</span>
        </div>
      </div>
      <aside className="terrain-controls">
        <div className="control-heading"><span className="section-kicker">VISIBILITY</span><Layers3 size={16} /></div>
        <div className="layer-list">
          {layers.map((layer) => (
            <button key={layer.name} className="layer-row" onClick={() => toggleLayer(layer.name)} type="button">
              <span>{layer.name}</span>{layer.enabled ? <Eye size={15} className="enabled-eye" /> : <EyeOff size={15} className="disabled-eye" />}
            </button>
          ))}
        </div>
        <div className="threshold-control">
          <div className="threshold-title"><strong>Corridor threshold</strong><span>FLOW ACCUMULATION</span></div>
          <div className="threshold-options">
            {[500, 1000, 5000].map((value) => (
              <button key={value} className={corridorThreshold === value ? "selected" : ""} onClick={() => setCorridorThreshold(value)} type="button">{value.toLocaleString()}</button>
            ))}
          </div>
          <div className="threshold-stat">
            <span>Screened corridor area</span>
            <strong>{corridorThreshold === 500 ? "162.76" : corridorThreshold === 1000 ? "140.13" : "90.69"} ha</strong>
          </div>
          <p>Terrain-derived screening layer only. Not a predicted inundation footprint.</p>
        </div>
        <div className="terrain-meta">
          <div><span>CRS</span><strong>EPSG:32643</strong></div>
          <div><span>GRID</span><strong>8 m</strong></div>
          <div><span>ROUTE</span><strong>Provisional D8</strong></div>
        </div>
      </aside>
    </div>
  );
}

function LakeMonitoring() {
  return (
    <div className="lake-page">
      <div className="metrics-grid lake-metrics">
        <MetricCard label="25 SEP 2026" value="155.04" unit="ha" detail="NDWI threshold 0.30" icon={Waves} tone="cyan" />
        <MetricCard label="05 OCT 2026" value="155.19" unit="ha" detail="NDWI threshold 0.30" icon={Waves} tone="blue" />
        <MetricCard label="APPARENT DIFFERENCE" value="+0.149" unit="ha" detail="+0.096% · threshold-sensitive" icon={Activity} tone="amber" />
      </div>
      <div className="panel lake-observation-panel">
        <div className="panel-heading"><div><span className="section-kicker">TEMPORAL OBSERVATION</span><h2>Extracted lake area</h2></div><span className="status-pill status-amber">NOT ROBUSTLY ESTABLISHED</span></div>
        <div className="lake-bars">
          <div className="lake-bar-group"><div className="lake-bar-value">155.04 ha</div><div className="lake-bar lake-bar-one" /><span>25 Sep 2026</span></div>
          <div className="lake-bar-group"><div className="lake-bar-value">155.19 ha</div><div className="lake-bar lake-bar-two" /><span>05 Oct 2026</span></div>
        </div>
        <p className="chart-caption">Both observations use NDWI = 0.30. Threshold sensitivity changes the apparent temporal difference, so this small increase should not be interpreted as confirmed lake expansion.</p>
      </div>
      <div className="panel lake-terrain-panel">
        <div className="panel-heading"><div><span className="section-kicker">SPATIAL CONTEXT</span><h2>Lake and catchment terrain</h2></div><span className="data-state"><span className="state-dot" /> 3D MODEL</span></div>
        <TerrainWorkspace compact />
      </div>
    </div>
  );
}

function PredictiveAnalysis() {
  const [selectedRank, setSelectedRank] = useState("10%");
  const topK = [
    { rank: "1%", lakes: 65, found: 3, precision: "4.62%", recall: "6.67%" },
    { rank: "5%", lakes: 321, found: 6, precision: "1.87%", recall: "13.33%" },
    { rank: "10%", lakes: 641, found: 11, precision: "1.72%", recall: "24.44%" },
    { rank: "20%", lakes: 1282, found: 15, precision: "1.17%", recall: "33.33%" },
  ];
  const selected = topK.find((item) => item.rank === selectedRank);
  const featureImportance = [
    { label: "Log lake perimeter", value: 26.50 },
    { label: "Lake elevation", value: 25.62 },
    { label: "Log lake area", value: 24.26 },
    { label: "Log shape complexity", value: 23.62 },
    { label: "Log elongation", value: 0.00 },
  ];

  return (
    <div className="prediction-page">
      <div className="model-banner">
        <div className="model-banner-icon"><BrainCircuit size={23} /></div>
        <div className="model-banner-copy">
          <span className="section-kicker">HISTORICAL RECORD CLASSIFIER</span>
          <h2>Random Forest · exploratory baseline</h2>
          <p>Ranks lake inventory records by similarity to documented historical GLOF lakes using five morphology and elevation features.</p>
        </div>
        <div className="model-banner-status"><span className="status-pill status-amber">WEAK DISCRIMINATION</span><small>Not operational</small></div>
      </div>

      <div className="prediction-dataset-strip">
        <DatasetStat value="31,698" label="HMA lake polygons" />
        <DatasetStat value="227" label="Matched event lakes" />
        <DatasetStat value="6,407" label="Geographic test lakes" />
        <DatasetStat value="45" label="Positive test lakes" />
      </div>

      <div className="prediction-section-heading">
        <div><span className="section-kicker">GEOGRAPHIC HOLDOUT</span><h2>Model performance</h2></div>
        <span className="muted-caption">20% spatially grouped test split · threshold 0.5</span>
      </div>

      <div className="performance-grid">
        <PerformanceCard label="ROC-AUC" value="0.5767" detail="Weak ranking discrimination" tone="amber" />
        <PerformanceCard label="PR-AUC" value="0.0240" detail="Baseline prevalence: 0.0070" tone="blue" />
        <PerformanceCard label="RECALL" value="2.22%" detail="1 of 45 positive test lakes found" tone="red" />
        <PerformanceCard label="PRECISION" value="25.00%" detail="1 true positive among 4 alerts" tone="violet" />
      </div>

      <div className="prediction-analysis-grid">
        <section className="panel topk-panel">
          <div className="panel-heading"><div><span className="section-kicker">RANKING ANALYSIS</span><h2>Top-ranked lake screening</h2></div><BarChart3 size={18} className="muted-icon" /></div>
          <p className="panel-intro">How many documented GLOF lakes appear when reviewing the highest-scoring portion of the held-out test inventory?</p>
          <div className="rank-selector">
            {topK.map((item) => <button key={item.rank} className={selectedRank === item.rank ? "selected" : ""} onClick={() => setSelectedRank(item.rank)}>{item.rank}</button>)}
          </div>
          <div className="rank-highlight">
            <div><span>DOCUMENTED EVENTS FOUND</span><strong>{selected.found}<small> / 45</small></strong></div>
            <div><span>RECALL AT K</span><strong>{selected.recall}</strong></div>
          </div>
          <div className="rank-bar-chart">
            {topK.map((item) => (
              <button className={`rank-bar-item ${selectedRank === item.rank ? "active" : ""}`} key={item.rank} onClick={() => setSelectedRank(item.rank)}>
                <span className="rank-bar-label">{item.rank}</span>
                <span className="rank-bar-track"><i style={{ width: `${Number(item.recall.replace("%", ""))}%` }} /></span>
                <strong>{item.recall}</strong>
              </button>
            ))}
          </div>
          <div className="rank-detail-grid">
            <div><span>LAKES REVIEWED</span><strong>{selected.lakes.toLocaleString()}</strong></div>
            <div><span>PRECISION AT K</span><strong>{selected.precision}</strong></div>
          </div>
          <p className="chart-caption">Top-K values are a post-hoc screening analysis of the geographic holdout set, not a validated operational alert threshold.</p>
        </section>

        <section className="panel importance-panel">
          <div className="panel-heading"><div><span className="section-kicker">MODEL EXPLANATION</span><h2>Feature importance</h2></div><Zap size={18} className="muted-icon" /></div>
          <p className="panel-intro">Relative impurity-based importance reported by the fitted Random Forest model.</p>
          <div className="importance-list">
            {featureImportance.map((item, index) => (
              <div className="importance-row" key={item.label}>
                <div className="importance-label"><span>{item.label}</span><strong>{item.value.toFixed(2)}%</strong></div>
                <div className="importance-track"><i className={`importance-fill importance-${index}`} style={{ width: `${item.value}%` }} /></div>
              </div>
            ))}
          </div>
          <div className="importance-note"><AlertTriangle size={14} /> Feature importance is model-specific and does not establish causation or physical hazard significance.</div>
        </section>
      </div>

      <section className="panel confusion-panel">
        <div className="panel-heading"><div><span className="section-kicker">CLASSIFICATION AT 0.5 THRESHOLD</span><h2>Holdout confusion matrix</h2></div><span className="status-pill status-red">LOW EVENT RECALL</span></div>
        <div className="confusion-grid">
          <div className="confusion-cell true-negative"><span>TRUE NEGATIVES</span><strong>6,359</strong><small>Candidate negatives correctly classified</small></div>
          <div className="confusion-cell false-positive"><span>FALSE POSITIVES</span><strong>3</strong><small>Candidate negatives flagged</small></div>
          <div className="confusion-cell false-negative"><span>FALSE NEGATIVES</span><strong>44</strong><small>Documented event lakes missed</small></div>
          <div className="confusion-cell true-positive"><span>TRUE POSITIVES</span><strong>1</strong><small>Documented event lake detected</small></div>
        </div>
      </section>

      <div className="model-caveat">
        <ShieldAlert size={18} />
        <div>
          <strong>Interpretation and safety boundary</strong>
          <p>Positive labels mean a historical GLOF record matched a 2022 inventory lake within 1 km. Candidate negatives mean no matching record was found—not that a lake is confirmed safe. Scores are not calibrated GLOF probabilities and must not be used for evacuation, engineering or operational warning decisions.</p>
        </div>
      </div>
    </div>
  );
}

function DatasetStat({ value, label }) {
  return <div className="dataset-stat"><strong>{value}</strong><span>{label}</span></div>;
}

function PerformanceCard({ label, value, detail, tone }) {
  return <div className="performance-card panel"><span>{label}</span><strong className={`performance-${tone}`}>{value}</strong><small>{detail}</small></div>;
}

function ScenarioExplorer() {
  const [scenario, setScenario] = useState("observed");
  return (
    <div className="scenario-page">
      <div className="scenario-intro panel">
        <div className="scenario-intro-icon"><AlertTriangle size={21} /></div>
        <div><span className="section-kicker">NRSC REFERENCE SCENARIO MATRIX</span><h2>Conditional stress-test framework</h2><p>Eight predefined hypothetical scenarios have been assembled. No hydrodynamic breach or inundation simulation has been run.</p></div>
      </div>
      <div className="scenario-switcher">
        <button className={scenario === "observed" ? "selected" : ""} onClick={() => setScenario("observed")}>Observed terrain context</button>
        <button className={scenario === "nrsc" ? "selected" : ""} onClick={() => setScenario("nrsc")}>NRSC scenarios 7–8</button>
      </div>
      <div className="scenario-detail-grid">
        <div className="panel scenario-detail">
          <span className="section-kicker">{scenario === "nrsc" ? "HYPOTHETICAL REFERENCE CASE" : "AVAILABLE OBSERVATIONS"}</span>
          <h2>{scenario === "nrsc" ? "Inclement-weather breach stress test" : "Terrain-derived drainage context"}</h2>
          {scenario === "nrsc" ? (
            <>
              <div className="scenario-parameter"><span>Lake release assumption</span><strong>100%</strong></div>
              <div className="scenario-parameter"><span>Weather condition</span><strong>Inclement</strong></div>
              <div className="scenario-parameter"><span>Additional condition</span><strong>Ghepang Ghat 100% breach</strong></div>
              <p className="chart-caption">NRSC scenarios 7 and 8 are reference assumptions only. No discharge hydrograph or flood arrival time is available.</p>
            </>
          ) : (
            <>
              <div className="scenario-parameter"><span>Terrain-derived D8 trace</span><strong>47.46 km</strong></div>
              <div className="scenario-parameter"><span>Catchment representation</span><strong>Candidate 14</strong></div>
              <div className="scenario-parameter"><span>Lake outlet connection</span><strong>Provisional</strong></div>
              <p className="chart-caption">The drainage trace is a DEM-derived pathway, not a validated flood route or inundation footprint.</p>
            </>
          )}
        </div>
        <div className="panel scenario-limitations">
          <span className="section-kicker">REQUIRED BEFORE FLOOD SIMULATION</span>
          <h2>Outstanding inputs</h2>
          <PipelineRow label="Lake bathymetry and volume" status="Missing" warning />
          <PipelineRow label="Breach geometry and hydrograph" status="Missing" warning />
          <PipelineRow label="Downstream roughness calibration" status="Missing" warning />
          <PipelineRow label="Independent inundation observations" status="Missing" warning />
        </div>
      </div>
      <div className="model-caveat"><ShieldAlert size={18} /><div><strong>Not a flood forecast</strong><p>Scenario selection changes the displayed reference assumptions only. It does not run a hydraulic model or produce predicted flood depths, extents or arrival times.</p></div></div>
    </div>
  );
}

function InsightRow({ label, value, note, tone }) {
  return <div className="insight-row"><div><span>{label}</span><small>{note}</small></div><strong className={`insight-${tone}`}>{value}</strong></div>;
}

function PipelineRow({ label, status, warning = false }) {
  return <div className="pipeline-row"><span>{label}</span><strong className={warning ? "pipeline-warning" : "pipeline-complete"}>{status}</strong></div>;
}

function QuickLink({ icon: Icon, title, subtitle, onClick }) {
  return <button className="quick-link" onClick={onClick}><span className="quick-link-icon"><Icon size={17} /></span><span><strong>{title}</strong><small>{subtitle}</small></span><ChevronRight size={16} /></button>;
}

export default App;
