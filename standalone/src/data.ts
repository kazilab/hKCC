import raw from "./data.json";
import type { Agent, Assay, Dataset, Kcc, Reference } from "./types";

export const data = raw as unknown as Dataset;

export const KCCS: Kcc[] = data.kccs;
export const AGENTS: Agent[] = data.agents;
export const REFERENCES: Reference[] = data.references;
export const ASSAYS: Assay[] = data.assays;

export const KCC_BY_ID = new Map(KCCS.map((k) => [k.id, k]));
export const AGENT_BY_ID = new Map(AGENTS.map((a) => [a.id, a]));
export const ASSAY_BY_ID = new Map(ASSAYS.map((a) => [a.id, a]));
export const REF_BY_ID = new Map(REFERENCES.map((r) => [r.id, r]));

export const KCC_IDS: string[] = KCCS.map((k) => k.id);

/** Agents with evidence >= minScore on a KCC, sorted by score desc. */
export function agentsForKcc(kccId: string, minScore = 2): (Agent & { kccScore: number })[] {
  return AGENTS.map((a) => ({ ...a, kccScore: a.evidence[kccId] ?? 0 }))
    .filter((a) => a.kccScore >= minScore)
    .sort((a, b) => b.kccScore - a.kccScore);
}

export function assaysForKcc(kccId: string): Assay[] {
  return ASSAYS.filter((a) => a.kcc_ids.includes(kccId));
}

const FOUNDATIONAL_TAGS = new Set(["Foundational", "Methodology", "Review", "Database"]);

/** References linked to a KCC, including foundational refs with no specific KCC. */
export function referencesForKcc(kccId: string): Reference[] {
  return REFERENCES.filter((r) => {
    if (r.kcc_ids.includes(kccId)) return true;
    return r.kcc_ids.length === 0 && r.tags.some((t) => FOUNDATIONAL_TAGS.has(t));
  });
}

export function referencesForAgent(agentId: string): Reference[] {
  const a = AGENT_BY_ID.get(agentId);
  if (!a) return [];
  return a.ref_ids.map((id) => REF_BY_ID.get(id)).filter((r): r is Reference => Boolean(r));
}

/** Deduplicate references by (year, normalized title) for the Literature view. */
export function uniqueLiterature(refs: Reference[]): Reference[] {
  const byKey = new Map<string, Reference>();
  const order: string[] = [];
  for (const ref of refs) {
    const title = (ref.title ?? "").replace(/\s+/g, " ").trim();
    if (!title || title === "-" || title === "—" || title === "–") continue;
    const key = `${ref.year ?? ""}|${title.toLowerCase()}`;
    const existing = byKey.get(key);
    if (!existing) {
      byKey.set(key, ref);
      order.push(key);
      continue;
    }
    if (score(ref) > score(existing)) byKey.set(key, ref);
  }
  return order.map((k) => byKey.get(k)!).filter(Boolean);
}

function score(ref: Reference): number {
  let s = 0;
  for (const f of [ref.doi, ref.pmid, ref.url, ref.article_id, ref.journal, ref.authors]) {
    const v = (f ?? "").toString().trim();
    if (v && v !== "—" && v !== "-") s += 1;
  }
  return s + ref.tags.length + ref.kcc_ids.length;
}
