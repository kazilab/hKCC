// hKCC — Browse carcinogens

function ScreenCarcinogens({ onNav }) {
  const all = window.CARCINOGENS;
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("all");
  const [type, setType] = useState("all");
  const [sort, setSort] = useState("name"); // name | coverage | weight

  const types = ["all", ...Array.from(new Set(all.map(c => c.type)))];

  const filtered = useMemo(() => {
    let r = all.slice();
    if (q) {
      const ql = q.toLowerCase();
      r = r.filter(c => c.name.toLowerCase().includes(ql) || c.cas.includes(q) || c.type.toLowerCase().includes(ql));
    }
    if (group !== "all") r = r.filter(c => c.group === group);
    if (type !== "all") r = r.filter(c => c.type === type);
    if (sort === "name") r.sort((a, b) => a.name.localeCompare(b.name));
    if (sort === "coverage") r.sort((a, b) => kccCoverage(b) - kccCoverage(a));
    if (sort === "weight") r.sort((a, b) => totalEvidence(b) - totalEvidence(a));
    return r;
  }, [q, group, type, sort, all]);

  return (
    <div className="content">
      <SectionHead
        eyebrow="The database"
        title={`Carcinogens & suspect agents (${all.length})`}
        sub="Searchable curated list of agents with mechanistic evidence assessed against the 14 key characteristics. Click any row to open the full profile."
      />

      {/* Controls */}
      <div className="card flat" style={{ background: "var(--paper-2)", padding: 16, marginBottom: 20 }}>
        <div className="flex" style={{ gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div className="search" style={{ margin: 0, width: 280 }}>
            <svg width="14" height="14" viewBox="0 0 14 14"><circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.2" fill="none"/><line x1="9.5" y1="9.5" x2="12.5" y2="12.5" stroke="currentColor" strokeWidth="1.2"/></svg>
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name, CAS, type…" />
          </div>
          <div className="flex gap-4">
            <span className="mono-sm" style={{ alignSelf: "center", marginRight: 6 }}>GROUP</span>
            {["all", "1", "2A", "2B", "—"].map(g => (
              <button key={g} className={`chip ${group === g ? "accent" : "outline"}`} style={{ cursor: "pointer", border: "none" }} onClick={() => setGroup(g)}>
                {g === "all" ? "All" : g === "—" ? "N/C" : `Group ${g}`}
              </button>
            ))}
          </div>
          <select value={type} onChange={e => setType(e.target.value)}
                  style={{ fontFamily: "inherit", fontSize: 12, padding: "6px 10px", background: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 4, color: "var(--ink)" }}>
            {types.map(t => <option key={t} value={t}>{t === "all" ? "All types" : t}</option>)}
          </select>
          <div className="flex gap-4" style={{ marginLeft: "auto", alignItems: "center" }}>
            <span className="mono-sm">SORT</span>
            <button className={`tab ${sort === "name" ? "active" : ""}`} onClick={() => setSort("name")} style={{ padding: "4px 8px" }}>A–Z</button>
            <button className={`tab ${sort === "coverage" ? "active" : ""}`} onClick={() => setSort("coverage")} style={{ padding: "4px 8px" }}>KCC coverage</button>
            <button className={`tab ${sort === "weight" ? "active" : ""}`} onClick={() => setSort("weight")} style={{ padding: "4px 8px" }}>Evidence weight</button>
          </div>
        </div>
      </div>

      <div className="mono-sm mb-12">Showing {filtered.length} of {all.length} agents</div>

      <table className="data">
        <thead>
          <tr>
            <th>Agent</th>
            <th>CAS</th>
            <th>Type</th>
            <th>IARC</th>
            <th>Tumour sites</th>
            <th>KCC fingerprint (14)</th>
            <th className="num">Coverage</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map(c => (
            <tr key={c.id} className="row-hover" onClick={() => onNav("carcDetail", { id: c.id })}>
              <td><span style={{ fontFamily: "var(--font-serif)", fontSize: 16 }}>{c.name}</span></td>
              <td className="mono-sm">{c.cas}</td>
              <td className="text-muted" style={{ fontSize: 12.5 }}>{c.type}</td>
              <td><GroupChip g={c.group} /></td>
              <td className="text-muted" style={{ fontSize: 12.5, maxWidth: 220 }}>{c.sites.join(", ")}</td>
              <td>
                <div className="flex" style={{ gap: 2 }}>
                  {window.KCCS.map(k => <EvCell key={k.id} v={c.evidence[k.id]} title={`${k.short}: ${c.evidence[k.id]}/4`} />)}
                </div>
              </td>
              <td className="num">{kccCoverage(c)}/14</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-24 flex" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <EvLegend />
        <div className="flex gap-8">
          <button className="btn ghost">↓ Export CSV</button>
          <button className="btn ghost">↓ JSON</button>
        </div>
      </div>

      <PageFoot />
    </div>
  );
}

// Per-carcinogen detail
function ScreenCarcDetail({ id, onNav }) {
  const c = window.CARCINOGENS.find(x => x.id === id);
  if (!c) return <div className="content">Agent not found.</div>;
  const kccs = window.KCCS;
  const [tab, setTab] = useState("kccs");

  const cov = kccCoverage(c);
  const weight = totalEvidence(c);
  const max = kccs.length * 4;

  // Radar
  const radar = useMemo(() => {
    const n = kccs.length;
    const cx = 180, cy = 180, R = 140;
    const pts = kccs.map((k, i) => {
      const a = (Math.PI * 2 * i) / n - Math.PI / 2;
      const v = c.evidence[k.id] / 4;
      return { x: cx + Math.cos(a) * R * v, y: cy + Math.sin(a) * R * v, ax: cx + Math.cos(a) * R, ay: cy + Math.sin(a) * R, label: k.short, n: k.n };
    });
    return { cx, cy, R, pts };
  }, [c]);

  return (
    <div className="content">
      <button className="mono-sm" onClick={() => onNav("carcinogens")} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--muted)" }}>← All agents</button>

      <div className="flex mt-16" style={{ gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div className="flex gap-12" style={{ alignItems: "center" }}>
            <GroupChip g={c.group} />
            <span className="mono-sm">{c.type}</span>
            {c.cas !== "—" && <span className="mono-sm">· CAS {c.cas}</span>}
          </div>
          <h1 className="h-display mt-12" style={{ fontSize: 72 }}>{c.name}</h1>
          <p className="lede mt-20">{c.summary}</p>
        </div>
      </div>

      <hr className="rule-thick mt-32" />

      <div className="stat-row">
        <div className="stat"><div className="v">{cov}<span style={{ fontSize: 22, color: "var(--muted)" }}>/14</span></div><div className="l">KCC coverage (ev ≥ 2)</div></div>
        <div className="stat"><div className="v">{weight}<span style={{ fontSize: 22, color: "var(--muted)" }}>/{max}</span></div><div className="l">Total weighted score</div></div>
        <div className="stat"><div className="v">{c.sites.length}</div><div className="l">Associated tumour sites</div></div>
        <div className="stat"><div className="v">42</div><div className="l">Curated references</div></div>
      </div>

      <hr className="rule mt-32" />

      <div className="tabs">
        {[
          { id: "kccs", label: "KCC fingerprint" },
          { id: "evidence", label: "Detailed evidence" },
          { id: "sites", label: "Tumour sites" },
          { id: "refs", label: "References" }
        ].map(t => (
          <button key={t.id} className={`tab ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>{t.label}</button>
        ))}
      </div>

      {tab === "kccs" && (
        <div className="grid-2" style={{ gap: 48 }}>
          {/* Radar */}
          <div>
            <span className="eyebrow">Radar plot</span>
            <h3 className="h-sub mt-12">Evidence fingerprint across 14 KCCs</h3>
            <svg viewBox="0 0 360 360" style={{ width: "100%", maxWidth: 360, marginTop: 16, display: "block" }}>
              {[1, 0.75, 0.5, 0.25].map(r => (
                <circle key={r} cx={radar.cx} cy={radar.cy} r={radar.R * r} fill="none" stroke="var(--rule)" strokeWidth="1" />
              ))}
              {radar.pts.map((p, i) => (
                <line key={i} x1={radar.cx} y1={radar.cy} x2={p.ax} y2={p.ay} stroke="var(--rule)" strokeWidth="1" />
              ))}
              <polygon
                points={radar.pts.map(p => `${p.x},${p.y}`).join(" ")}
                fill="var(--accent)" fillOpacity="0.18"
                stroke="var(--accent)" strokeWidth="1.5"
              />
              {radar.pts.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="3" fill="var(--accent)" />)}
              {radar.pts.map((p, i) => {
                const a = (Math.PI * 2 * i) / kccs.length - Math.PI / 2;
                const lx = radar.cx + Math.cos(a) * (radar.R + 16);
                const ly = radar.cy + Math.sin(a) * (radar.R + 16);
                return (
                  <text key={i} x={lx} y={ly} fontSize="9.5" fontFamily="var(--font-mono)" fill="var(--muted)" textAnchor="middle" dominantBaseline="middle" letterSpacing="0.04em">
                    {String(p.n).padStart(2, "0")}
                  </text>
                );
              })}
            </svg>
          </div>
          {/* List */}
          <div>
            <span className="eyebrow">All 14 KCCs</span>
            <h3 className="h-sub mt-12">Tap a KCC to inspect its assays and literature</h3>
            <div className="flex flex-col mt-16" style={{ gap: 1 }}>
              {kccs.map(k => {
                const v = c.evidence[k.id];
                return (
                  <button key={k.id} onClick={() => onNav("kccDetail", { id: k.id })}
                          className="card-hover"
                          style={{ background: "var(--paper-2)", border: "none", borderBottom: "1px solid var(--rule)", padding: "10px 14px", display: "grid", gridTemplateColumns: "36px 28px 1fr 110px", gap: 12, alignItems: "center", cursor: "pointer", textAlign: "left", fontFamily: "inherit", color: "var(--ink)" }}>
                    <span className="mono-sm">{String(k.n).padStart(2, "0")}</span>
                    <KCCGlyph kind={k.icon} size={20} color={k.color} />
                    <span style={{ fontSize: 14 }}>{k.short}</span>
                    <EvBar v={v} />
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {tab === "evidence" && (
        <div>
          <span className="eyebrow">Detailed evidence</span>
          <h3 className="h-sub mt-12">Curator notes by KCC</h3>
          <div className="flex flex-col gap-16 mt-20">
            {kccs.filter(k => c.evidence[k.id] >= 1).map(k => (
              <article key={k.id} className="card">
                <div className="flex gap-12" style={{ alignItems: "center" }}>
                  <KCCGlyph kind={k.icon} size={20} color={k.color} />
                  <div style={{ fontFamily: "var(--font-serif)", fontSize: 20 }}>{k.title}</div>
                  <div style={{ marginLeft: "auto" }}><EvBar v={c.evidence[k.id]} /></div>
                </div>
                <p className="prose mt-12">{k.mechanism}</p>
                <div className="mono-sm mt-12">Anchored to: {Math.max(2, c.evidence[k.id] * 3)} curated references · last reviewed 2025-11</div>
              </article>
            ))}
          </div>
        </div>
      )}

      {tab === "sites" && (
        <div>
          <span className="eyebrow">Tumour sites</span>
          <h3 className="h-sub mt-12">Associated cancers (IARC monograph)</h3>
          <div className="flex flex-col gap-8 mt-16">
            {c.sites.map(s => (
              <div key={s} className="card flex" style={{ alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontFamily: "var(--font-serif)", fontSize: 20 }}>{s}</span>
                <span className="mono-sm">Sufficient evidence in humans</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "refs" && (
        <div>
          <span className="eyebrow">References</span>
          <h3 className="h-sub mt-12">Underlying citations · {window.LITERATURE.length} on file</h3>
          <div className="flex flex-col gap-12 mt-20">
            {window.LITERATURE.map(ref => (
              <article key={ref.id} className="flex" style={{ alignItems: "baseline", gap: 16, padding: "10px 0", borderBottom: "1px solid var(--rule)" }}>
                <span className="mono-sm" style={{ minWidth: 50, color: "var(--accent)" }}>{ref.year}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: 1.25 }}>{ref.title}</div>
                  <div className="mono-sm mt-4">{ref.authors} · <em style={{ fontStyle: "italic" }}>{ref.journal}</em>, {ref.vol}</div>
                </div>
                <span className="mono-sm">{ref.cites} cites</span>
              </article>
            ))}
          </div>
        </div>
      )}

      <PageFoot />
    </div>
  );
}

window.ScreenCarcinogens = ScreenCarcinogens;
window.ScreenCarcDetail = ScreenCarcDetail;
