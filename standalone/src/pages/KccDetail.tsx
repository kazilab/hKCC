import { KCC_BY_ID, agentsForKcc, assaysForKcc, referencesForKcc } from "../data";
import { href, scoreColor, scoreLabel } from "../lib/util";
import RefList from "../components/RefList";

export default function KccDetail({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const kcc = KCC_BY_ID.get(id);
  if (!kcc) {
    return (
      <div className="card" style={{ marginTop: 40 }}>
        <h2>Key Characteristic not found</h2>
        <a href={href("kccs")}>← Back to KCCs</a>
      </div>
    );
  }

  const agents = agentsForKcc(id);
  const assays = assaysForKcc(id);
  const refs = referencesForKcc(id).slice(0, 60);

  return (
    <>
      <a className="back" href={href("kccs")}>
        ← All Key Characteristics
      </a>

      <div className="card">
        <span className="chip">KC{kcc.n}</span>
        <h1 style={{ margin: "10px 0 8px", fontSize: "1.8rem" }}>{kcc.title}</h1>
        {kcc.description && <p style={{ marginTop: 0 }}>{kcc.description}</p>}
        {kcc.mechanism && (
          <>
            <div className="eyebrow" style={{ marginTop: 12 }}>
              Mechanism
            </div>
            <p className="small" style={{ marginTop: 4, marginBottom: 0 }}>
              {kcc.mechanism}
            </p>
          </>
        )}
      </div>

      <h2 className="section-title">Carcinogens with evidence ({agents.length})</h2>
      {agents.length === 0 ? (
        <p className="muted">No carcinogens scored ≥ 2 on this characteristic.</p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table>
            <thead>
              <tr>
                <th>Carcinogen</th>
                <th>IARC</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr key={a.id} className="clickable" onClick={() => navigate(`carcinogens/${a.id}`)}>
                  <td style={{ fontWeight: 600 }}>{a.name}</td>
                  <td>{a.iarc_group !== "—" ? <span className="chip">{a.iarc_group}</span> : "—"}</td>
                  <td>
                    <span
                      className="chip"
                      style={{ background: scoreColor(a.kccScore), color: a.kccScore >= 3 ? "#fff" : undefined }}
                      title={scoreLabel(a.kccScore)}
                    >
                      {a.kccScore} · {scoreLabel(a.kccScore)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="section-title">Assays ({assays.length})</h2>
      {assays.length === 0 ? (
        <p className="muted">No assays mapped to this characteristic.</p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table>
            <thead>
              <tr>
                <th>Assay</th>
                <th>Type</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              {assays.slice(0, 80).map((a) => (
                <tr key={a.id} className="clickable" onClick={() => navigate(`assays/${a.id}`)}>
                  <td style={{ fontWeight: 600 }}>{a.name}</td>
                  <td className="muted small">{a.type ?? "—"}</td>
                  <td className="muted small">{a.target ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="section-title">References ({refs.length})</h2>
      {refs.length === 0 ? <p className="muted">No linked references.</p> : <RefList refs={refs} />}
    </>
  );
}
