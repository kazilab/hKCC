import { KCCS, agentsForKcc, assaysForKcc } from "../data";

export default function Kccs({ navigate }: { navigate: (p: string) => void }) {
  return (
    <>
      <h2 className="section-title" style={{ marginTop: 28 }}>
        Key Characteristics ({KCCS.length})
      </h2>
      <div className="grid cols-2">
        {KCCS.map((k) => {
          const nAgents = agentsForKcc(k.id).length;
          const nAssays = assaysForKcc(k.id).length;
          return (
            <div key={k.id} className="card clickable" style={{ cursor: "pointer" }} onClick={() => navigate(`kccs/${k.id}`)}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="chip">KC{k.n}</span>
                {k.is_extended && <span className="chip gray">extended</span>}
              </div>
              <h3 style={{ margin: "10px 0 6px", fontSize: "1.1rem" }}>{k.title}</h3>
              <p className="muted small" style={{ margin: "0 0 10px" }}>
                {k.description ?? k.short}
              </p>
              <div className="muted small">
                {nAgents} carcinogens · {nAssays} assays
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
