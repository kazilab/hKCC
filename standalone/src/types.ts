export interface Kcc {
  id: string;
  n: number;
  title: string;
  short: string;
  description: string | null;
  mechanism: string | null;
  icon: string | null;
  is_extended: boolean;
}

export interface Agent {
  id: string;
  name: string;
  cas: string;
  iarc_group: string;
  agent_type: string | null;
  summary: string | null;
  monograph_volume: string | null;
  evaluation_year: number | null;
  evidence: Record<string, number>;
  evidence_refs: Record<string, string[]>;
  ref_ids: string[];
}

export interface Reference {
  id: string;
  year: number | null;
  authors: string | null;
  title: string | null;
  journal: string | null;
  vol: string;
  doi: string;
  pmid: string | null;
  citations: number;
  source: string | null;
  article_id: string | null;
  url: string | null;
  tags: string[];
  kcc_ids: string[];
}

export interface Assay {
  id: string;
  name: string;
  name_alt: string | null;
  type: string | null;
  target: string | null;
  throughput: string | null;
  oecd_tg: string;
  notes: string;
  source: string | null;
  granularity: string | null;
  kcc_ids: string[];
  subgroups: { kcc_id: string; subgroup: string }[];
  study_designs: { kcc_id: string; design: string | null; source: string | null }[];
}

export interface Glossary {
  abbreviation: string;
  expansion: string;
}

export interface ColumnDef {
  column_name: string;
  definition: string;
}

export interface Dataset {
  meta: {
    version: string;
    generated: string;
    developer: string;
    contact: string;
    counts: { agents: number; kccs: number; assays: number; references: number };
  };
  kccs: Kcc[];
  agents: Agent[];
  references: Reference[];
  assays: Assay[];
  abbreviations: Glossary[];
  columnDefinitions: ColumnDef[];
}
