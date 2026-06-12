import { data } from "../data";
import { resourceBibtex, resourceRis } from "../lib/citations";
import { downloadText } from "../lib/util";

const CONTRIBUTE_SUBJECT = encodeURIComponent("hKCC score proposal");
const CONTRIBUTE_BODY = encodeURIComponent(
  "Agent (name / CAS):\nKey Characteristic (KC number):\nProposed score (0–4):\nRationale:\nSupporting references (DOI/PMID):\n",
);

export default function About() {
  const m = data.meta;
  const mailto = `mailto:${m.contact}?subject=${CONTRIBUTE_SUBJECT}&body=${CONTRIBUTE_BODY}`;
  return (
    <>
      <h2 className="section-title" style={{ marginTop: 28 }}>
        About hKCC
      </h2>
      <p style={{ maxWidth: 720 }}>
        hKCC is an open, versioned, citable mechanism atlas for human carcinogens. Each evidence
        score (0–4) links carcinogenic agents to the {m.counts.kccs} Key Characteristics framework
        with citation-level provenance. This is a fully self-contained, offline build — all data is
        embedded in this single HTML file; no server or network access is required.
      </p>

      <div className="card">
        <table>
          <tbody>
            <tr>
              <th style={{ width: 160 }}>Version</th>
              <td>v{m.version}</td>
            </tr>
            <tr>
              <th>Generated</th>
              <td>{m.generated}</td>
            </tr>
            <tr>
              <th>Developed by</th>
              <td>{m.developer}</td>
            </tr>
            <tr>
              <th>Contact</th>
              <td>
                <a href={`mailto:${m.contact}`}>{m.contact}</a>
              </td>
            </tr>
            <tr>
              <th>Licenses</th>
              <td>
                data <a href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</a> · code MIT
              </td>
            </tr>
            <tr>
              <th>Contents</th>
              <td>
                {m.counts.agents} carcinogens · {m.counts.kccs} key characteristics ·{" "}
                {m.counts.assays} assays · {m.counts.references} references
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="section-title">Cite this resource</h2>
      <div className="toolbar">
        <button className="btn primary" onClick={() => downloadText("hkcc.bib", resourceBibtex(), "application/x-bibtex")}>
          Download BibTeX
        </button>
        <button className="btn" onClick={() => downloadText("hkcc.ris", resourceRis(), "application/x-research-info-systems")}>
          Download RIS
        </button>
      </div>
      <pre className="code">{resourceBibtex()}</pre>

      <h2 className="section-title">Propose a score</h2>
      <div className="notice">
        This is a read-only, offline build, so in-app submission is disabled. To propose a new or
        revised evidence score, email the curation team with the agent, KC, proposed score (0–4),
        rationale, and supporting references.
      </div>
      <div className="toolbar" style={{ marginTop: 12 }}>
        <a className="btn primary" href={mailto}>
          Email a score proposal
        </a>
      </div>
    </>
  );
}
