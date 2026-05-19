// hKCC data — Key Characteristics of Human Carcinogens
// Curated demo data: 14 KCCs (original 10 from Smith et al. 2016 + 4 newer additions)
// Carcinogens are a mix of IARC Group 1, 2A, 2B with illustrative evidence scores.

window.KCCS = [
  {
    id: "kcc-01",
    n: 1,
    title: "Electrophilicity & metabolic activation",
    short: "Electrophilic",
    desc: "Is electrophilic or can be metabolically activated to electrophiles that form covalent adducts with macromolecules.",
    icon: "circle",
    color: "#8B2E2A",
    assayCount: 28,
    carcCount: 41,
    examples: ["Vinyl chloride", "Aflatoxin B1", "Benzo[a]pyrene"],
    keyAssays: ["DNA-adductomics (LC-MS/MS)", "Glutathione depletion assay", "Reactivity profiling (e.g. GSH-AS)"],
    mechanism: "Compounds undergo phase-I metabolic activation (often via CYP450) to produce reactive intermediates that covalently bind nucleophilic sites in DNA, RNA, and proteins."
  },
  {
    id: "kcc-02",
    n: 2,
    title: "Genotoxicity",
    short: "Genotoxic",
    desc: "Induces DNA damage including strand breaks, mutations, micronuclei, chromosomal aberrations, or DNA-protein crosslinks.",
    icon: "helix",
    color: "#8B2E2A",
    assayCount: 34,
    carcCount: 58,
    examples: ["Ionizing radiation", "Ethylene oxide", "1,3-Butadiene"],
    keyAssays: ["Ames bacterial reverse-mutation", "Comet assay", "Micronucleus test (in vitro + in vivo)", "γ-H2AX foci"],
    mechanism: "Direct or indirect induction of DNA lesions detectable in standardized genotoxicity batteries; high concordance with carcinogenicity in long-term rodent bioassays."
  },
  {
    id: "kcc-03",
    n: 3,
    title: "Altered DNA repair / genomic instability",
    short: "DNA repair",
    desc: "Alters DNA repair capacity or causes large-scale genomic instability (e.g. aneuploidy, polyploidy, chromothripsis).",
    icon: "grid",
    color: "#8B2E2A",
    assayCount: 19,
    carcCount: 29,
    examples: ["Cadmium", "Arsenic", "Nickel compounds"],
    keyAssays: ["Host-cell reactivation", "BER/NER/MMR functional assays", "Karyotype / SKY", "Chromosome painting"],
    mechanism: "Indirect carcinogens may not damage DNA themselves but compromise repair fidelity or chromosomal segregation, amplifying mutational burden over time."
  },
  {
    id: "kcc-04",
    n: 4,
    title: "Epigenetic alterations",
    short: "Epigenetic",
    desc: "Induces changes in DNA methylation, histone modification, or non-coding RNA expression that persist across cell divisions.",
    icon: "marks",
    color: "#8B2E2A",
    assayCount: 22,
    carcCount: 36,
    examples: ["Arsenic", "Nickel", "Diethylstilbestrol"],
    keyAssays: ["Whole-genome bisulfite sequencing", "ChIP-seq for H3K4/K9/K27", "miRNA / lncRNA profiling"],
    mechanism: "Heritable changes in gene expression without alteration of DNA sequence; can silence tumor suppressors or activate oncogenes long after exposure."
  },
  {
    id: "kcc-05",
    n: 5,
    title: "Oxidative stress",
    short: "Oxidative",
    desc: "Induces oxidative stress via ROS/RNS, mitochondrial dysfunction, or depletion of antioxidant defenses.",
    icon: "rays",
    color: "#8B2E2A",
    assayCount: 17,
    carcCount: 47,
    examples: ["Asbestos", "Diesel exhaust", "Cadmium"],
    keyAssays: ["DCFH-DA fluorescence", "8-oxo-dG measurement", "Nrf2/ARE reporter", "GSH/GSSG ratio"],
    mechanism: "Excess reactive species cause oxidative DNA lesions, lipid peroxidation, and signaling dysregulation; chronic ROS exposure is mechanistically linked to multiple tumor types."
  },
  {
    id: "kcc-06",
    n: 6,
    title: "Chronic inflammation",
    short: "Inflammation",
    desc: "Induces or sustains chronic inflammation through cytokine release, immune cell recruitment, or persistent tissue injury.",
    icon: "burst",
    color: "#8B2E2A",
    assayCount: 14,
    carcCount: 38,
    examples: ["Helicobacter pylori", "Hepatitis B virus", "Asbestos"],
    keyAssays: ["Cytokine panels (IL-6, TNF-α, IL-1β)", "Macrophage polarization (M1/M2)", "NF-κB reporter assays"],
    mechanism: "Sustained inflammatory microenvironments produce ROS/RNS, growth factors, and immunosuppressive signals that promote initiation, promotion, and progression."
  },
  {
    id: "kcc-07",
    n: 7,
    title: "Immunosuppression",
    short: "Immunosuppression",
    desc: "Is immunosuppressive — decreases immune surveillance against transformed cells.",
    icon: "shield",
    color: "#8B2E2A",
    assayCount: 11,
    carcCount: 18,
    examples: ["Cyclosporine A", "TCDD", "UV radiation"],
    keyAssays: ["NK-cell cytotoxicity", "T-cell proliferation", "Mixed lymphocyte reaction"],
    mechanism: "Reduced immune surveillance permits clonal expansion of pre-neoplastic cells; particularly relevant for virally-driven and skin malignancies."
  },
  {
    id: "kcc-08",
    n: 8,
    title: "Receptor-mediated effects",
    short: "Receptor",
    desc: "Modulates nuclear receptors (AhR, ER, AR, PPAR, etc.) or membrane receptors in ways that drive proliferation or differentiation.",
    icon: "diamond",
    color: "#8B2E2A",
    assayCount: 26,
    carcCount: 31,
    examples: ["TCDD (Dioxin)", "Diethylstilbestrol", "BPA"],
    keyAssays: ["AhR / ER / AR reporter assays (ToxCast)", "Receptor binding (radioligand)", "Co-activator recruitment"],
    mechanism: "Ligand-receptor interactions produce sustained transcriptional reprogramming; especially important for hormone-dependent tissues."
  },
  {
    id: "kcc-09",
    n: 9,
    title: "Immortalization",
    short: "Immortalization",
    desc: "Causes immortalization via telomerase activation or bypass of replicative senescence.",
    icon: "loop",
    color: "#8B2E2A",
    assayCount: 8,
    carcCount: 12,
    examples: ["HPV-16 (E6/E7)", "EBV", "HTLV-1"],
    keyAssays: ["TRAP telomerase activity", "Soft-agar colony formation", "Senescence-associated β-gal"],
    mechanism: "Activation of telomere-maintenance pathways or inactivation of p53/Rb axis enables indefinite proliferative capacity — a hallmark of malignancy."
  },
  {
    id: "kcc-10",
    n: 10,
    title: "Altered proliferation, death & nutrient supply",
    short: "Proliferation",
    desc: "Alters cell proliferation, cell death, angiogenesis, or nutrient supply in the tissue microenvironment.",
    icon: "wave",
    color: "#8B2E2A",
    assayCount: 31,
    carcCount: 52,
    examples: ["TCDD", "Phenobarbital", "Ethanol"],
    keyAssays: ["BrdU / Ki-67 incorporation", "Annexin-V apoptosis", "Tube formation (HUVEC)", "Glycolysis flux"],
    mechanism: "Imbalance between proliferation and apoptosis, coupled with neovascularization and metabolic rewiring, supports tumor outgrowth and expansion."
  },
  {
    id: "kcc-11",
    n: 11,
    title: "Microbiome alteration",
    short: "Microbiome",
    desc: "Alters composition or function of the host microbiota in ways linked to carcinogenesis.",
    icon: "dots",
    color: "#2D5959",
    assayCount: 9,
    carcCount: 14,
    examples: ["Ethanol", "Aspartame (proposed)", "Air pollutants"],
    keyAssays: ["16S rRNA sequencing", "Shotgun metagenomics", "Short-chain fatty acid profiling"],
    mechanism: "Recently proposed KCC. Dysbiosis can promote local inflammation, generate genotoxic metabolites (e.g. colibactin), and modulate xenobiotic metabolism.",
    isNew: true
  },
  {
    id: "kcc-12",
    n: 12,
    title: "Cellular senescence",
    short: "Senescence",
    desc: "Induces premature cellular senescence and a pro-tumorigenic senescence-associated secretory phenotype (SASP).",
    icon: "fade",
    color: "#2D5959",
    assayCount: 7,
    carcCount: 11,
    examples: ["Doxorubicin (therapy-related)", "Ionizing radiation", "Bleomycin"],
    keyAssays: ["SA-β-gal staining", "p16^INK4a / p21 induction", "SASP cytokine secretion"],
    mechanism: "Senescent cells secrete a pro-inflammatory, pro-mitogenic milieu (SASP) that can paradoxically promote proliferation and invasion of neighboring cells.",
    isNew: true
  },
  {
    id: "kcc-13",
    n: 13,
    title: "Altered stem-cell dynamics",
    short: "Stem cells",
    desc: "Disrupts normal stem- or progenitor-cell behavior, including self-renewal, lineage commitment, or niche signaling.",
    icon: "tree",
    color: "#2D5959",
    assayCount: 10,
    carcCount: 9,
    examples: ["Benzene (hematopoietic)", "Radon (lung)", "Ethanol"],
    keyAssays: ["Sphere/organoid formation", "Lineage tracing", "ALDH activity (Aldefluor)"],
    mechanism: "Expansion or mis-differentiation of tissue stem cells generates a larger pool of long-lived cells susceptible to mutation accumulation.",
    isNew: true
  },
  {
    id: "kcc-14",
    n: 14,
    title: "Disrupted intercellular communication",
    short: "Gap junctions",
    desc: "Disrupts gap-junction intercellular communication (GJIC) or other tissue-level signaling.",
    icon: "link",
    color: "#2D5959",
    assayCount: 6,
    carcCount: 13,
    examples: ["Phenobarbital", "DDT", "TPA"],
    keyAssays: ["Scrape-loading / dye transfer", "Connexin expression panels"],
    mechanism: "Loss of GJIC removes a key homeostatic constraint, allowing initiated cells to escape growth control imposed by neighboring normal cells.",
    isNew: true
  }
];

