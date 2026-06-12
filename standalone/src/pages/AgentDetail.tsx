import { AGENT_BY_ID, KCCS, REF_BY_ID, referencesForAgent } from "../data";
import { agentBibtex } from "../lib/citations";
import { downloadText, href, scoreColor, scoreLabel } from "../lib/util";
import RefList from "../components/RefList";

export default function AgentDetail({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const agent = AGENT_BY_ID.get(id);
  if (!agent) {
    return (
      <div className="card" style={{ marginTop: 40 }}>
        <h2>Carcinogen not found</h2>
        <a href={href("carcinogens")}>← Back to carcinogens</a>
      </div>
    );
  }

  const refs = referencesForAgent(id);
  const scoredKccs = KCCS.filter((k) => (agent.evidence[k.id] ?? 0) > 0);

  return (
    <>
      <a className="back" href={href("carcinogens")}>
        ← All carcinogens
      </a>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <h1 style={{ margin: "0 0 6px", fontSize: "1.8rem" }}>{agent.name}</h1>
            <div className="muted small">
              CAS <span className="mono">{agent.cas}</span>
              {agent.agent_type ? ` · ${agent.agent_type}` : ""}
              {agent.evaluation_year ? ` · evaluated ${agent.evaluation_year}` : ""}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start", flexWrap: "wrap" }}>
            {agent.iarc_group !== "—" && <span className="chip">IARC {agent.iarc_group}</span>}
            <button className="btn" onClick={() => downloadText(`${agent.id}.bib`, agentBibtex(agent), "application/x-bibtex")}>
              BibTeX
            </button>
          </div>
        </div>
        {agent.summary && <p style={{ marginBottom: 0 }}>{agent.summary}</p>}
      </div>

      <h2 className="section-title">Evidence by Key Characteristic</h2>
      {scoredKccs.length === 0 ? (
        <p className="muted">No scored characteristics for this agent.</p>
      ) : (
        <div className="card">
          {scoredKccs.map((k) => {
            const s = agent.evidence[k.id] ?? 0;
            const cellRefs = (agent.evidence_refs[k.id] ?? [])
              .map((rid) => REF_BY_ID.get(rid))
              .filter(Boolean);
            return (
              <div key={k.id} style={{ padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="ev-row">
                  <a href={href(`kccs/${k.id}`)} style={{ fontWeight: 600 }}>
                    {k.n}. {k.short}
                  </a>
                  <div className="ev-track">
                    <div className="ev-fill" style={{ width: `${(s / 4) * 100}%`, background: scoreColor(s) }} />
                  </div>
                  <span title={scoreLabel(s)} style={{ fontWeight: 700, textAlign: "right" }}>
                    {s}
                  </span>
                </div>
                {cellRefs.length > 0 && (
                  <div className="muted small" style={{ paddingLeft: 4 }}>
                    {cellRefs.length} citation{cellRefs.length > 1 ? "s" : ""}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <h2 className="section-title">Linked literature ({refs.length})</h2>
      {refs.length === 0 ? (
        <p className="muted">No KCAD-linked references recorded for this agent.</p>
      ) : (
        <RefList refs={refs} />
      )}

      <div style={{ marginTop: 16 }}>
        <button className="btn" onClick={() => navigate("matrix")}>
          View in matrix
        </button>
      </div>
    </>
  );
}
