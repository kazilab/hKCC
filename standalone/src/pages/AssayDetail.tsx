import { ASSAY_BY_ID, KCC_BY_ID } from "../data";
import { href } from "../lib/util";

export default function AssayDetail({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const assay = ASSAY_BY_ID.get(id);
  if (!assay) {
    return (
      <div className="card" style={{ marginTop: 40 }}>
        <h2>Assay not found</h2>
        <a href={href("assays")}>← Back to assays</a>
      </div>
    );
  }

  const fields: [string, string | null][] = [
    ["Type", assay.type],
    ["Target", assay.target],
    ["Throughput", assay.throughput],
    ["OECD TG", assay.oecd_tg],
    ["Granularity", assay.granularity],
    ["Source", assay.source],
  ];

  return (
    <>
      <a className="back" href={href("assays")}>
        ← All assays
      </a>

      <div className="card">
        <h1 style={{ margin: "0 0 6px", fontSize: "1.6rem" }}>{assay.name}</h1>
        {assay.name_alt && <div className="muted small">also: {assay.name_alt}</div>}
        {assay.notes && <p>{assay.notes}</p>}
        <div className="grid cols-3" style={{ marginTop: 8 }}>
          {fields
            .filter(([, v]) => v && v !== "—")
            .map(([k, v]) => (
              <div key={k}>
                <div className="eyebrow">{k}</div>
                <div className="small">{v}</div>
              </div>
            ))}
        </div>
      </div>

      <h2 className="section-title">Mapped Key Characteristics</h2>
      {assay.kcc_ids.length === 0 ? (
        <p className="muted">No KCC mapping recorded.</p>
      ) : (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {assay.kcc_ids.map((kid) => {
            const k = KCC_BY_ID.get(kid);
            return (
              <button key={kid} className="btn" onClick={() => navigate(`kccs/${kid}`)}>
                {k ? `${k.n}. ${k.short}` : kid}
              </button>
            );
          })}
        </div>
      )}

      {assay.subgroups.length > 0 && (
        <>
          <h2 className="section-title">KC subgroups</h2>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table>
              <thead>
                <tr>
                  <th>KCC</th>
                  <th>Subgroup</th>
                </tr>
              </thead>
              <tbody>
                {assay.subgroups.map((sg, i) => (
                  <tr key={i}>
                    <td>{KCC_BY_ID.get(sg.kcc_id)?.short ?? sg.kcc_id}</td>
                    <td className="small">{sg.subgroup}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {assay.study_designs.length > 0 && (
        <>
          <h2 className="section-title">Study designs</h2>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table>
              <thead>
                <tr>
                  <th>KCC</th>
                  <th>Design</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {assay.study_designs.map((sd, i) => (
                  <tr key={i}>
                    <td>{KCC_BY_ID.get(sd.kcc_id)?.short ?? sd.kcc_id}</td>
                    <td className="small">{sd.design ?? "—"}</td>
                    <td className="muted small">{sd.source ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
