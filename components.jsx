// hKCC shared components

const { useState, useMemo, useEffect, useRef } = React;

// Tiny SVG glyph for each KCC — abstract, never literal
function KCCGlyph({ kind, size = 22, color = "currentColor" }) {
  const s = size;
  const stroke = { stroke: color, strokeWidth: 1.4, fill: "none", strokeLinecap: "round", strokeLinejoin: "round" };
  const fill = { fill: color };
  const shapes = {
    circle: <circle cx={s/2} cy={s/2} r={s/2 - 3} {...stroke} />,
    helix: <g {...stroke}>
      <path d={`M 4 4 Q ${s/2} ${s/2} ${s-4} 4`} />
      <path d={`M 4 ${s-4} Q ${s/2} ${s/2} ${s-4} ${s-4}`} />
      <line x1="6" y1={s/2} x2={s-6} y2={s/2} />
    </g>,
    grid: <g {...stroke}>
      <rect x="4" y="4" width={s-8} height={s-8} />
      <line x1="4" y1={s/2} x2={s-4} y2={s/2} />
      <line x1={s/2} y1="4" x2={s/2} y2={s-4} />
    </g>,
    marks: <g {...stroke}>
      <line x1="5" y1={s-6} x2={s-5} y2={s-6} />
      <circle cx="8" cy={s-10} r="2" {...fill} />
      <circle cx={s-8} cy={s-10} r="2" />
      <circle cx={s/2} cy={s-10} r="2" {...fill} />
    </g>,
    rays: <g {...stroke}>
      <circle cx={s/2} cy={s/2} r="3" {...fill} />
      <line x1={s/2} y1="3" x2={s/2} y2="7" />
      <line x1={s/2} y1={s-7} x2={s/2} y2={s-3} />
      <line x1="3" y1={s/2} x2="7" y2={s/2} />
      <line x1={s-7} y1={s/2} x2={s-3} y2={s/2} />
      <line x1="6" y1="6" x2="9" y2="9" />
      <line x1={s-9} y1={s-9} x2={s-6} y2={s-6} />
      <line x1={s-9} y1="9" x2={s-6} y2="6" />
      <line x1="6" y1={s-6} x2="9" y2={s-9} />
    </g>,
    burst: <g {...stroke}>
      <polygon points={`${s/2},3 ${s-5},${s/2} ${s/2},${s-3} 5,${s/2}`} />
    </g>,
    shield: <g {...stroke}>
      <path d={`M ${s/2} 4 L ${s-5} 7 L ${s-5} ${s/2} Q ${s-5} ${s-5} ${s/2} ${s-4} Q 5 ${s-5} 5 ${s/2} L 5 7 Z`} />
    </g>,
    diamond: <g {...stroke}>
      <polygon points={`${s/2},4 ${s-4},${s/2} ${s/2},${s-4} 4,${s/2}`} />
      <line x1={s/2} y1="8" x2={s/2} y2={s-8} />
    </g>,
    loop: <g {...stroke}>
      <ellipse cx={s/2} cy={s/2} rx={s/2 - 4} ry={s/4} />
      <ellipse cx={s/2} cy={s/2} rx={s/4} ry={s/2 - 4} />
    </g>,
    wave: <g {...stroke}>
      <path d={`M 3 ${s/2} Q ${s/4} 4 ${s/2} ${s/2} T ${s-3} ${s/2}`} />
    </g>,
    dots: <g {...fill}>
      <circle cx="6" cy="6" r="1.6" />
      <circle cx={s/2} cy="6" r="1.6" />
      <circle cx={s-6} cy="6" r="1.6" />
      <circle cx="6" cy={s/2} r="1.6" />
      <circle cx={s/2} cy={s/2} r="1.6" />
      <circle cx={s-6} cy={s/2} r="1.6" />
      <circle cx="6" cy={s-6} r="1.6" />
      <circle cx={s/2} cy={s-6} r="1.6" />
      <circle cx={s-6} cy={s-6} r="1.6" />
    </g>,
    fade: <g {...stroke}>
      <line x1="4" y1="6" x2={s-4} y2="6" />
      <line x1="4" y1={s/2} x2={s-7} y2={s/2} opacity="0.6" />
      <line x1="4" y1={s-6} x2={s-10} y2={s-6} opacity="0.3" />
    </g>,
    tree: <g {...stroke}>
      <line x1={s/2} y1={s-4} x2={s/2} y2={s/2} />
      <line x1={s/2} y1={s/2} x2="6" y2="6" />
      <line x1={s/2} y1={s/2} x2={s-6} y2="6" />
      <line x1={s/2} y1={s-8} x2="8" y2={s-10} />
      <line x1={s/2} y1={s-8} x2={s-8} y2={s-10} />
    </g>,
    link: <g {...stroke}>
      <rect x="3" y={s/2-3} width="8" height="6" rx="3" />
      <rect x={s-11} y={s/2-3} width="8" height="6" rx="3" />
      <line x1="11" y1={s/2} x2={s-11} y2={s/2} />
    </g>
  };
  return <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">{shapes[kind] || shapes.circle}</svg>;
}

// Evidence cell — colored swatch, hover tooltip handled by parent
function EvCell({ v, title }) {
  return <span className={`ev ev-${v}`} title={title || `Evidence ${v}/4`} />;
}

