// hKCC — About / methodology

function ScreenAbout({ onNav }) {
  return (
    <div className="content">
      <span className="eyebrow">About hKCC</span>
      <h1 className="h-display mt-12" style={{ fontSize: 64, maxWidth: "20ch" }}>
        An open, versioned, citable mechanism atlas for human carcinogens.
      </h1>

      <hr className="rule-thick mt-32" />

      <div className="grid-2" style={{ gap: 48 }}>
        <div>
          <span className="eyebrow muted">Scope</span>
          <p className="prose mt-12">
            hKCC organises mechanistic evidence linking known and suspected human carcinogens to the 14 key characteristics framework. The original ten KCCs were proposed by Smith et al. (2016) and have since been adopted by the IARC Monographs as a structuring device for mechanistic evaluation. hKCC additionally tracks four community-extended characteristics covering microbiome, cellular senescence, stem-cell dynamics, and gap-junction communication.
          </p>
          <p className="prose mt-12">
            The platform is not itself a classification authority. It aggregates and surfaces evidence; classifications cited throughout (IARC Group 1, 2A, 2B) are reproduced from IARC monographs and other regulatory determinations.
          </p>
        </div>
        <div>
          <span className="eyebrow muted">Curation</span>
          <p className="prose mt-12">
            Each evidence score (0–4) is assigned by at least two independent curators with cancer-mechanism expertise and adjudicated through a documented dissent-resolution process. Underlying citations are stored at the cell level: every score has a provenance trail of references, ToxCast assay endpoints, and curator notes that can be inspected via the API.
          </p>
          <p className="prose mt-12">
            Releases follow semantic versioning. The complete dataset is archived to Zenodo at every minor version with a citable DOI.
          </p>
        </div>
      </div>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Process" title="How an agent enters hKCC" />
        <div className="grid-4" style={{ gap: 16 }}>
          {[
            { n: "01", t: "Nomination", d: "Curators or contributors nominate an agent based on IARC monograph activity, NTP RoC listings, or emerging epidemiological signals." },
            { n: "02", t: "Evidence extraction", d: "Mechanistic statements from the monograph and primary literature are extracted, tagged with the relevant KCC, and stored verbatim." },
            { n: "03", t: "Independent scoring", d: "Two curators independently assign a 0–4 evidence score per KCC. Disagreements ≥ 2 are escalated to the editorial board." },
            { n: "04", t: "Release & versioning", d: "Approved entries are merged into the next quarterly release and tagged with a versioned DOI for citation." }
          ].map(s => (
            <div key={s.n} className="card">
              <div className="mono-sm" style={{ color: "var(--accent)", fontSize: 13 }}>STEP {s.n}</div>
              <div style={{ fontFamily: "var(--font-serif)", fontSize: 22, marginTop: 8 }}>{s.t}</div>
              <p className="prose mt-8" style={{ fontSize: 13 }}>{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Architecture" title="Built on Python + Streamlit" />
        <div className="grid-2" style={{ gap: 48, alignItems: "start" }}>
          <div>
            <p className="prose">
              hKCC is implemented as a Streamlit application backed by a Postgres data layer and a FastAPI service for the public read API. Curators interact through an authenticated Streamlit interface; readers see the public face you are using now.
            </p>
            <p className="prose mt-8">
              Underlying data pipelines pull live from PubChem (chemistry), ToxCast/Tox21 (assay endpoints), and OpenAlex (citations). Manual curation always supersedes automated extraction; both are kept in the provenance trail.
            </p>
          </div>
          <div className="card" style={{ background: "var(--paper)", padding: 0, overflow: "hidden", border: "1px solid var(--rule)" }}>
            <div className="mono-sm" style={{ padding: "10px 16px", borderBottom: "1px solid var(--rule)", background: "var(--paper-3)" }}>STACK</div>
            <table className="data" style={{ background: "transparent" }}>
              <tbody>
                {[
                  ["Frontend", "Streamlit · custom components"],
                  ["API", "FastAPI · Pydantic · ORJSON"],
                  ["Database", "PostgreSQL 16 · pgvector"],
                  ["Pipelines", "Python · Prefect · DuckDB"],
                  ["External", "PubChem · ToxCast · OpenAlex · CrossRef"],
                  ["Hosting", "Self-hosted · EU region"],
                  ["License", "CC-BY-4.0 (data) · MIT (code)"]
                ].map(([k, v]) => (
                  <tr key={k}>
                    <td className="mono-sm" style={{ width: "32%" }}>{k}</td>
                    <td>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Cite this resource" title="How to cite hKCC" />
        <div className="card" style={{ background: "var(--paper-2)" }}>
          <div className="mono-sm mb-12">SUGGESTED CITATION</div>
          <p style={{ fontFamily: "var(--font-serif)", fontSize: 18, lineHeight: 1.4 }}>
            hKCC Consortium (2026). <em>hKCC — A mechanism atlas for the key characteristics of human carcinogens, v0.4.2.</em> Zenodo. doi:10.5281/zenodo.XXXXXXX
          </p>
          <div className="flex gap-8 mt-16">
            <button className="btn ghost">Copy BibTeX</button>
            <button className="btn ghost">Copy RIS</button>
            <button className="btn ghost">Copy DOI</button>
          </div>
        </div>
      </section>

      <hr className="rule mt-48" />

      <section className="mt-40">
        <SectionHead eyebrow="Team" title="Editorial board" />
        <div className="grid-3" style={{ gap: 16 }}>
          {[
            { n: "M. T. Lindqvist", r: "Editor-in-chief", a: "Karolinska Institutet" },
            { n: "R. Okonkwo", r: "Mechanism lead", a: "Imperial College London" },
            { n: "D. Almeida", r: "Curation lead", a: "University of São Paulo" },
            { n: "S. Yamaguchi", r: "Data engineering", a: "RIKEN" },
            { n: "L. Berger", r: "Assays & methods", a: "EPA / CCTE" },
            { n: "A. Hassan", r: "Microbiome subboard", a: "Pasteur Institute" }
          ].map(p => (
            <div key={p.n} className="flex gap-12" style={{ alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--rule)" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", background: "var(--paper-3)", border: "1px solid var(--rule)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-serif)", fontSize: 18, color: "var(--muted)" }}>
                {p.n.split(" ").map(x => x[0]).join("")}
              </div>
              <div>
                <div style={{ fontFamily: "var(--font-serif)", fontSize: 17 }}>{p.n}</div>
                <div className="mono-sm">{p.r} · {p.a}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <PageFoot />
    </div>
  );
}

window.ScreenAbout = ScreenAbout;
