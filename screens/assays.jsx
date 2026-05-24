// hKCC — Assays & methods library

function ScreenAssays({ onNav }) {
  const all = window.ASSAYS;
  const [kccFilter, setKccFilter] = useState("all");
  const [throughputFilter, setThroughputFilter] = useState("all");

  const filtered = all.filter(a => {
    if (kccFilter !== "all" && !a.kccs.includes(kccFilter)) return false;
    if (throughputFilter !== "all" && a.throughput !== throughputFilter) return false;
    return true;
  });

  return (
    <div className="content">
      <SectionHead
        eyebrow="Methods"
        title={`Assays & methods (${all.length})`}
        sub="Standard wet-lab and high-throughput readouts mapped to one or more KCCs. Includes OECD test guideline numbers where harmonised protocols exist."
      />

      <div className="card flat" style={{ background: "var(--paper-2)", padding: 14, marginBottom: 24 }}>
        <div className="flex gap-16" style={{ alignItems: "center", flexWrap: "wrap" }}>
          <div className="flex gap-4" style={{ alignItems: "center" }}>
            <span className="mono-sm">KCC</span>
            <select value={kccFilter} onChange={e => setKccFilter(e.target.value)}
                    style={{ fontFamily: "inherit", fontSize: 12, padding: "6px 10px", background: "var(--paper)", border: "1px solid var(--rule)", borderRadius: 4, color: "var(--ink)" }}>
              <option value="all">All KCCs</option>
              {window.KCCS.map(k => <option key={k.id} value={k.id}>{String(k.n).padStart(2,"0")} · {k.short}</option>)}
            </select>
          </div>
          <div className="flex gap-4">
            <span className="mono-sm" style={{ alignSelf: "center" }}>THROUGHPUT</span>
            {["all", "High", "Medium", "Low"].map(t => (
              <button key={t} className={`chip ${throughputFilter === t ? "accent" : "outline"}`} style={{ cursor: "pointer", border: "none" }} onClick={() => setThroughputFilter(t)}>{t}</button>
            ))}
          </div>
          <div style={{ marginLeft: "auto" }} className="mono-sm">Showing {filtered.length} / {all.length}</div>
        </div>
      </div>

      <div className="grid-2" style={{ gap: 16 }}>
        {filtered.map(a => (
          <article key={a.id} className="card">
            <div className="flex" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontFamily: "var(--font-serif)", fontSize: 22, lineHeight: 1.1 }}>{a.name}</div>
                <div className="mono-sm mt-4">{a.type} · {a.target}</div>
              </div>
              <span className="chip outline">{a.throughput} throughput</span>
            </div>
            <p className="prose mt-12" style={{ fontSize: 13 }}>{a.notes}</p>
            <div className="flex gap-8 mt-16" style={{ alignItems: "center", flexWrap: "wrap" }}>
              <span className="mono-sm">MAPS TO</span>
              {a.kccs.map(kid => {
                const k = window.KCCS.find(x => x.id === kid);
                return (
                  <button key={kid} className="chip accent" onClick={() => onNav("kccDetail", { id: kid })}
                          style={{ cursor: "pointer", border: "none" }}>
                    {String(k.n).padStart(2,"0")} · {k.short}
                  </button>
                );
              })}
              {a.oecd !== "—" && <span className="chip outline" style={{ marginLeft: "auto" }}>{a.oecd}</span>}
            </div>
          </article>
        ))}
      </div>

      <PageFoot />
    </div>
  );
}

window.ScreenAssays = ScreenAssays;