// Carcinogens — 26 entries, mix of IARC groups
// evidence[k] is 0..4 for KCC k (1-indexed via id minus 1)
function row(values) {
  const map = {};
  values.forEach((v, i) => { map["kcc-" + String(i + 1).padStart(2, "0")] = v; });
  return map;
}

window.CARCINOGENS = [
  {
    id: "benzene", name: "Benzene", cas: "71-43-2", group: "1",
    type: "Industrial chemical", sites: ["Acute myeloid leukemia", "Lymphoma"],
    summary: "Volatile aromatic hydrocarbon; widespread occupational exposure historically in petrochemical and shoe-manufacturing industries.",
    evidence: row([4, 4, 3, 2, 4, 2, 2, 1, 0, 3, 1, 1, 4, 1])
  },
  {
    id: "formaldehyde", name: "Formaldehyde", cas: "50-00-0", group: "1",
    type: "Industrial chemical", sites: ["Nasopharyngeal carcinoma", "Leukemia"],
    summary: "Reactive aldehyde used in resins, embalming, and lab fixation. Forms DNA-protein crosslinks at sites of contact.",
    evidence: row([4, 4, 3, 2, 3, 3, 1, 0, 0, 2, 0, 1, 2, 0])
  },
  {
    id: "aflatoxin-b1", name: "Aflatoxin B1", cas: "1162-65-8", group: "1",
    type: "Mycotoxin", sites: ["Hepatocellular carcinoma"],
    summary: "Fungal metabolite from Aspergillus contaminating grains and nuts. Bioactivated by CYP3A4 to 8,9-epoxide, the proximate carcinogen.",
    evidence: row([4, 4, 3, 2, 3, 2, 1, 0, 0, 3, 0, 0, 0, 0])
  },
  {
    id: "asbestos", name: "Asbestos (all forms)", cas: "1332-21-4", group: "1",
    type: "Mineral fiber", sites: ["Mesothelioma", "Lung", "Larynx", "Ovary"],
    summary: "Fibrous silicate minerals. Mechanical and frustrated phagocytosis drive chronic inflammation and ROS at the pleural surface.",
    evidence: row([0, 3, 3, 1, 4, 4, 1, 0, 0, 3, 0, 1, 1, 0])
  },
  {
    id: "tobacco-smoke", name: "Tobacco smoke", cas: "—", group: "1",
    type: "Complex mixture", sites: ["Lung", "Oral cavity", "Bladder", "Pancreas", "Esophagus"],
    summary: "Complex mixture of >7,000 chemicals including PAHs, nitrosamines, and aldehydes. The single largest preventable cause of cancer globally.",
    evidence: row([4, 4, 4, 4, 4, 4, 3, 2, 1, 4, 2, 2, 3, 2])
  },
  {
    id: "arsenic", name: "Arsenic (inorganic)", cas: "7440-38-2", group: "1",
    type: "Metalloid", sites: ["Skin", "Lung", "Bladder", "Kidney", "Liver"],
    summary: "Exposure via drinking water in many regions. Indirectly genotoxic; classic example of an epigenetic and DNA-repair-disrupting carcinogen.",
    evidence: row([2, 2, 4, 4, 4, 3, 3, 1, 1, 3, 2, 2, 2, 2])
  },
  {
    id: "cadmium", name: "Cadmium & compounds", cas: "7440-43-9", group: "1",
    type: "Heavy metal", sites: ["Lung", "Prostate (suspected)", "Kidney"],
    summary: "Industrial use in batteries and pigments. Disrupts MMR/BER repair fidelity and induces oxidative stress.",
    evidence: row([1, 2, 4, 3, 4, 2, 2, 1, 0, 2, 1, 1, 1, 0])
  },
  {
    id: "vinyl-chloride", name: "Vinyl chloride", cas: "75-01-4", group: "1",
    type: "Industrial chemical", sites: ["Hepatic angiosarcoma", "Hepatocellular carcinoma"],
    summary: "Monomer for PVC production. Activated by CYP2E1 to chloroethylene oxide, a potent DNA-alkylating agent.",
    evidence: row([4, 4, 2, 1, 2, 1, 0, 0, 0, 2, 0, 0, 0, 0])
  },
  {
    id: "butadiene", name: "1,3-Butadiene", cas: "106-99-0", group: "1",
    type: "Industrial chemical", sites: ["Hematolymphatic"],
    summary: "Synthetic rubber monomer. Forms reactive mono- and diepoxides via CYP2E1.",
    evidence: row([4, 4, 3, 1, 3, 1, 1, 0, 0, 2, 0, 0, 3, 0])
  },
  {
    id: "ethylene-oxide", name: "Ethylene oxide", cas: "75-21-8", group: "1",
    type: "Industrial chemical", sites: ["Lymphoid", "Breast"],
    summary: "Direct-acting alkylator widely used in sterilization. Classic SN2 electrophile forming N7-HOE-Gua adducts.",
    evidence: row([4, 4, 2, 1, 2, 1, 1, 0, 0, 2, 0, 0, 1, 0])
  },
  {
    id: "bap", name: "Benzo[a]pyrene", cas: "50-32-8", group: "1",
    type: "PAH", sites: ["Lung", "Skin", "Bladder"],
    summary: "Prototypical PAH from incomplete combustion. Activated by CYP1A1/1B1 + epoxide hydrolase to BPDE.",
    evidence: row([4, 4, 2, 2, 3, 2, 2, 3, 0, 3, 1, 1, 2, 1])
  },
  {
    id: "tcdd", name: "2,3,7,8-TCDD (Dioxin)", cas: "1746-01-6", group: "1",
    type: "Persistent organic pollutant", sites: ["All-sites (multisite promoter)"],
    summary: "Persistent AhR agonist with no direct genotoxicity. Iconic example of a receptor-mediated, promotional carcinogen.",
    evidence: row([0, 0, 0, 3, 2, 2, 4, 4, 0, 4, 1, 1, 1, 2])
  },
  {
    id: "des", name: "Diethylstilbestrol", cas: "56-53-1", group: "1",
    type: "Synthetic estrogen", sites: ["Vaginal clear-cell adenocarcinoma", "Breast"],
    summary: "Historic prescription estrogen; transplacental carcinogen with well-documented receptor-mediated mechanism.",
    evidence: row([2, 2, 1, 3, 1, 1, 0, 4, 0, 3, 0, 0, 1, 0])
  },
  {
    id: "hbv", name: "Hepatitis B virus", cas: "—", group: "1",
    type: "Biological agent", sites: ["Hepatocellular carcinoma"],
    summary: "Chronic infection drives hepatocyte injury, inflammation, and regeneration cycles; HBx protein has direct oncogenic activity.",
    evidence: row([0, 2, 2, 2, 3, 4, 2, 1, 2, 3, 0, 1, 2, 1])
  },
  {
    id: "hpv16", name: "HPV-16", cas: "—", group: "1",
    type: "Biological agent", sites: ["Cervix", "Oropharynx", "Anus"],
    summary: "High-risk papillomavirus. E6 degrades p53; E7 inactivates Rb — combined effect drives immortalization.",
    evidence: row([0, 2, 3, 2, 1, 2, 1, 0, 4, 3, 0, 0, 1, 0])
  },
  {
    id: "hpylori", name: "Helicobacter pylori", cas: "—", group: "1",
    type: "Biological agent", sites: ["Gastric adenocarcinoma", "MALT lymphoma"],
    summary: "Chronic gastric infection. Combines persistent inflammation with CagA/VacA virulence factors and microbiome disruption.",
    evidence: row([0, 2, 1, 1, 3, 4, 1, 0, 0, 2, 4, 0, 1, 1])
  },
  {
    id: "ionizing-radiation", name: "Ionizing radiation", cas: "—", group: "1",
    type: "Physical agent", sites: ["Multiple sites"],
    summary: "X-rays, γ-rays, neutrons. Directly ionizes DNA producing strand breaks and clustered damage.",
    evidence: row([0, 4, 3, 2, 4, 1, 1, 0, 0, 2, 0, 4, 2, 0])
  },
  {
    id: "uv", name: "Solar radiation (UV)", cas: "—", group: "1",
    type: "Physical agent", sites: ["Melanoma", "Squamous cell", "Basal cell"],
    summary: "UVB induces pyrimidine dimers; UVA drives oxidative damage and local immunosuppression.",
    evidence: row([0, 4, 2, 1, 4, 1, 3, 0, 0, 2, 0, 2, 1, 0])
  },
  {
    id: "ethanol", name: "Ethanol (alcoholic beverages)", cas: "64-17-5", group: "1",
    type: "Lifestyle / dietary", sites: ["Oral", "Esophageal", "Liver", "Breast", "Colorectal"],
    summary: "Metabolized to acetaldehyde (genotoxic) by ADH; also alters folate metabolism, hormones, and the gut microbiome.",
    evidence: row([3, 3, 2, 3, 3, 2, 1, 2, 0, 2, 4, 1, 2, 1])
  },
  {
    id: "acrylamide", name: "Acrylamide", cas: "79-06-1", group: "2A",
    type: "Industrial / dietary", sites: ["Suspected: kidney, endometrium"],
    summary: "Forms in heated starchy foods; metabolized to glycidamide which forms DNA adducts.",
    evidence: row([3, 3, 1, 1, 2, 1, 0, 1, 0, 1, 0, 0, 0, 0])
  },
  {
    id: "glyphosate", name: "Glyphosate", cas: "1071-83-6", group: "2A",
    type: "Pesticide", sites: ["Non-Hodgkin lymphoma (suspected)"],
    summary: "Broad-spectrum herbicide. Subject of ongoing controversy; IARC and EPA differ in classification.",
    evidence: row([1, 2, 1, 1, 3, 2, 1, 0, 0, 1, 3, 0, 0, 0])
  },
  {
    id: "diesel-exhaust", name: "Diesel engine exhaust", cas: "—", group: "1",
    type: "Complex mixture", sites: ["Lung", "Bladder (suspected)"],
    summary: "Particulate-rich mixture with PAHs, nitro-PAHs, and metals. Strong oxidative and inflammatory profile.",
    evidence: row([3, 3, 2, 2, 4, 4, 2, 1, 0, 3, 1, 1, 1, 0])
  },
  {
    id: "bpa", name: "Bisphenol A", cas: "80-05-7", group: "—",
    type: "Plasticizer", sites: ["Under evaluation"],
    summary: "Estrogenic monomer in polycarbonate plastics and epoxy resins. Not formally classified by IARC; mechanistic data extensive.",
    evidence: row([0, 1, 1, 3, 2, 1, 0, 4, 0, 2, 0, 1, 1, 0])
  },
  {
    id: "pfoa", name: "PFOA", cas: "335-67-1", group: "2B",
    type: "Industrial chemical", sites: ["Kidney", "Testicular (suspected)"],
    summary: "Persistent perfluorinated surfactant; activates PPARα and disrupts lipid and immune homeostasis.",
    evidence: row([0, 1, 1, 2, 2, 1, 2, 3, 0, 2, 1, 0, 0, 1])
  },
  {
    id: "tce", name: "Trichloroethylene", cas: "79-01-6", group: "1",
    type: "Industrial solvent", sites: ["Kidney", "Liver", "NHL"],
    summary: "Metabolized to reactive intermediates including chloral hydrate and DCVC; nephrotoxic with mutation signature in VHL.",
    evidence: row([3, 3, 2, 1, 3, 1, 1, 1, 0, 2, 0, 0, 1, 0])
  },
  {
    id: "radon", name: "Radon-222", cas: "14859-67-7", group: "1",
    type: "Physical agent", sites: ["Lung"],
    summary: "Decay-chain α-emitter; second leading cause of lung cancer globally after tobacco. Local clustered DNA damage in bronchial epithelium.",
    evidence: row([0, 4, 3, 1, 4, 1, 0, 0, 0, 2, 0, 2, 3, 0])
  }
];

