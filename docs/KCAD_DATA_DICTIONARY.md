<!-- This file is auto-generated. Run: python -m pipelines.gen_kcad_docs -->

# KCAD data dictionary

> Source: **Rigutto G, McHale CM, Singam ERA, Rana I, Zhang L, Smith MT.**
> *Mapping assays to the key characteristics of carcinogens to support
> decision-making.* Database (Oxford) **2025**, article `baaf026`.
> DOI: [`10.1093/database/baaf026`](https://doi.org/10.1093/database/baaf026).

Definitions for every column in `suppl_data/filtered_table.csv`,
reproduced verbatim from KCManuscript Supplementary Table 2.

Programmatic access:

- API: `GET /api/v1/methodology/columns`
- Streamlit UI: `app/pages/9a_Methodology.py`
- DB table: `kcad_column_definitions`

See also: [`KCAD_ABBREVIATIONS.md`](KCAD_ABBREVIATIONS.md) for the glossary.

| Column | Definition |
| --- | --- |
| `KC` | Primary key characteristic of carcinogens |
| `Secondary_KC` | Other associated key characteristic |
| `KC_Subgroup` | Major endpoints associated with the key characteristic |
| `KC_Subgroup2` | Additional sub-grouping of the KC subgroup, if applicable |
| `Assay_endpoint` | The assay endpoint provides context to what biomarker/outcome measured by a particular assay is indicative of, and how it relates back to the broader KC/KC-subgrouping. For example, DNA adducts measured using [32P]-Postlabelling techniques indicate DNA damage ('Assay endpoint'). If within a given study the specific DNA adducts being measured are known to be caused by by-products of oxidative radicals, the KC subgroup provides context to the associated KC: 'oxidative damage to DNA'. |
| `Assay_endpoint2` | Additional sub-grouping of the KC endpoints, if applicable. For example, an assay may be used to measure a specific type of lipid peroxidation product (a by-product of reactive oxygen species reacting with cellular lipids and thus denoted as being the secondary assay endpoint, 'Assay endpoint II'). This by-product's relevance to a chemical's carcinogenic potential is its propensity to react with nucleophilic sites in DNA (DNA damage thus being primary assay endpoint for this assay, 'Assay endpoint I'.). |
| `Assay_endpoint3` | See row above, 'Assay endpoint III" offers additional subgrouping if deemed appropriate. For example, study authors may use methylation-specific PCR to confirm methylation status of CpG within the promoter region of a gene related with homologous recombination ('Assay endpoint III"). Methylation status may alter mRNA expression of this critical cell regulatory/DNA repair gene ('Assay Endpoint II'). The primary assay endpoint relating the given chemical agent's relation to KCs is thus "Locus-specific DNA methylation" (Assay endpoint I). |
| `Biomarker` | Indicates as to whether another stimulant or acitvation agent was applied to the experimental test system, required for carrying out the assay or demonstrating a particular effect |
| `Method` | Name or description of assay/method applied |
| `Method2` | Any additional details of the assay may be indicated here. This may either be a particular instrument, a specific method developed by a research team, etc. Many methods require the use of an additional technology |
| `Stimulant_activation_agent` | Substance (e.g. mitogen, cytokine, cell type, virus, hormone, etc.) used to provoke a specific biological response in cells or tissue. This is commonly used in immunological applications, such as  to assess a chemical agents effect on allergic response. |
| `Target_cell` | Cell line type used to evaluate the activity of various immune effector cells, such as cytotoxic T lymphocytes (CTLs), natural killer (NK) cells, and natural cytotoxicity (NC) assays |
| `Cell_format` | Indicates as to whether an assay is applied to a primary cell, primary tissue, a cell line, a cultured cell, or is cell-free |
| `Design` | Experimental design in which assay may be applied |
| `Organism` | Additonal experimental design information, as to whether assay is applied in humans vs. animals vs. plants, etc., including those that may be conducted ex vivo and in vitro. |
| `Species` | Indication as to whether an assay referenced within a publication/test guideline is to be conducted in a particular species for 'Animal' studies (or biological order - such as rodents). If the organism is 'Human', species is denoted as 'NA'. |
| `Mammalian` | Indication as to whether an assay is to be conducted in exclusively mammalian cells (or vice versa) per a particular reference (including test guidelines) |
| `Tissue` | Tissue type in which assay is conducted/biomarker is measured (if applicable) |
| `Tissue2` | Additional tissue type information |
| `Cell_type` | Cell type or specific cell line in which assay is conducted/biomarker is measured |
| `Transgenic` | Indicates if a transgenic cell line is used ('Yes') |
| `Immortalized` | Indicates if an immortalized cell line is used ('Yes') |
| `Monograph_num` | Monograph chemical agent |
| `Monograph_chem` | IARC monograph in which assay is referenced, if applicable |
| `OECD` | Associated OECD Test Guideline number, if applicable |
| `PMID` | PMID of any references used, if applicable |
| `DOI` | DOI of any references used, if applicable |
| `Citation` | Study author and year of reference publication |
