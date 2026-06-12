import { useMemo, useState } from "react";
import { ASSAYS } from "../data";

export default function Assays({ navigate }: { navigate: (p: string) => void }) {
  const [q, setQ] = useState("");
  const rows = useMemo(() => {
    const n = q.trim().toLowerCase();
    if (!n) return ASSAYS;
    return ASSAYS.filter(
      (a) =>
        a.name.toLowerCase().includes(n) ||
        (a.target ?? "").toLowerCase().includes(n) ||
        (a.type ?? "").toLowerCase().includes(n) ||
        (a.notes ?? "").toLowerCase().includes(n),
    );
  }, [q]);

  return (
    <>
      <h2 className="section-title" style={{ marginTop: 28 }}>
        Assay library
      </h2>
      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 360 }}
          placeholder="Search assays, targets, notes…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <span className="muted small">{rows.length} of {ASSAYS.length}</span>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead>
            <tr>
              <th>Assay</th>
              <th>Type</th>
              <th>Target</th>
              <th>KCCs</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 400).map((a) => (
              <tr key={a.id} className="clickable" onClick={() => navigate(`assays/${a.id}`)}>
                <td style={{ fontWeight: 600 }}>{a.name}</td>
                <td className="muted small">{a.type ?? "—"}</td>
                <td className="muted small">{a.target ?? "—"}</td>
                <td>{a.kcc_ids.length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 400 && (
        <p className="muted small">Showing first 400 — refine your search to narrow results.</p>
      )}
    </>
  );
}
