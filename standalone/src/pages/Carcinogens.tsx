import { useMemo, useState } from "react";
import { AGENTS } from "../data";

export default function Carcinogens({ navigate }: { navigate: (p: string) => void }) {
  const [q, setQ] = useState("");
  const rows = useMemo(() => {
    const n = q.trim().toLowerCase();
    if (!n) return AGENTS;
    return AGENTS.filter(
      (a) =>
        a.name.toLowerCase().includes(n) ||
        (a.cas ?? "").toLowerCase().includes(n) ||
        (a.agent_type ?? "").toLowerCase().includes(n),
    );
  }, [q]);

  return (
    <>
      <h2 className="section-title" style={{ marginTop: 28 }}>
        Carcinogens
      </h2>
      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 360 }}
          placeholder="Search name, CAS, type…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <span className="muted small">{rows.length} of {AGENTS.length}</span>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>CAS</th>
              <th>IARC group</th>
              <th>Type</th>
              <th>Scored KCCs</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => {
              const scored = Object.values(a.evidence).filter((s) => s > 0).length;
              return (
                <tr key={a.id} className="clickable" onClick={() => navigate(`carcinogens/${a.id}`)}>
                  <td style={{ fontWeight: 600 }}>{a.name}</td>
                  <td className="mono">{a.cas}</td>
                  <td>
                    {a.iarc_group !== "—" ? <span className="chip">{a.iarc_group}</span> : <span className="muted">—</span>}
                  </td>
                  <td className="muted small">{a.agent_type ?? "—"}</td>
                  <td>{scored}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
