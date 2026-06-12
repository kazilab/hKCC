import { useMemo, useState } from "react";
import { data } from "../data";

export default function Methodology() {
  const [q, setQ] = useState("");
  const abbr = useMemo(() => {
    const n = q.trim().toLowerCase();
    if (!n) return data.abbreviations;
    return data.abbreviations.filter(
      (a) => a.abbreviation.toLowerCase().includes(n) || a.expansion.toLowerCase().includes(n),
    );
  }, [q]);
  const cols = useMemo(() => {
    const n = q.trim().toLowerCase();
    if (!n) return data.columnDefinitions;
    return data.columnDefinitions.filter(
      (c) => c.column_name.toLowerCase().includes(n) || (c.definition ?? "").toLowerCase().includes(n),
    );
  }, [q]);

  return (
    <>
      <h2 className="section-title" style={{ marginTop: 28 }}>
        Methodology
      </h2>
      <p className="muted small" style={{ marginTop: 0 }}>
        Source dataset: KCAD (Key Characteristics of Carcinogens Assay Database). Glossary and column
        data dictionary below.
      </p>
      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 360 }}
          placeholder="Search abbreviations & columns…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      <h3 className="section-title" style={{ fontSize: "1.1rem" }}>
        Abbreviations ({abbr.length})
      </h3>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead>
            <tr>
              <th style={{ width: 160 }}>Abbreviation</th>
              <th>Expansion</th>
            </tr>
          </thead>
          <tbody>
            {abbr.map((a) => (
              <tr key={a.abbreviation}>
                <td className="mono">{a.abbreviation}</td>
                <td className="small">{a.expansion}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="section-title" style={{ fontSize: "1.1rem" }}>
        Column dictionary ({cols.length})
      </h3>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table>
          <thead>
            <tr>
              <th style={{ width: 200 }}>Column</th>
              <th>Definition</th>
            </tr>
          </thead>
          <tbody>
            {cols.map((c) => (
              <tr key={c.column_name}>
                <td className="mono">{c.column_name}</td>
                <td className="small">{c.definition}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
