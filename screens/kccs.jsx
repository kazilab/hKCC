// hKCC — Browse the 14 KCCs

function ScreenKCCs({ onNav }) {
  const kccs = window.KCCS;
  const [view, setView] = useState("grid"); // grid | list
  const [filter, setFilter] = useState("all"); // all | original | new

  const filtered = kccs.filter(k => {
    if (filter === "original") return !k.isNew;
    if (filter === "new") return k.isNew;
    return true;
  });

  return (
    <div className="content">
      <SectionHead
        eyebrow="The framework"
        title="The 14 key characteristics"
        sub="Each KCC describes a distinct biological process consistently observed in established carcinogens. Together they form a mechanistic checklist for hazard identification — independent of tumour site, exposure route, or chemical class."
      />

      <div className="flex gap-12 mb-24" style={{ alignItems: "center", justifyContent: "space-between" }}>
        <div className="flex gap-4">
          {[
            { id: "all", label: `All (${kccs.length})` },
            { id: "original", label: "Original 10" },
            { id: "new", label: "New additions (4)" }
          ].map(f => (
            <button key={f.id} className={`chip ${filter === f.id ? "accent" : "outline"}`} onClick={() => setFilter(f.id)} style={{ cursor: "pointer", border: "none" }}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex gap-4">
          <button className={`tab ${view === "grid" ? "active" : ""}`} onClick={() => setView("grid")}>Grid</button>
          <button className={`tab ${view === "list" ? "active" : ""}`} onClick={() => setView("list")}>List</button>
        </div>
      </div>

      {view === "grid" ? (
        <div className="grid-2" style={{ gap: 16 }}>
          {filtered.map(k => (
            <button key={k.id} className="card card-hover" onClick={() => onNav("kccDetail", { id: k.id })}
                    style={{ textAlign: "left", cursor: "pointer", fontFamily: "inherit", padding: 24 }}>
              <div className="flex" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <span className="mono-sm" style={{ fontSize: 12 }}>KCC-{String(k.n).padStart(2, "0")}</span>
                <KCCGlyph kind={k.icon} size={26} color={k.color} />
              </div>
              <div className="mt-16" style={{ fontFamily: "var(--font-serif)", fontSize: 26, lineHeight: 1.1, letterSpacing: "-0.015em" }}>
                {k.title}
              </div>
              <p className="prose mt-12" style={{ fontSize: 13.5 }}>{k.desc}</p>
              <div className="flex gap-16 mt-20" style={{ alignItems: "center" }}>
                <span className="mono-sm">{k.carcCount} agents</span>
                <span className="mono-sm">·</span>
                <span className="mono-sm">{k.assayCount} assays</span>
                {k.isNew && <span className="chip outline" style={{ marginLeft: "auto", borderColor: "var(--teal)", color: "var(--teal)", fontSize: 9.5 }}>Extended set</span>}
              </div>
            </button>
          ))}
        </div>
      ) : (
        <table className="data">
          <thead>
            <tr>
              <th style={{ width: 60 }}>ID</th>
              <th></th>
              <th>Title</th>
              <th>Examples</th>
              <th className="num">Agents</th>
              <th className="num">Assays</th>
              <th>Set</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(k => (
              <tr key={k.id} className="row-hover" onClick={() => onNav("kccDetail", { id: k.id })}>
                <td className="mono-sm">KCC-{String(k.n).padStart(2, "0")}</td>
                <td><KCCGlyph kind={k.icon} size={20} color={k.color} /></td>
                <td>
                  <div style={{ fontFamily: "var(--font-serif)", fontSize: 17 }}>{k.title}</div>
                  <div className="mono-sm mt-4" style={{ maxWidth: "60ch" }}>{k.short}</div>
                </td>
                <td className="text-muted" style={{ fontSize: 12.5 }}>{k.examples.join(", ")}</td>
                <td className="num">{k.carcCount}</td>
                <td className="num">{k.assayCount}</td>
                <td>{k.isNew ? <span className="chip outline" style={{ borderColor: "var(--teal)", color: "var(--teal)" }}>Extended</span> : <span className="chip outline">Original</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <PageFoot />
    </div>
  );
}

// Single KCC detail
function ScreenKCCDetail({ id, onNav }) {
  const k = window.KCCS.find(x => x.id === id);
  if (!k) return <div className="content">KCC not found.</div>;

  // top carcinogens for this KCC (evidence >= 3)
  const top = window.CARCINOGENS
    .map(c => ({ c, v: c.evidence[k.id] }))
    .filter(x => x.v >= 1)
    .sort((a, b) => b.v - a.v)
    .slice(0, 12);

  const relAssays = window.ASSAYS.filter(a => a.kccs.includes(k.id));
  const relRefs = window.LITERATURE.filter(r => r.kccs === "all" || (Array.isArray(r.kccs) && r.kccs.includes(k.id)));

  return (
    <div className="content">
      <button className="mono-sm" onClick={() => onNav("kccs")} style={{ background: "none", border: "none", padding: 0, cursor: "pointer", color: "var(--muted)" }}>← All KCCs</button>

      <div className="flex mt-16" style={{ gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <span className="mono-sm" style={{ color: "var(--accent)" }}>KCC-{String(k.n).padStart(2, "0")}{k.isNew ? " · Extended set" : " · Original (Smith 2016)"}</span>
          <h1 className="h-display mt-12" style={{ fontSize: 64, maxWidth: "18ch" }}>{k.title}</h1>
          <p className="lede mt-20">{k.desc}</p>
        </div>
        <div className="card" style={{ width: 180, textAlign: "center", padding: 32 }}>
          <KCCGlyph kind={k.icon} size={80} color={k.color} />
          <div className="mono-sm mt-12">SYMBOL</div>
        </div>
      </div>

      <hr className="rule-thick mt-32" />

      <div className="stat-row">
        <div className="stat"><div className="v">{k.carcCount}</div><div className="l">Agents w/ evidence</div></div>
        <div className="stat"><div className="v">{k.assayCount}</div><div className="l">Mapped assays</div></div>
        <div className="stat"><div className="v">{relRefs.length}</div><div className="l">Anchor references</div></div>
        <div className="stat"><div className="v">{k.examples.length}</div><div className="l">Canonical examples</div></div>
      </div>

      <hr className="rule mt-32" />

      <div className="grid-2 mt-32" style={{ gap: 48 }}>
        <section>
          <span className="eyebrow">Mechanism</span>
          <h3 className="h-sub mt-12">How agents express this characteristic</h3>
          <p className="prose mt-12">{k.mechanism}</p>
          <p className="prose mt-8">
            Demonstration of this characteristic alone is not sufficient to classify an agent as carcinogenic; rather, the framework aggregates mechanistic signals across all 14 KCCs and weighs them against epidemiological and animal evidence.
          </p>
        </section>
        <section>
          <span className="eyebrow">Canonical agents</span>
          <h3 className="h-sub mt-12">Frequently cited examples</h3>
          <ul className="flex flex-col gap-8 mt-12" style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {k.examples.map(ex => (
              <li key={ex} className="flex gap-12" style={{ alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--rule)" }}>
                <span style={{ fontFamily: "var(--font-serif)", fontSize: 18 }}>{ex}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Mapped assays" title={`${relAssays.length} validated readouts`} sub="Standard wet-lab and high-throughput methods commonly used to probe this characteristic." />
        <table className="data">
          <thead>
            <tr>
              <th>Assay</th>
              <th>Type</th>
              <th>Target / readout</th>
              <th>Throughput</th>
              <th>OECD TG</th>
            </tr>
          </thead>
          <tbody>
            {relAssays.map(a => (
              <tr key={a.id} className="row-hover" onClick={() => onNav("assays")}>
                <td><span style={{ fontFamily: "var(--font-serif)", fontSize: 16 }}>{a.name}</span></td>
                <td>{a.type}</td>
                <td className="text-muted">{a.target}</td>
                <td>{a.throughput}</td>
                <td className="mono-sm">{a.oecd}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Agents" title="Top agents with evidence for this KCC" sub={`Ranked by curated evidence strength. ${top.length} of ${window.CARCINOGENS.length} agents have evidence ≥ 1 for ${k.short}.`} />
        <table className="data">
          <thead>
            <tr>
              <th>Agent</th>
              <th>IARC group</th>
              <th>Type</th>
              <th style={{ width: 220 }}>Evidence for {k.short}</th>
            </tr>
          </thead>
          <tbody>
            {top.map(({ c, v }) => (
              <tr key={c.id} className="row-hover" onClick={() => onNav("carcDetail", { id: c.id })}>
                <td><span style={{ fontFamily: "var(--font-serif)", fontSize: 17 }}>{c.name}</span></td>
                <td><GroupChip g={c.group} /></td>
                <td className="text-muted">{c.type}</td>
                <td><EvBar v={v} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="References" title={`${relRefs.length} anchoring publications`} />
        <div className="flex flex-col gap-12">
          {relRefs.slice(0, 8).map(ref => (
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
      </section>

      <PageFoot />
    </div>
  );
}

window.ScreenKCCs = ScreenKCCs;
window.ScreenKCCDetail = ScreenKCCDetail;
