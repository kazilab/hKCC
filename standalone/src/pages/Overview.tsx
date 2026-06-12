import { data, KCCS } from "../data";
import { href } from "../lib/util";

export default function Overview({ navigate }: { navigate: (p: string) => void }) {
  const c = data.meta.counts;
  return (
    <>
      <section className="hero">
        <div className="eyebrow">Open · versioned · citable</div>
        <h1>A mechanism atlas mapping human carcinogens to their Key Characteristics.</h1>
        <p>
          Evidence linking carcinogenic agents to the {c.kccs} Key Characteristics of Human
          Carcinogens (KCC) framework. Every score is transparent and citation-backed. This is a
          fully offline, self-contained build of the hKCC dataset (v{data.meta.version}).
        </p>
      </section>

      <div className="grid cols-4">
        {[
          ["Carcinogens", c.agents, "carcinogens"],
          ["Key characteristics", c.kccs, "kccs"],
          ["Assays", c.assays, "assays"],
          ["References", c.references, "methodology"],
        ].map(([label, num, path]) => (
          <a key={label as string} href={href(path as string)} className="card stat" style={{ textDecoration: "none" }}>
            <div className="num">{num as number}</div>
            <div className="lbl">{label as string}</div>
          </a>
        ))}
      </div>

      <h2 className="section-title">The {c.kccs} Key Characteristics</h2>
      <div className="grid cols-3">
        {KCCS.map((k) => (
          <div
            key={k.id}
            className="card clickable"
            style={{ cursor: "pointer" }}
            onClick={() => navigate(`kccs/${k.id}`)}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span className="chip">KC{k.n}</span>
              {k.is_extended && <span className="chip gray">extended</span>}
            </div>
            <h3 style={{ margin: "10px 0 6px", fontSize: "1.05rem" }}>{k.title}</h3>
            <p className="muted small" style={{ margin: 0 }}>
              {k.description ?? k.short}
            </p>
          </div>
        ))}
      </div>

      <h2 className="section-title">Explore</h2>
      <div className="grid cols-3">
        <ExploreCard
          title="Evidence matrix"
          body="Browse the full carcinogen × KCC heat-map of evidence scores."
          onClick={() => navigate("matrix")}
        />
        <ExploreCard
          title="Carcinogens"
          body="Search agents, view per-characteristic evidence and linked literature."
          onClick={() => navigate("carcinogens")}
        />
        <ExploreCard
          title="Assays"
          body="The mechanistic assay library mapped to KCCs and study designs."
          onClick={() => navigate("assays")}
        />
      </div>
    </>
  );
}

function ExploreCard({ title, body, onClick }: { title: string; body: string; onClick: () => void }) {
  return (
    <div className="card clickable" style={{ cursor: "pointer" }} onClick={onClick}>
      <h3 style={{ margin: "0 0 6px", fontSize: "1.05rem" }}>{title} →</h3>
      <p className="muted small" style={{ margin: 0 }}>
        {body}
      </p>
    </div>
  );
}
