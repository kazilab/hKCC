import type { Reference } from "../types";
import { referenceBibtex, referenceRis } from "../lib/citations";
import { downloadText } from "../lib/util";

function doiUrl(doi: string): string | null {
  if (!doi || doi === "—") return null;
  const clean = doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "").trim();
  return clean ? `https://doi.org/${clean}` : null;
}

export default function RefList({ refs }: { refs: Reference[] }) {
  return (
    <div className="card" style={{ padding: 0, overflow: "hidden" }}>
      <table>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Year</th>
            <th>Source</th>
            <th style={{ textAlign: "right" }}>Cite</th>
          </tr>
        </thead>
        <tbody>
          {refs.map((r) => {
            const url = r.url || doiUrl(r.doi);
            return (
              <tr key={r.id}>
                <td>
                  <div style={{ fontWeight: 600 }}>
                    {url ? (
                      <a href={url} target="_blank" rel="noreferrer">
                        {r.title || r.id}
                      </a>
                    ) : (
                      r.title || r.id
                    )}
                  </div>
                  <div className="muted small">
                    {r.authors ?? "Unknown authors"}
                    {r.journal ? ` · ${r.journal}` : ""}
                  </div>
                  {r.tags.length > 0 && (
                    <div style={{ marginTop: 4 }}>
                      {r.tags.map((t) => (
                        <span key={t} className="chip gray" style={{ marginRight: 4 }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </td>
                <td>{r.year ?? "—"}</td>
                <td className="muted small">{r.source ?? "—"}</td>
                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                  <button
                    className="btn"
                    style={{ padding: "4px 8px" }}
                    onClick={() => downloadText(`${r.id}.bib`, referenceBibtex(r), "application/x-bibtex")}
                  >
                    .bib
                  </button>{" "}
                  <button
                    className="btn"
                    style={{ padding: "4px 8px" }}
                    onClick={() => downloadText(`${r.id}.ris`, referenceRis(r), "application/x-research-info-systems")}
                  >
                    .ris
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