// Evidence dot variant
function EvDot({ v }) {
  return <span className={`ev-dot ev-${v}`} />;
}

// Evidence bar (horizontal mini)
function EvBar({ v, max = 4 }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{
        position: "relative", display: "inline-block",
        width: 80, height: 6, background: "var(--paper-3)", borderRadius: 2, overflow: "hidden"
      }}>
        <span style={{
          position: "absolute", left: 0, top: 0, bottom: 0,
          width: `${(v/max)*100}%`,
          background: `var(--ev-${v})`
        }} />
      </span>
      <span className="mono-sm" style={{ minWidth: 24 }}>{v}/{max}</span>
    </span>
  );
}

// Group badge
function GroupChip({ g }) {
  const cls = g === "1" ? "group1" : g === "2A" ? "group2a" : g === "2B" ? "group2b" : "group3";
  const label = g === "—" ? "Not classified" : `Group ${g}`;
  return <span className={`chip ${cls}`}>{label}</span>;
}

// Evidence legend
function EvLegend() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--muted)", letterSpacing: "0.06em" }}>
      <span>EVIDENCE</span>
      {[0,1,2,3,4].map(v => (
        <span key={v} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
          <EvCell v={v} /> <span>{v === 0 ? "none" : v === 1 ? "weak" : v === 2 ? "moderate" : v === 3 ? "strong" : "definitive"}</span>
        </span>
      ))}
    </div>
  );
}

// Sidebar nav
function Sidebar({ route, onNav, tweaks }) {
  const items = [
    { sec: "Browse" },
    { id: "home", label: "Overview", count: null },
    { id: "kccs", label: "The 14 KCCs", count: 14 },
    { id: "carcinogens", label: "Carcinogens", count: window.CARCINOGENS.length },
    { sec: "Analyze" },
    { id: "matrix", label: "Evidence matrix", count: null },
    { id: "assays", label: "Assays & methods", count: window.ASSAYS.length },
    { id: "literature", label: "Literature", count: window.LITERATURE.length },
    { sec: "Build" },
    { id: "api", label: "Data & API", count: null },
    { id: "about", label: "About hKCC", count: null }
  ];
  return (
    <aside className="sidebar">
      <div className="flex flex-col gap-8">
        <button className="brand" onClick={() => onNav("home")} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left" }}>
          <span className="brand-mark">h<span className="accent">KCC</span></span>
        </button>
        <div className="brand-sub">Key characteristics of human carcinogens</div>
      </div>
      <nav className="nav">
        {items.map((it, i) => {
          if (it.sec) return <div key={i} className="nav-section-label">{it.sec}</div>;
          return (
            <button key={it.id} className={`nav-item ${route.screen === it.id ? "active" : ""}`} onClick={() => onNav(it.id)}>
              <span>{it.label}</span>
              {it.count != null && <span className="count">{it.count}</span>}
            </button>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <div>v0.4.2 · build 1124</div>
        <div className="mt-8">Curated from IARC monographs<br/>and primary literature.</div>
        <div className="mt-8">Last sync · 2026-05-18</div>
      </div>
    </aside>
  );
}

// Topbar
function Topbar({ route, onNav }) {
  const crumbsFor = (r) => {
    const map = {
      home: ["Overview"],
      kccs: ["Browse", "The KCCs"],
      kccDetail: ["Browse", "The KCCs", r.id],
      carcinogens: ["Browse", "Carcinogens"],
      carcDetail: ["Browse", "Carcinogens", r.id],
      matrix: ["Analyze", "Evidence matrix"],
      assays: ["Analyze", "Assays & methods"],
      literature: ["Analyze", "Literature"],
      api: ["Build", "Data & API"],
      about: ["About"]
    };
    return map[r.screen] || ["—"];
  };
  const crumbs = crumbsFor(route);
  return (
    <div className="topbar">
      <div className="crumbs">
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span className="sep">/</span>}
            <span className={i === crumbs.length - 1 ? "here" : ""}>{c}</span>
          </React.Fragment>
        ))}
      </div>
      <div className="search">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.2"/><line x1="9.5" y1="9.5" x2="12.5" y2="12.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/></svg>
        <input placeholder="Search carcinogens, KCCs, assays, references…" />
        <span className="kbd">⌘K</span>
      </div>
    </div>
  );
}

// Page foot
function PageFoot() {
  return (
    <footer className="page-foot">
      <div>© 2026 hKCC consortium · CC-BY-4.0 dataset</div>
      <div>Curatorial board · Methodology · Cite this resource</div>
    </footer>
  );
}

// Section header
function SectionHead({ eyebrow, title, sub }) {
  return (
    <header className="flex flex-col gap-8 mb-24">
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <h2 className="h-section">{title}</h2>
      {sub && <p className="lede mt-8">{sub}</p>}
    </header>
  );
}

// Utility: total evidence for a carcinogen
function totalEvidence(c) {
  return Object.values(c.evidence).reduce((a, b) => a + b, 0);
}
function kccCoverage(c) {
  return Object.values(c.evidence).filter(v => v >= 2).length;
}

Object.assign(window, { KCCGlyph, EvCell, EvDot, EvBar, GroupChip, EvLegend, Sidebar, Topbar, PageFoot, SectionHead, totalEvidence, kccCoverage });
