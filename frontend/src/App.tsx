import { useState } from "react";

type NavKey = "overview" | "vessels" | "documents" | "loading" | "reports";

const navigation: { key: NavKey; label: string; icon: string }[] = [
  { key: "overview", label: "Overview", icon: "◫" },
  { key: "vessels", label: "Vessels", icon: "▤" },
  { key: "documents", label: "Documents", icon: "▧" },
  { key: "loading", label: "Loading conditions", icon: "⌁" },
  { key: "reports", label: "Calculation runs", icon: "▥" },
];

function App() {
  const [active, setActive] = useState<NavKey>("overview");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">S</span><span>ShipLoad<small>VESSEL WORKSPACE</small></span></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {navigation.map((item) => (
            <button key={item.key} className={active === item.key ? "nav-item active" : "nav-item"} onClick={() => setActive(item.key)}>
              <span className="nav-icon">{item.icon}</span>{item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection"><span /> Local project scaffold</div>
          <div className="user-row"><div className="avatar">Q</div><div>Project owner<small>ShipLoad development</small></div></div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div><span className="breadcrumb">Workspace</span><span className="slash">/</span><strong>{navigation.find((item) => item.key === active)?.label}</strong></div>
          <div className="topbar-right"><span className="env-tag">DEVELOPMENT</span><button className="help-button">Documentation ↗</button></div>
        </header>

        <section className="content">
          <div className="page-heading">
            <div><div className="eyebrow">MARITIME OPERATIONS / ENGINEERING</div><h1>{active === "overview" ? "Vessel workspace" : navigation.find((item) => item.key === active)?.label}</h1><p>Manage vessel data, review source documents and prepare traceable loading conditions.</p></div>
            <button className="primary-button" onClick={() => setActive("vessels")}>＋ Add vessel</button>
          </div>

          <div className="notice"><span className="notice-icon">!</span><div><strong>Development environment — not approved for operational use</strong><p>No stability or loading calculation is currently available. Do not use this application to make vessel safety decisions.</p></div></div>

          <div className="metric-grid">
            <Metric label="VESSELS" value="0" detail="No vessel profiles yet" />
            <Metric label="SOURCE DOCUMENTS" value="0" detail="Awaiting first upload" />
            <Metric label="LOADING CONDITIONS" value="0" detail="No conditions created" />
            <Metric label="VALIDATED RUNS" value="0" detail="No reference cases configured" />
          </div>

          <div className="section-grid">
            <section className="panel getting-started">
              <div className="panel-heading"><div><div className="eyebrow">GETTING STARTED</div><h2>Set up your first vessel</h2></div><span className="step-count">0 / 4</span></div>
              <SetupStep number="01" title="Create vessel profile" description="Enter principal particulars, coordinate system and reference datums." />
              <SetupStep number="02" title="Upload approved documentation" description="Add the stability booklet, hydrostatic tables and tank calibration data." />
              <SetupStep number="03" title="Review extracted data" description="Verify each imported value against its original page and table." />
              <SetupStep number="04" title="Build a loading condition" description="Add lightship, cargo, consumables, ballast and other variable weights." />
              <button className="secondary-button" onClick={() => setActive("vessels")}>Start vessel setup <span>→</span></button>
            </section>
            <section className="panel status-panel">
              <div className="eyebrow">SYSTEM STATUS</div><h2>Calculation services</h2>
              <StatusRow name="Vessel data registry" status="Not configured" />
              <StatusRow name="Document extraction" status="Not implemented" />
              <StatusRow name="Hydrostatic calculation" status="Not implemented" />
              <StatusRow name="Stability criteria checks" status="Not implemented" />
              <StatusRow name="Report generation" status="Not implemented" />
              <div className="status-foot">Services will be enabled only after their validation requirements are met.</div>
            </section>
          </div>

          <div className="bottom-note"><span>SHIPLOAD</span><span>Data provenance first · Reproducible calculations · Explicit validation status</span><span>v0.1.0</span></div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function SetupStep({ number, title, description }: { number: string; title: string; description: string }) {
  return <div className="setup-step"><span className="step-number">{number}</span><div><strong>{title}</strong><p>{description}</p></div><span className="step-arrow">→</span></div>;
}

function StatusRow({ name, status }: { name: string; status: string }) {
  return <div className="status-row"><span className="status-dot" /><span>{name}</span><small>{status}</small></div>;
}

export default App;