// Assays library
window.ASSAYS = [
  { id: "ames", name: "Ames test", type: "In vitro", target: "Mutagenicity", kccs: ["kcc-02"], throughput: "Medium", oecd: "OECD TG 471", notes: "Bacterial reverse-mutation in S. typhimurium / E. coli strains." },
  { id: "comet", name: "Comet assay", type: "In vitro / in vivo", target: "DNA strand breaks", kccs: ["kcc-02", "kcc-03"], throughput: "Medium", oecd: "OECD TG 489", notes: "Single-cell gel electrophoresis under alkaline conditions." },
  { id: "mnt", name: "Micronucleus test", type: "In vitro / in vivo", target: "Clastogenicity / aneugenicity", kccs: ["kcc-02", "kcc-03"], throughput: "High", oecd: "OECD TG 487 / 474", notes: "Flow cytometry or microscopy quantification of MN-containing cells." },
  { id: "h2ax", name: "γ-H2AX foci", type: "In vitro", target: "DSB formation", kccs: ["kcc-02"], throughput: "High", oecd: "—", notes: "Immunofluorescence readout of double-strand-break repair foci." },
  { id: "trap", name: "TRAP telomerase activity", type: "In vitro", target: "Telomerase", kccs: ["kcc-09"], throughput: "Low", oecd: "—", notes: "PCR-based telomeric-repeat amplification protocol." },
  { id: "soft-agar", name: "Soft-agar colony formation", type: "In vitro", target: "Anchorage-independent growth", kccs: ["kcc-09", "kcc-10"], throughput: "Low", oecd: "—", notes: "Phenotypic transformation assay in primary or immortal lines." },
  { id: "ahr-rep", name: "AhR luciferase reporter", type: "In vitro", target: "AhR activation", kccs: ["kcc-08"], throughput: "High", oecd: "—", notes: "Stably transfected line; part of ToxCast aryl-hydrocarbon battery." },
  { id: "er-rep", name: "Estrogen receptor reporter", type: "In vitro", target: "ER agonism / antagonism", kccs: ["kcc-08"], throughput: "High", oecd: "OECD TG 455", notes: "Stably transfected human cell-based reporter." },
  { id: "dcfh", name: "DCFH-DA ROS assay", type: "In vitro", target: "Intracellular ROS", kccs: ["kcc-05"], throughput: "High", oecd: "—", notes: "Cell-permeant probe oxidized to fluorescent DCF." },
  { id: "nrf2", name: "Nrf2/ARE reporter", type: "In vitro", target: "Antioxidant response", kccs: ["kcc-05"], throughput: "High", oecd: "—", notes: "ARE-luciferase or HiBiT-tagged endogenous Nrf2." },
  { id: "wgbs", name: "Whole-genome bisulfite-seq", type: "Genomic", target: "DNA methylation", kccs: ["kcc-04"], throughput: "Low", oecd: "—", notes: "Single-base methylation map." },
  { id: "chipseq", name: "ChIP-seq (histone marks)", type: "Genomic", target: "Histone modifications", kccs: ["kcc-04"], throughput: "Low", oecd: "—", notes: "Genome-wide localization of H3K4me3, H3K27me3, H3K9me3, etc." },
  { id: "cytokine", name: "Multiplex cytokine panel", type: "In vitro / serum", target: "Inflammatory mediators", kccs: ["kcc-06"], throughput: "High", oecd: "—", notes: "Luminex or MSD 30-plex assays." },
  { id: "nk", name: "NK cytotoxicity", type: "Ex vivo", target: "Immune surveillance", kccs: ["kcc-07"], throughput: "Medium", oecd: "—", notes: "K562 target lysis quantified by flow cytometry." },
  { id: "16s", name: "16S rRNA sequencing", type: "Genomic", target: "Microbiota composition", kccs: ["kcc-11"], throughput: "Medium", oecd: "—", notes: "Amplicon sequencing of bacterial 16S V3-V4." },
  { id: "sab", name: "SA-β-gal staining", type: "In vitro", target: "Senescence", kccs: ["kcc-12"], throughput: "Low", oecd: "—", notes: "Histochemical readout for senescence-associated β-galactosidase." },
  { id: "sphere", name: "Organoid / sphere formation", type: "In vitro", target: "Stem-cell self-renewal", kccs: ["kcc-13"], throughput: "Low", oecd: "—", notes: "3D primary or iPSC-derived organoid systems." },
  { id: "gjic", name: "Scrape-loading dye transfer", type: "In vitro", target: "GJIC", kccs: ["kcc-14"], throughput: "Medium", oecd: "—", notes: "Lucifer-yellow transfer across gap junctions." }
];

