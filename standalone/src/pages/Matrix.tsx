import { useMemo, useState } from "react";
import { AGENTS, KCCS } from "../data";
import { scoreColor, scoreLabel, scoreTextColor } from "../lib/util";

export default function Matrix({ navigate }: { navigate: (p: string) => void }) {
  const [q, setQ] = useState("");
  const [group, setGroup] = useState("all");

  const groups = useMemo(() => {
    const s = new Set(AGENTS.map((a) => a.iarc_group).filter((g) => g && g !== "—"));
    return ["all", ...Array.from(s).sort()];
  }, []);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return AGENTS.filter((a) => {
      if (group !== "all" && a.iarc_group !== group) return false;
      if (needle && !a.name.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [q, group]);

  return (
    <>
      <h2 className="section-title" style={{ marginTop: 28 }}>
        Evidence matrix
      </h2>
      <p className="muted small" style={{ marginTop: 0 }}>
        Carcinogen × Key Characteristic evidence scores (0–4). Click a row to open the agent profile.
      </p>

      <div className="toolbar">
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="Filter carcinogens…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className="input" style={{ maxWidth: 200 }} value={group} onChange={(e) => setGroup(e.target.value)}>
          {groups.map((g) => (
            <option key={g} value={g}>
              {g === "all" ? "All IARC groups" : `IARC group ${g}`}
            </option>
          ))}
        </select>
        <span className="muted small">{rows.length} agents</span>
      </div>

      <div className="legend">
        {[0, 1, 2, 3, 4].map((s) => (
          <span key={s}>
            <span className="sw" style={{ background: scoreColor(s) }} />
            {s} · {scoreLabel(s)}
          </span>
        ))}
      </div>

      <div className="matrix-wrap">
        <table className="matrix">
          <thead>
            <tr>
              <th className="agent">Carcinogen</th>
              {KCCS.map((k) => (
                <th key={k.id} className="kcc" title={k.title}>
                  {k.n}. {k.short}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id}>
                <td className="agent" title={a.name} onClick={() => navigate(`carcinogens/${a.id}`)}>
                  {a.name}
                </td>
                {KCCS.map((k) => {
                  const s = a.evidence[k.id] ?? 0;
                  return (
                    <td
                      key={k.id}
                      className="cell"
                      style={{ background: scoreColor(s), color: scoreTextColor(s) }}
                      title={`${a.name} · ${k.title}: ${s} (${scoreLabel(s)})`}
                    >
                      {s > 0 ? s : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
