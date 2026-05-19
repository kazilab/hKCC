// hKCC — Literature explorer

function ScreenLiterature({ onNav }) {
  const all = window.LITERATURE;
  const [tagFilter, setTagFilter] = useState("all");
  const tags = ["all", ...Array.from(new Set(all.map(r => r.tag)))];

  const filtered = tagFilter === "all" ? all : all.filter(r => r.tag === tagFilter);

  // Year histogram
  const years = all.map(r => r.year);
  const minY = Math.min(...years), maxY = Math.max(...years);
  const yearCounts = {};
  for (let y = minY; y <= maxY; y++) yearCounts[y] = 0;
  years.forEach(y => yearCounts[y]++);
  const maxC = Math.max(...Object.values(yearCounts));

  return (
    <div className="content">
      <SectionHead
        eyebrow="Literature"
        title={`Anchor references (${all.length})`}
        sub="The publications hKCC curators draw on when scoring evidence. Foundational, methodological and KCC-specific anchor papers, with cross-links to mapped agents."
      />

      {/* Histogram */}
      <div className="card flat" style={{ background: "var(--paper-2)", padding: 20, marginBottom: 24 }}>
        <div className="mono-sm mb-12">PUBLICATIONS BY YEAR · {minY}–{maxY}</div>
        <div className="flex" style={{ alignItems: "flex-end", gap: 4, height: 80 }}>
          {Object.entries(yearCounts).map(([y, c]) => (
            <div key={y} className="flex flex-col" style={{ alignItems: "center", flex: 1, gap: 4 }}>
              <div style={{
                width: "100%", maxWidth: 28,
                height: `${(c / maxC) * 64 + (c ? 8 : 1)}px`,
                background: c ? "var(--accent)" : "var(--paper-3)",
                borderRadius: "2px 2px 0 0"
              }} title={`${y}: ${c}`} />
              <span className="mono-sm" style={{ fontSize: 9 }}>{(+y) % 10 === 0 || +y === maxY || +y === minY ? y : ""}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-4 mb-20" style={{ flexWrap: "wrap" }}>
        {tags.map(t => (
          <button key={t} className={`chip ${tagFilter === t ? "accent" : "outline"}`} style={{ cursor: "pointer", border: "none" }} onClick={() => setTagFilter(t)}>{t === "all" ? "All" : t}</button>
        ))}
      </div>

      <div className="flex flex-col gap-16">
        {filtered.map(ref => (
          <article key={ref.id} className="card-hover" style={{ padding: "16px 0", borderTop: "1px solid var(--rule)" }}>
            <div className="flex gap-12" style={{ alignItems: "baseline" }}>
              <span className="mono-sm" style={{ color: "var(--accent)", fontSize: 13 }}>{ref.year}</span>
              <span className="chip outline">{ref.tag}</span>
              <span className="mono-sm" style={{ marginLeft: "auto" }}>{ref.cites} citations</span>
            </div>
            <h3 style={{ fontFamily: "var(--font-serif)", fontSize: 22, lineHeight: 1.2, marginTop: 8, fontWeight: 400 }}>
              {ref.title}
            </h3>
            <div className="mono-sm mt-8">{ref.authors}</div>
            <div className="mono-sm mt-4"><em style={{ fontStyle: "italic" }}>{ref.journal}</em> {ref.vol} {ref.doi !== "—" && `· DOI ${ref.doi}`}</div>
            <div className="flex gap-8 mt-12">
              {ref.kccs === "all" ? <span className="chip outline">All 14 KCCs</span> : ref.kccs.map(kid => {
                const k = window.KCCS.find(x => x.id === kid);
                return <button key={kid} className="chip accent" onClick={() => onNav("kccDetail", { id: kid })} style={{ cursor: "pointer", border: "none" }}>{String(k.n).padStart(2,"0")} · {k.short}</button>;
              })}
            </div>
          </article>
        ))}
      </div>

      <PageFoot />
    </div>
  );
}

window.ScreenLiterature = ScreenLiterature;
