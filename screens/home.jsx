// hKCC — Home / Overview screen

function ScreenHome({ onNav }) {
  const kccs = window.KCCS;
  const carcs = window.CARCINOGENS;
  const group1Count = carcs.filter(c => c.group === "1").length;
  const totalRefs = window.LITERATURE.length;

  return (
    <div className="content">
      <span className="platform-note mb-12">Live · Streamlit backend · last refresh 14m ago</span>
      <h1 className="h-display" style={{ maxWidth: "16ch" }}>
        A mechanistic atlas for the <em style={{ fontStyle: "italic", color: "var(--accent)" }}>14 key characteristics</em> of human carcinogens.
      </h1>
      <p className="lede mt-24" style={{ maxWidth: "62ch" }}>
        hKCC is an open, curated database that organises mechanistic evidence linking known and suspected carcinogens to the key characteristics framework proposed by Smith et al. (2016) and extended in the years since.
      </p>

      <div className="flex gap-12 mt-32">
        <button className="btn accent" onClick={() => onNav("kccs")}>Browse the KCCs →</button>
        <button className="btn ghost" onClick={() => onNav("matrix")}>Open evidence matrix</button>
        <button className="btn ghost" onClick={() => onNav("api")}>API & downloads</button>
      </div>

      <hr className="rule-thick mt-48" />

      <div className="stat-row">
        <div className="stat"><div className="v">{kccs.length}</div><div className="l">Key characteristics</div></div>
        <div className="stat"><div className="v">{carcs.length}</div><div className="l">Curated agents</div></div>
        <div className="stat"><div className="v">{group1Count}</div><div className="l">IARC Group 1</div></div>
        <div className="stat"><div className="v">{window.ASSAYS.length}</div><div className="l">Mapped assays</div></div>
        <div className="stat"><div className="v">{totalRefs}</div><div className="l">Source references</div></div>
        <div className="stat"><div className="v">CC-BY</div><div className="l">License</div></div>
      </div>

      <hr className="rule mt-32" />

      {/* The 14 KCCs preview */}
      <section className="mt-40">
        <SectionHead eyebrow="The framework" title="Fourteen key characteristics" sub="Ten characteristics from Smith et al. (2016), plus four community-extended characteristics covering microbiome, senescence, stem-cell dynamics, and gap-junction communication." />
        <div className="grid-4" style={{ gap: 12 }}>
          {kccs.map(k => (
            <button key={k.id} className="card card-hover" onClick={() => onNav("kccDetail", { id: k.id })} style={{ textAlign: "left", border: "1px solid var(--rule)", cursor: "pointer", fontFamily: "inherit", background: "var(--paper-2)" }}>
              <div className="flex" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                <span className="mono-sm">{String(k.n).padStart(2, "0")}</span>
                <KCCGlyph kind={k.icon} size={20} color={k.color} />
              </div>
              <div className="mt-12" style={{ fontFamily: "var(--font-serif)", fontSize: 18, lineHeight: 1.15, letterSpacing: "-0.01em" }}>
                {k.title}
              </div>
              <div className="mt-12 flex gap-8" style={{ alignItems: "center" }}>
                <span className="mono-sm">{k.carcCount} agents</span>
                <span className="mono-sm" style={{ color: "var(--muted-2)" }}>·</span>
                <span className="mono-sm">{k.assayCount} assays</span>
              </div>
              {k.isNew && <div className="chip outline mt-12" style={{ borderColor: "var(--teal)", color: "var(--teal)" }}>New addition</div>}
            </button>
          ))}
        </div>
      </section>

      <hr className="rule mt-48" />

      {/* Two columns: featured agents + recent literature */}
      <div className="grid-2 mt-40" style={{ gap: 48 }}>
        <section>
          <SectionHead eyebrow="Featured" title="Most-queried agents this week" />
          <div className="flex flex-col gap-8">
            {["tobacco-smoke", "benzene", "asbestos", "tcdd", "ethanol", "arsenic"].map(id => {
              const c = carcs.find(x => x.id === id);
              const cov = kccCoverage(c);
              return (
                <button key={id} className="card card-hover flex" onClick={() => onNav("carcDetail", { id })}
                        style={{ alignItems: "center", gap: 16, textAlign: "left", padding: "14px 18px", cursor: "pointer", fontFamily: "inherit" }}>
                  <div style={{ flex: 1 }}>
                    <div className="flex gap-12" style={{ alignItems: "baseline" }}>
                      <span style={{ fontFamily: "var(--font-serif)", fontSize: 20 }}>{c.name}</span>
                      <GroupChip g={c.group} />
                    </div>
                    <div className="mono-sm mt-4">{c.cas !== "—" ? `CAS ${c.cas} · ` : ""}{c.type}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div className="mono-sm" style={{ color: "var(--muted)" }}>Coverage</div>
                    <div style={{ fontFamily: "var(--font-mono)", fontSize: 16 }}>{cov}/{kccs.length}</div>
                  </div>
                  <div className="flex" style={{ gap: 2 }}>
                    {Object.values(c.evidence).map((v, i) => <EvCell key={i} v={v} />)}
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        <section>
          <SectionHead eyebrow="Recent" title="Methodology & literature" />
          <div className="flex flex-col gap-16">
            {window.LITERATURE.slice(0, 5).map(ref => (
              <article key={ref.id} className="card-hover" style={{ padding: "8px 0", borderTop: "1px solid var(--rule)", cursor: "pointer" }} onClick={() => onNav("literature")}>
                <div className="flex gap-12" style={{ alignItems: "baseline" }}>
                  <span className="mono-sm" style={{ color: "var(--accent)" }}>{ref.year}</span>
                  <span className="chip outline" style={{ fontSize: 9.5 }}>{ref.tag}</span>
                </div>
                <div style={{ fontFamily: "var(--font-serif)", fontSize: 17, lineHeight: 1.25, marginTop: 6 }}>
                  {ref.title}
                </div>
                <div className="mono-sm mt-4">{ref.authors} — <em style={{ fontStyle: "italic", color: "var(--ink-2)" }}>{ref.journal}</em>, {ref.vol}</div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <hr className="rule mt-48" />

      {/* Evidence ramp explainer */}
      <section className="mt-40 card flat" style={{ background: "var(--paper-2)", padding: 32 }}>
        <div className="grid-2" style={{ gap: 48, alignItems: "start" }}>
          <div>
            <span className="eyebrow">How to read this</span>
            <h3 className="h-sub mt-12">Every cell in hKCC is an editorial judgement of evidence strength.</h3>
            <p className="prose mt-12">
              For each carcinogen × KCC pair, curators score the weight of mechanistic evidence on a 0–4 ordinal scale, drawing on IARC monograph mechanistic write-ups, primary literature, and high-throughput screening data from ToxCast / Tox21 where available.
            </p>
            <p className="prose mt-8">
              Hover any cell in the evidence matrix to see the underlying citations. Scoring is fully transparent and versioned.
            </p>
          </div>
          <div className="flex flex-col gap-16">
            <EvLegend />
            <div className="card" style={{ background: "var(--paper)" }}>
              <div className="mono-sm mb-8">EXAMPLE · BENZENE</div>
              <div className="flex" style={{ gap: 3, flexWrap: "wrap" }}>
                {kccs.map(k => (
                  <span key={k.id} title={`${k.short} — ${carcs[0].evidence[k.id]}/4`}>
                    <EvCell v={carcs[0].evidence[k.id]} />
                  </span>
                ))}
              </div>
              <div className="mono-sm mt-12">14 cells · 1 row · {totalEvidence(carcs[0])}/56 weighted score</div>
            </div>
          </div>
        </div>
      </section>

      <PageFoot />
    </div>
  );
}

window.ScreenHome = ScreenHome;
