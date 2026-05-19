// hKCC — Data & API

function ScreenAPI({ onNav }) {
  const [endpoint, setEndpoint] = useState("agents");

  const endpoints = {
    agents: {
      method: "GET",
      path: "/api/v1/agents",
      desc: "List all curated agents with metadata and KCC evidence vectors.",
      sample: JSON.stringify({
        count: 26,
        items: [
          {
            id: "benzene",
            name: "Benzene",
            cas: "71-43-2",
            iarc_group: "1",
            tumour_sites: ["AML", "lymphoma"],
            evidence: { "kcc-01": 4, "kcc-02": 4, "kcc-03": 3, "...": "..." },
            last_review: "2025-11-04"
          }
        ]
      }, null, 2)
    },
    kccs: {
      method: "GET",
      path: "/api/v1/kccs",
      desc: "All 14 key characteristics with assays, mechanism notes, anchor references.",
      sample: JSON.stringify({
        count: 14,
        items: [{
          id: "kcc-02",
          n: 2,
          title: "Genotoxicity",
          short: "Genotoxic",
          assay_count: 34,
          extended: false
        }]
      }, null, 2)
    },
    matrix: {
      method: "GET",
      path: "/api/v1/matrix?group=1&format=long",
      desc: "Full agent × KCC evidence matrix. Supports wide (CSV) and long (JSON Lines) formats.",
      sample: JSON.stringify([
        { agent: "benzene", kcc: "kcc-01", evidence: 4, n_refs: 18 },
        { agent: "benzene", kcc: "kcc-02", evidence: 4, n_refs: 21 }
      ], null, 2)
    },
    assays: {
      method: "GET",
      path: "/api/v1/assays?kcc=kcc-02",
      desc: "Assays mapped to a given KCC. Filterable by throughput, OECD TG, and assay type.",
      sample: JSON.stringify({
        count: 4,
        items: [{ id: "ames", name: "Ames test", oecd: "OECD TG 471", throughput: "Medium" }]
      }, null, 2)
    },
    submit: {
      method: "POST",
      path: "/api/v1/contribute",
      desc: "Submit a curator annotation: new agent, evidence revision, or reference addition. Authenticated endpoint.",
      sample: JSON.stringify({
        agent_id: "pfoa",
        kcc_id: "kcc-08",
        proposed_evidence: 3,
        rationale: "New ToxCast data + Chen et al. 2024 (DOI: …) suggest stronger PPARα activation than previously scored.",
        references: ["10.1093/toxsci/kfae012"]
      }, null, 2)
    }
  };

  const ep = endpoints[endpoint];

  return (
    <div className="content">
      <SectionHead
        eyebrow="Build"
        title="Data & API"
        sub="hKCC is fully open. Download the entire dataset, query the JSON API, or contribute curator annotations."
      />

      {/* Download cards */}
      <div className="grid-3" style={{ gap: 16, marginBottom: 32 }}>
        {[
          { fmt: "CSV", desc: "Wide matrix (agents × KCCs) plus metadata join tables.", size: "412 KB", file: "hkcc-v0.4.2.csv.zip" },
          { fmt: "JSON", desc: "Full normalized dataset with citations and provenance.", size: "1.8 MB", file: "hkcc-v0.4.2.json" },
          { fmt: "Parquet", desc: "Columnar format for pandas / DuckDB workflows.", size: "286 KB", file: "hkcc-v0.4.2.parquet" }
        ].map(d => (
          <div key={d.fmt} className="card">
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 28 }}>{d.fmt}</div>
            <p className="prose mt-8" style={{ fontSize: 13 }}>{d.desc}</p>
            <div className="flex" style={{ justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
              <span className="mono-sm">{d.size}</span>
              <button className="btn ghost" style={{ padding: "6px 12px" }}>↓ Download</button>
            </div>
            <div className="mono-sm mt-12" style={{ fontSize: 10 }}>{d.file}</div>
          </div>
        ))}
      </div>

      <hr className="rule" />

      {/* API explorer */}
      <div className="grid-2 mt-32" style={{ gap: 32 }}>
        <div>
          <span className="eyebrow">API endpoints</span>
          <h3 className="h-sub mt-12">Stable v1 routes</h3>
          <div className="flex flex-col mt-16" style={{ gap: 2 }}>
            {Object.entries(endpoints).map(([key, e]) => (
              <button key={key} onClick={() => setEndpoint(key)}
                      className={endpoint === key ? "" : "card-hover"}
                      style={{
                        background: endpoint === key ? "var(--ink)" : "var(--paper-2)",
                        color: endpoint === key ? "var(--paper)" : "var(--ink)",
                        border: "1px solid var(--rule)",
                        padding: "10px 14px",
                        textAlign: "left",
                        cursor: "pointer",
                        fontFamily: "inherit",
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        borderRadius: 4
                      }}>
                <span className="mono-sm" style={{
                  color: endpoint === key ? "color-mix(in srgb, var(--paper) 70%, transparent)" : (e.method === "POST" ? "var(--accent)" : "var(--muted)"),
                  fontWeight: 600,
                  minWidth: 40
                }}>{e.method}</span>
                <span style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}>{e.path}</span>
              </button>
            ))}
          </div>
          <p className="prose mt-20" style={{ fontSize: 13 }}>{ep.desc}</p>
        </div>

        <div>
          <span className="eyebrow">Sample response</span>
          <h3 className="h-sub mt-12">{ep.method} {ep.path}</h3>
          <pre style={{
            background: "var(--ink)",
            color: "var(--paper)",
            padding: 20,
            borderRadius: 4,
            fontFamily: "var(--font-mono)",
            fontSize: 11.5,
            lineHeight: 1.6,
            overflow: "auto",
            maxHeight: 420,
            marginTop: 16
          }}>{ep.sample}</pre>
          <div className="flex gap-8 mt-12">
            <button className="btn ghost" style={{ padding: "6px 12px" }}>Copy</button>
            <button className="btn ghost" style={{ padding: "6px 12px" }}>Open in playground</button>
          </div>
        </div>
      </div>

      <hr className="rule mt-48" />

      {/* Auth */}
      <section className="mt-40">
        <SectionHead eyebrow="Authentication" title="API keys & rate limits" />
        <div className="grid-3">
          <div className="card">
            <div className="mono-sm" style={{ color: "var(--accent)" }}>PUBLIC</div>
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 22, marginTop: 8 }}>Anonymous</div>
            <p className="prose mt-8" style={{ fontSize: 12.5 }}>Read-only access to all curated data. No key required.</p>
            <div className="mono-sm mt-16">100 req / hour · IP-throttled</div>
          </div>
          <div className="card">
            <div className="mono-sm" style={{ color: "var(--accent)" }}>RESEARCHER</div>
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 22, marginTop: 8 }}>Free API key</div>
            <p className="prose mt-8" style={{ fontSize: 12.5 }}>Higher rate limits, webhook subscriptions on dataset updates.</p>
            <div className="mono-sm mt-16">10 000 req / hour · ORCID auth</div>
          </div>
          <div className="card">
            <div className="mono-sm" style={{ color: "var(--accent)" }}>CURATOR</div>
            <div style={{ fontFamily: "var(--font-serif)", fontSize: 22, marginTop: 8 }}>Write access</div>
            <p className="prose mt-8" style={{ fontSize: 12.5 }}>Submit revisions to evidence scores and reference lists. Requires invite from the editorial board.</p>
            <div className="mono-sm mt-16">By application</div>
          </div>
        </div>
      </section>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Snippets" title="Quickstart" />
        <div className="grid-2" style={{ gap: 16 }}>
          {[
            { lang: "Python", code: `import requests, pandas as pd

m = requests.get("https://api.hkcc.org/v1/matrix?format=long").json()
df = pd.DataFrame(m)
df.pivot(index="agent", columns="kcc", values="evidence").head()` },
            { lang: "R", code: `library(httr); library(jsonlite)

m <- fromJSON("https://api.hkcc.org/v1/matrix?format=long")
head(reshape2::acast(m, agent ~ kcc, value.var = "evidence"))` }
          ].map(s => (
            <div key={s.lang} className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div className="flex" style={{ justifyContent: "space-between", padding: "10px 16px", borderBottom: "1px solid var(--rule)", background: "var(--paper-3)" }}>
                <span className="mono-sm">{s.lang}</span>
                <button className="mono-sm" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent)" }}>Copy ↗</button>
              </div>
              <pre style={{ margin: 0, padding: 16, fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.6, color: "var(--ink-2)" }}>{s.code}</pre>
            </div>
          ))}
        </div>
      </section>

      <PageFoot />
    </div>
  );
}

window.ScreenAPI = ScreenAPI;