// Literature
window.LITERATURE = [
  { id: "smith2016", year: 2016, authors: "Smith MT, Guyton KZ, Gibbons CF, et al.", title: "Key characteristics of carcinogens as a basis for organizing data on mechanisms of carcinogenesis.", journal: "Environmental Health Perspectives", vol: "124(6):713–721", doi: "10.1289/ehp.1509912", kccs: "all", cites: 1240, tag: "Foundational" },
  { id: "iarc2019", year: 2019, authors: "IARC Monographs Programme", title: "IARC Monographs on the identification of carcinogenic hazards to humans — Preamble (2019).", journal: "IARC", vol: "—", doi: "—", kccs: "all", cites: 980, tag: "Methodology" },
  { id: "guyton2018", year: 2018, authors: "Guyton KZ, Rieswijk L, Wang A, et al.", title: "Application of the key characteristics of carcinogens in cancer hazard identification.", journal: "Carcinogenesis", vol: "39(4):614–622", doi: "10.1093/carcin/bgy031", kccs: "all", cites: 460, tag: "Methodology" },
  { id: "samet2019", year: 2019, authors: "Samet JM, Chiu WA, Cogliano V, et al.", title: "The IARC Monographs: updated procedures for modern and transparent evidence synthesis.", journal: "JNCI", vol: "112(1):30–37", doi: "10.1093/jnci/djz169", kccs: "all", cites: 220, tag: "Methodology" },
  { id: "krewski2020", year: 2020, authors: "Krewski D, Bird M, Al-Zoughool M, et al.", title: "Key characteristics of 86 agents known to cause cancer in humans.", journal: "J Toxicol Environ Health B", vol: "22(7–8):244–263", doi: "10.1080/10937404.2019.1643536", kccs: "all", cites: 380, tag: "Review" },
  { id: "rieswijk2022", year: 2022, authors: "Rieswijk L, Brauer VS, Bailey J, et al.", title: "A mechanistic database for the key characteristics of carcinogens.", journal: "Environ Int", vol: "158", doi: "10.1016/j.envint.2021.106953", kccs: "all", cites: 95, tag: "Database" },
  { id: "kogevinas2024", year: 2024, authors: "Kogevinas M, Saracci R, Schernhammer E, et al.", title: "Microbiome-mediated mechanisms in cancer hazard identification.", journal: "Cancer Discov", vol: "14(3)", doi: "10.1158/2159-8290.CD-23-0921", kccs: ["kcc-11"], cites: 42, tag: "KCC-11" },
  { id: "ferrari2023", year: 2023, authors: "Ferrari R, Müller MM, Cosi V, et al.", title: "SASP-driven paracrine effects link senescence to carcinogenesis.", journal: "Nat Rev Cancer", vol: "23(11):754–770", doi: "—", kccs: ["kcc-12"], cites: 88, tag: "KCC-12" },
  { id: "chu2021", year: 2021, authors: "Chu Y, Khaw KW, Lee BY, et al.", title: "Stem-cell origin of carcinogen-driven malignancies: a unifying framework.", journal: "Cell Stem Cell", vol: "28(5)", doi: "—", kccs: ["kcc-13"], cites: 130, tag: "KCC-13" },
  { id: "trosko2019", year: 2019, authors: "Trosko JE", title: "Gap-junctional intercellular communication and the key characteristics of carcinogens.", journal: "Toxicol Res", vol: "35(3):225–237", doi: "—", kccs: ["kcc-14"], cites: 75, tag: "KCC-14" }
];
