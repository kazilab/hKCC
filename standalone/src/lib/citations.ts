import type { Agent, Reference } from "../types";
import { data } from "../data";

const DEVELOPER = data.meta.developer;
const CONTACT = data.meta.contact;
const VERSION = data.meta.version;
const YEAR = "2026";

export function resourceBibtex(): string {
  return (
    "@misc{hkcc2026,\n" +
    "  title = {hKCC: Key Characteristics of Human Carcinogens},\n" +
    `  version = {${VERSION}},\n` +
    `  year = {${YEAR}},\n` +
    `  publisher = {${DEVELOPER}},\n` +
    "  license = {CC-BY-4.0},\n" +
    `  note = {Contact: ${CONTACT}}\n` +
    "}\n"
  );
}

export function resourceRis(): string {
  return (
    "TY  - DATA\n" +
    "TI  - hKCC: Key Characteristics of Human Carcinogens\n" +
    `ET  - ${VERSION}\n` +
    `PY  - ${YEAR}\n` +
    `PB  - ${DEVELOPER}\n` +
    `N1  - Contact: ${CONTACT}\n` +
    "Licence  - CC-BY-4.0\n" +
    "ER  - \n"
  );
}

export function agentBibtex(agent: Agent): string {
  const key = agent.id.replace(/-/g, "");
  const cas = agent.cas && agent.cas !== "—" ? `, CAS ${agent.cas}` : "";
  return (
    `@misc{hkcc_agent_${key},\n` +
    `  title = {hKCC profile: ${agent.name}${cas}},\n` +
    "  howpublished = {hKCC database},\n" +
    `  version = {${VERSION}},\n` +
    `  year = {${YEAR}}\n` +
    "}\n"
  );
}

function canonicalDoi(doi: string): string | null {
  if (!doi || doi === "—") return null;
  return doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "").trim() || null;
}

export function referenceBibtex(ref: Reference): string {
  const key = ref.id.replace(/-/g, "");
  const doi = canonicalDoi(ref.doi);
  const doiLine = doi ? `,\n  doi = {${doi}}` : "";
  return (
    `@article{${key},\n` +
    `  author = {${ref.authors ?? ""}},\n` +
    `  title = {${ref.title ?? ""}},\n` +
    `  journal = {${ref.journal ?? ""}},\n` +
    `  year = {${ref.year ?? ""}},\n` +
    `  volume = {${ref.vol ?? ""}}${doiLine}\n` +
    "}\n"
  );
}

export function referenceRis(ref: Reference): string {
  const lines = [
    "TY  - JOUR",
    `AU  - ${ref.authors ?? ""}`,
    `TI  - ${ref.title ?? ""}`,
    `JO  - ${ref.journal ?? ""}`,
  ];
  if (ref.year) lines.push(`PY  - ${ref.year}`);
  const doi = canonicalDoi(ref.doi);
  if (doi) lines.push(`DO  - ${doi}`);
  lines.push("ER  - ");
  return lines.join("\n") + "\n";
}
