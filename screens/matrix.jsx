// hKCC — Cross-tab matrix

function ScreenMatrix({ onNav, matrixStyle = "heatmap" }) {
  const kccs = window.KCCS;
  const carcs = window.CARCINOGENS;
  const [sortBy, setSortBy] = useState("name");
  const [groupFilter, setGroupFilter] = useState("all");

  let rows = carcs.slice();
  if (groupFilter !== "all") rows = rows.filter(c => c.group === groupFilter);
  if (sortBy === "name") rows.sort((a, b) => a.name.localeCompare(b.name));
  if (sortBy === "weight") rows.sort((a, b) => totalEvidence(b) - totalEvidence(a));
  if (sortBy === "coverage") rows.sort((a, b) => kccCoverage(b) - kccCoverage(a));

  // Column totals
  const colTotals = kccs.map(k => rows.reduce((s, c) => s + c.evidence[k.id], 0));
  const maxColTotal = Math.max(...colTotals);

  const cellSize = 32;

  return (
    <div className="content" style={{ maxWidth: "100%" }}>
      <SectionHead
        eyebrow="Analyze"
        title="Evidence matrix · agents × KCCs"
        sub="Rows are carcinogens, columns are key characteristics. Every cell is a 0–4 evidence score curated from monographs and primary literature. Hover any cell for details, click to open the agent profile."
      />

      <div className="card flat" style={{ background: "var(--paper-2)", padding: 14, marginBottom: 24 }}>
        <div className="flex gap-16" style={{ alignItems: "center", flexWrap: "wrap" }}>
          <div className="flex gap-4" style={{ alignItems: "center" }}>
            <span className="mono-sm">SORT</span>
            <button className={`tab ${sortBy === "name" ? "active" : ""}`} onClick={() => setSortBy("name")} style={{ padding: "4px 10px" }}>A–Z</button>
            <button className={`tab ${sortBy === "coverage" ? "active" : ""}`} onClick={() => setSortBy("coverage")} style={{ padding: "4px 10px" }}>Coverage</button>
            <button className={`tab ${sortBy === "weight" ? "active" : ""}`} onClick={() => setSortBy("weight")} style={{ padding: "4px 10px" }}>Weight</button>
          </div>
          <div className="flex gap-4" style={{ alignItems: "center" }}>
            <span className="mono-sm">GROUP</span>
            {["all", "1", "2A", "2B"].map(g => (
              <button key={g} className={`chip ${groupFilter === g ? "accent" : "outline"}`} style={{ cursor: "pointer", border: "none" }} onClick={() => setGroupFilter(g)}>
                {g === "all" ? "All" : `G${g}`}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto" }}>
            <EvLegend />
          </div>
        </div>
      </div>

      {/* Matrix table */}
      <div style={{ overflowX: "auto", border: "1px solid var(--rule)", borderRadius: 4, background: "var(--paper-2)" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{
                position: "sticky", left: 0, zIndex: 2, background: "var(--paper-2)",
                padding: "8px 12px", textAlign: "left", minWidth: 240, borderBottom: "1px solid var(--rule)", borderRight: "1px solid var(--rule)"
              }}>
                <div className="mono-sm">AGENT ({rows.length})</div>
              </th>
              {kccs.map(k => (
                <th key={k.id} style={{ padding: 0, borderBottom: "1px solid var(--rule)", borderRight: "1px solid var(--rule)", background: "var(--paper-2)" }}>
                  <div style={{ height: 160, width: cellSize, position: "relative", display: "flex", alignItems: "flex-end", justifyContent: "center", padding: "8px 0" }}>
                    <span style={{
                      fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--muted)",
                      transform: "rotate(-60deg)", transformOrigin: "center", whiteSpace: "nowrap", position: "absolute", bottom: 36
                    }}>
                      {k.short}
                    </span>
                    <span className="mono-sm" style={{ fontSize: 9.5 }}>{String(k.n).padStart(2, "0")}</span>
                  </div>
                </th>
              ))}
              <th style={{ padding: "8px 10px", borderBottom: "1px solid var(--rule)", borderRight: "1px solid var(--rule)", background: "var(--paper-2)", minWidth: 80 }}>
                <div className="mono-sm">WEIGHT</div>
              </th>
              <th style={{ padding: "8px 10px", borderBottom: "1px solid var(--rule)", background: "var(--paper-2)", minWidth: 80 }}>
                <div className="mono-sm">COVERAGE</div>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(c => {
              const w = totalEvidence(c), cov = kccCoverage(c);
              return (
                <tr key={c.id}>
                  <td onClick={() => onNav("carcDetail", { id: c.id })}
                      style={{ position: "sticky", left: 0, zIndex: 1, background: "var(--paper-2)", padding: "8px 12px", borderBottom: "1px solid var(--rule)", borderRight: "1px solid var(--rule)", cursor: "pointer", minWidth: 240 }}>
                    <div className="flex gap-8" style={{ alignItems: "center" }}>
                      <span style={{ fontFamily: "var(--font-serif)", fontSize: 15 }}>{c.name}</span>
                      <span className="chip outline" style={{ fontSize: 9, padding: "1px 5px" }}>{c.group}</span>
                    </div>
                  </td>
                  {kccs.map(k => {
                    const v = c.evidence[k.id];
                    const bg = `var(--ev-${v})`;
                    return (
                      <td key={k.id} onClick={() => onNav("carcDetail", { id: c.id })}
                          title={`${c.name} × ${k.short} = ${v}/4`}
                          style={{ padding: 0, borderBottom: "1px solid var(--rule)", borderRight: "1px solid var(--rule)", width: cellSize, height: cellSize, background: bg, cursor: "pointer", position: "relative" }}>
                        {matrixStyle === "dot" && (
                          <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <span style={{ width: 4 + v*2, height: 4 + v*2, borderRadius: "50%", background: v === 0 ? "transparent" : "var(--ink)", opacity: 0.7 }} />
                          </span>
                        )}
                        {matrixStyle === "bar" && v > 0 && (
                          <span style={{ position: "absolute", left: 0, bottom: 0, right: 0, height: `${(v/4)*100}%`, background: "var(--accent)" }} />
                        )}
                        {matrixStyle === "number" && v > 0 && (
                          <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-mono)", fontSize: 11, color: v >= 3 ? "#fff" : "var(--ink)" }}>{v}</span>
                        )}
                      </td>
                    );
                  })}
                  <td className="mono-sm" style={{ padding: "0 10px", borderBottom: "1px solid var(--rule)", borderRight: "1px solid var(--rule)", textAlign: "right" }}>{w}</td>
                  <td className="mono-sm" style={{ padding: "0 10px", borderBottom: "1px solid var(--rule)", textAlign: "right" }}>{cov}/14</td>
                </tr>
              );
            })}
            {/* Column totals */}
            <tr>
              <td style={{ position: "sticky", left: 0, zIndex: 1, background: "var(--paper-3)", padding: "10px 12px", borderRight: "1px solid var(--rule)" }} className="mono-sm">COLUMN WEIGHT</td>
              {colTotals.map((t, i) => (
                <td key={i} className="mono-sm" style={{ background: "var(--paper-3)", textAlign: "center", padding: "8px 0", borderRight: "1px solid var(--rule)", fontSize: 11 }}>
                  {t}
                </td>
              ))}
              <td colSpan="2" className="mono-sm" style={{ background: "var(--paper-3)", padding: "8px 10px", textAlign: "right" }}>
                Σ {colTotals.reduce((a, b) => a + b, 0)} / {rows.length * kccs.length * 4}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-20 flex" style={{ justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div className="prose" style={{ fontSize: 12.5, maxWidth: "60ch" }}>
          Visualisation style configurable via Tweaks panel · heatmap, dot density, vertical bar, or numeric. The same data backs the JSON / CSV exports linked under Data & API.
        </div>
        <div className="flex gap-8">
          <button className="btn ghost">↓ PNG snapshot</button>
          <button className="btn ghost">↓ Matrix CSV</button>
          <button className="btn accent">Open in matrix builder</button>
        </div>
      </div>

      <PageFoot />
    </div>
  );
}

window.ScreenMatrix = ScreenMatrix;
