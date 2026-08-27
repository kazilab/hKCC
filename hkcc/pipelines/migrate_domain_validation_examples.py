"""Seed ``candidate_domain_validation_examples`` from the EMD simulation paper.

The four systems models were built to test whether the candidate domains hold up
as *annotation rules*, not to produce new carcinogenicity evidence. What they
yield is a set of statements of the form "this measurement does not settle the
question, that one does, and here is the competing explanation you have to
exclude". This migration carries thirteen of them into the database.

Nothing here touches ``evidence``. A model result is not an independent
mechanistic positive: the observations used to constrain a model cannot be
counted a second time as the model's output. The table therefore has no ``score``
column, and ``evidence`` has no foreign key to it - see docs/KCC_EVIDENCE_RULES.md.

Provenance is the simulation paper, inserted here as ``kazi2026-emd-sim``. It is
deliberately *not* ``kazi2026-emd``: that is the framework manuscript, a
different paper, and pointing at it would misattribute where these results came
from. Both are manuscript records with no DOI, which is stated rather than
invented. ``source_locator`` names the individual validation check, which the
reference itself cannot.

Usage::

    python -m hkcc.pipelines.migrate_domain_validation_examples            # dry-run
    python -m hkcc.pipelines.migrate_domain_validation_examples --apply    # write
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

#: The simulation paper. Separate from `kazi2026-emd` (the framework paper).
SOURCE_REF = {
    "id": "kazi2026-emd-sim",
    "year": 2026,
    "authors": "Kazi JU, Sarigiannis DA, Pienta KJ",
    "title": ("Systems biology models test emerging mechanistic domains in "
              "carcinogen evidence mapping"),
    "journal": "Manuscript",
    "source": "foundational",
}

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS candidate_domain_validation_examples (
	id VARCHAR(64) NOT NULL,
	domain_id VARCHAR(32) NOT NULL,
	kcc_id VARCHAR(32),
	sort_order SMALLINT NOT NULL,
	title VARCHAR(255) NOT NULL,
	alternative_explanation TEXT NOT NULL,
	insufficient_measurement TEXT NOT NULL,
	discriminating_measurement TEXT NOT NULL,
	simulation_finding TEXT NOT NULL,
	annotation_implication TEXT NOT NULL,
	evidentiary_status VARCHAR(32) NOT NULL,
	evidentiary_note TEXT,
	robustness_note TEXT,
	source_locator VARCHAR(255),
	source_ref_id VARCHAR(64),
	PRIMARY KEY (id),
	CONSTRAINT uq_domain_validation_sort UNIQUE (domain_id, sort_order),
	CONSTRAINT ck_domain_validation_sort CHECK (sort_order > 0),
	CONSTRAINT ck_domain_validation_status CHECK (evidentiary_status IN
		('data-constrained','design-constrained','structural',
		'illustrative','prior-dominated','predictive')),
	FOREIGN KEY(domain_id) REFERENCES candidate_domains (id) ON DELETE CASCADE,
	FOREIGN KEY(kcc_id) REFERENCES kccs (id) ON DELETE SET NULL,
	FOREIGN KEY(source_ref_id) REFERENCES "references" (id) ON DELETE SET NULL
)
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_cdve_domain_id ON candidate_domain_validation_examples (domain_id)",
    "CREATE INDEX IF NOT EXISTS ix_cdve_kcc_id ON candidate_domain_validation_examples (kcc_id)",
    "CREATE INDEX IF NOT EXISTS ix_cdve_source_ref_id ON candidate_domain_validation_examples (source_ref_id)",
)

FIELDS = ("id", "domain_id", "kcc_id", "sort_order", "title", "alternative_explanation",
          "insufficient_measurement", "discriminating_measurement", "simulation_finding",
          "annotation_implication", "evidentiary_status", "evidentiary_note",
          "robustness_note", "source_locator", "source_ref_id")


def _ex(id, domain, kcc, order, title, alt, insufficient, discriminator,
        finding, implication, status, note, robustness, locator) -> dict:
    return dict(zip(FIELDS, (id, domain, kcc, order, title, alt, insufficient,
                             discriminator, finding, implication, status, note,
                             robustness, locator, SOURCE_REF["id"])))


EXAMPLES = [
    # --- EMD1: epitranscriptomic regulation ---------------------------------
    _ex("emd1-val-01", "emd1", "kcc-04", 1,
        "Global m6A can conceal site-specific effects",
        "A single global RNA-methylation scalar adequately describes the exposure response.",
        "Global or transcriptome-averaged m6A abundance.",
        "Site- and transcript-resolved m6A, with transcript identity and reader-dependent RNA fate.",
        "Under chronic arsenic the modelled APOBEC3B and NEDD4L sites decreased, the antioxidant "
        "module increased, and the repair-site proxy was approximately unchanged. The average lost "
        "mechanistic information that was present at the individual sites.",
        "EMD1 should require site or transcript resolution; a global m6A shift alone does not qualify.",
        "data-constrained",
        "Mixed model: measured, digitised and fitted quantities alongside structural assumptions.",
        "Site-specific FTO targets and several downstream effects were sensitivity-stable; mean m6A was not.",
        "EMD1 Results - “Site-specific m6A responses under chronic arsenic”"),

    _ex("emd1-val-02", "emd1", "kcc-04", 2,
        "Reader identity is required to interpret an m6A change",
        "A change in m6A has one monotone effect on all affected transcripts.",
        "m6A direction without transcript identity and reader context.",
        "Transcript-specific decay, stabilisation or translation, with a reader-resolved perturbation.",
        "FTO inhibition moved APOBEC3B and NEDD4L in opposite transcript directions, because the "
        "modelled reader effects carry opposite signs.",
        "Preserve reader and RNA-fate information; do not infer function from methylation direction alone.",
        "data-constrained",
        "Data-concordance and encoding-consistency result, anchored by published transcript-decay mechanisms.",
        "The opposing transcript directions are a load-bearing model result and are supported by published kinetics.",
        "EMD1 validation check V12"),

    _ex("emd1-val-03", "emd1", "kcc-03", 3,
        "Separate edge existence from exposure-specific engagement",
        "Because a writer-repair mechanism exists, chronic arsenic necessarily engages it.",
        "General support for a writer-dependent repair mechanism, without exposure-specific site evidence.",
        "Exposure-specific repair-site m6A with a matched genome-maintenance readout, ideally with "
        "direct perturbation and rescue.",
        "The repair coupling stays active under direct writer perturbation, while nominal chronic "
        "arsenic leaves the repair-site proxy and genome-maintenance capacity at the null.",
        "A typed downstream relation can exist while a particular exposure has not been shown to engage it.",
        "structural",
        "The direct-writer response is a model implication, not matched empirical validation.",
        "The arsenic-null state is structural in the nominal model. The deposited tracks are consistent "
        "with no site-specific effect but do not exclude a moderate one.",
        "EMD1 Results - “Genome-maintenance capacity: an edge that is present but shows no "
        "detectable engagement”"),

    # --- EMD2: microbiome-mediated toxicokinetics ---------------------------
    _ex("emd2-val-01", "emd2", "kcc-01", 1,
        "A urinary metabolite can be matched by a host-only null",
        "Host metabolism alone generates the observed BCPN.",
        "Urinary BCPN, or total urothelial metabolite exposure.",
        "Paired luminal and systemic measurements, especially the caecum-to-plasma BCPN ratio.",
        "A refitted host-only model reproduces urinary BCPN while remaining unable to reproduce the "
        "lumen-first caecum/plasma pattern that microbial generation produces.",
        "Metabolite presence alone is not enough when host and microbial routes make the same molecule.",
        "design-constrained",
        "Toxicokinetic model; absolute microbial capacities are illustrative.",
        "The null comparison held in 400/400 heuristic rate-perturbation draws.",
        "EMD2 validation check V7"),

    _ex("emd2-val-02", "emd2", "kcc-01", 2,
        "Use independent microbial handles rather than taxonomy alone",
        "Metabolite changes reflect unrelated host changes rather than microbial transformation.",
        "Taxonomic association, or a single community perturbation without evidence of functional transformation.",
        "Orthogonal manipulations - antibiotics, germ-free comparison, and restoration with a "
        "converting isolate or community - while host parameters stay unchanged.",
        "Microbiota depletion and germ-free conditions reduce modelled microbial BCPN, and a "
        "converting mono-colonised arm restores the luminal phenotype towards conventional.",
        "Prefer causal community or isolate evidence and demonstrated biochemical transformation over taxonomy.",
        "design-constrained",
        "Community capacities are structurally assigned rather than fitted.",
        "The antibiotic and germ-free checks are highly robust. Mono-colonised restoration is a "
        "held-out model prediction, not independent empirical validation of the assigned capacity.",
        "EMD2 validation checks V2-V4"),

    _ex("emd2-val-03", "emd2", "kcc-01", 3,
        "Total metabolite exposure is not a provenance readout",
        "Higher total BCPN exposure necessarily means greater microbial conversion.",
        "Total urothelial BCPN exposure used as a surrogate for microbial provenance.",
        "A provenance-sensitive spatial measurement such as the caecum/plasma ratio, plus functional "
        "community information.",
        "The non-converting two-member consortium can rank above the antibiotic arm on total urothelial "
        "exposure while producing no microbial BCPN at all; the spatial ratio correctly reports the "
        "absence of microbial conversion.",
        "Do not infer microbial conversion from total metabolite burden alone.",
        "structural",
        "Model-derived negative result.",
        "The mis-ranking against the antibiotic arm held in 399/400 draws.",
        "EMD2 validation checks V8 and V12"),

    # --- EMD3: phenotypic plasticity ----------------------------------------
    _ex("emd3-val-01", "emd3", "kcc-04", 1,
        "The same stem-like fraction can arise by induction or by selection",
        "A higher stem-like fraction proves exposure-induced state conversion.",
        "A single endpoint stem-like fraction.",
        "Longitudinal fractions with an explicit alternative-model comparison; preferably absolute "
        "counts or lineage information.",
        "Pure induction and pure selection were matched to the same 20% stem-like fraction at day 14 "
        "and are indistinguishable at that endpoint.",
        "A marker-fraction increase alone should not satisfy EMD3.",
        "illustrative",
        "Structural identifiability result; baseline population rates are chosen rather than measured.",
        "The endpoint indistinguishability is a constructed structural result, not a parameter estimate.",
        "EMD3 validation check V4"),

    _ex("emd3-val-02", "emd3", "kcc-04", 2,
        "Absolute counts break a fraction-level degeneracy",
        "Selection and differential cytotoxicity can be separated by collecting more fraction time points.",
        "Stem-like fractions alone, even measured longitudinally.",
        "Stem-like fraction plus absolute total-cell count, lineage tracing, or equivalent population "
        "gain/loss information.",
        "Selection and non-stem differential death are algebraically identical in the observed "
        "fraction, whereas total counts distinguish expansion from killing.",
        "EMD3 should require a design able to exclude selection and cytotoxicity, not simply more "
        "fraction measurements.",
        "structural",
        "Algebraic result, carried by an illustrative population model.",
        "The fraction-level degeneracy is algebraic. Counts broke it in 58/60 heuristic baseline-rate draws.",
        "EMD3 validation checks V7-V8"),

    _ex("emd3-val-03", "emd3", "kcc-04", 3,
        "Compare mechanisms instead of fitting induction alone",
        "A non-zero fitted induction parameter is sufficient evidence of plasticity.",
        "An interval for an induction parameter from a model that omits selection and differential death.",
        "Model comparison across induction, selection, combined and differential-death structures, "
        "preferably using fractions plus absolute counts.",
        "An induction-only analysis can confidently report non-zero induction for purely selective or "
        "purely cytotoxic synthetic data; model comparison avoids that call on the same data.",
        "Explicit alternatives and model specification are part of the EMD3 evidence requirement.",
        "illustrative",
        "Identifiability and design result.",
        "The nominal false-positive result is marginal across baseline-rate uncertainty. Present it as a "
        "misspecification caution, not as a universal false-positive frequency.",
        "EMD3 validation checks V5, V6 and V9"),

    _ex("emd3-val-04", "emd3", "kcc-09", 4,
        "A stem-like marker is not a replicative-potential readout",
        "Because the refined KCC framework lists stem-cell genes among KCC9-relevant endpoints, an "
        "exposure-induced stem-like state is itself evidence of immortalisation.",
        "Stem-cell marker expression, stem-like fraction, or the size of a stem-like or immortal "
        "attractor basin.",
        "A telomere-maintenance or replicative-bypass readout measured directly - telomerase activity, "
        "telomere length, or demonstrated escape from replicative arrest - with the exposure shown to "
        "reach it.",
        "In the Boolean attractor layer the modelled exposure enlarges the immortal basin from 10.2% to "
        "14.3% while immortal reachability stays at exactly zero in every condition. Every attractor in "
        "that basin is entered only from a start state where telomere maintenance is already on.",
        "Stem-like state and limitless replicative potential are separate claims needing separate "
        "readouts. A stem-marker or basin-size increase must never be filed as KCC9 evidence.",
        "structural",
        "A property of the network wiring, deliberately not sampled in the ensemble.",
        "Structural. Note that the zero-reachability result is encoded (IMMORTAL requires TERT, and "
        "nothing on the exposure path activates TERT), so it is not itself the finding. The finding is "
        "the divergence between the two statistics: the plausible-looking summary moves and the "
        "claim-bearing one does not.",
        "EMD3 validation checks V3 and V15"),

    # --- EMD4: persistent senescence ----------------------------------------
    _ex("emd4-val-01", "emd4", "kcc-06", 1,
        "Withdrawal or longitudinal data reveal persistence hidden by endpoints",
        "A no-feedback senescence model sufficiently explains the endpoint dose-response.",
        "A forward endpoint dose-response without a discriminating time course.",
        "A longitudinal time course, or exposure withdrawal with continued senescence and SASP measurement.",
        "A no-feedback model reproduced the forward endpoint dose-response almost perfectly "
        "(R² = 0.996) but relaxed to baseline after withdrawal, whereas the feedback model retained "
        "a persistent state.",
        "Persistence should be demonstrated directly; endpoint agreement alone should not satisfy EMD4.",
        "prior-dominated",
        "Mechanistic hypothesis test. Withdrawal persistence is anchored to published arsenite "
        "observations, but most parameter magnitudes are chosen.",
        "Reference-dose persistence after withdrawal held in 231/250 heuristic parameter draws.",
        "EMD4 validation checks V2 and V11"),

    _ex("emd4-val-02", "emd4", "kcc-06", 2,
        "Stress-responsive markers can overstate the latent senescent state",
        "A positive SA-β-gal or DDR-foci readout alone establishes persistent senescence.",
        "A single senescence-associated marker, especially during active stress exposure.",
        "A multi-marker panel spanning arrest, structural change, DDR and secreted functional SASP, "
        "measured over time.",
        "In the low-dose arm the stress-responsive SA-β-gal and DDR-foci readouts overstate the "
        "modelled latent senescent fraction during exposure.",
        "Require construct-valid multi-marker evidence and functional secretome information rather than "
        "one marker.",
        "structural",
        "Observation model informed by current senescence-marker guidance.",
        "The SA-β-gal overstatement during exposure was sign-robust. The separate claim that a "
        "marker must fall after withdrawal was not robust and is deliberately not made here.",
        "EMD4 validation check V3"),

    _ex("emd4-val-03", "emd4", "kcc-09", 3,
        "Preserve the opposing polarity between senescence and KCC9",
        "Exposure-induced senescence can be counted as positive evidence for immortalisation.",
        "Senescence burden interpreted as a positive KCC9 signal.",
        "A separate escape or immortalisation readout demonstrating bypass of, or escape from, arrest.",
        "Increasing senescence does not activate a positive immortalisation path. Escape is modelled "
        "separately and can increase while the senescent burden falls.",
        "Keep EMD4-KCC9 contrastive: senescence must never be scored as positive KCC9 evidence without "
        "an independent escape or immortalisation observation.",
        "structural",
        "Directionality rule encoded in the model wiring.",
        "Structural rather than parameter-dependent.",
        "EMD4 validation check V9"),
]


def default_db() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "hkcc.db"


def validate(con: sqlite3.Connection) -> list[str]:
    """Every reason the seed would be wrong against *this* database."""
    problems: list[str] = []
    domains = {r[0] for r in con.execute("SELECT id FROM candidate_domains")}
    kccs = {r[0] for r in con.execute("SELECT id FROM kccs")}
    links = {(d, k) for d, k in con.execute("SELECT domain_id, kcc_id FROM candidate_domain_kccs")}

    for ex in EXAMPLES:
        if ex["domain_id"] not in domains:
            problems.append(f"{ex['id']}: unknown domain {ex['domain_id']}")
        if ex["kcc_id"] is not None:
            if ex["kcc_id"] not in kccs:
                problems.append(f"{ex['id']}: unknown KCC {ex['kcc_id']}")
            # An example annotates a relation that already exists. If the pair is
            # not a link, either the mapping changed or the example is wrong -
            # both are reasons to stop rather than to invent a link.
            elif (ex["domain_id"], ex["kcc_id"]) not in links:
                problems.append(
                    f"{ex['id']}: ({ex['domain_id']}, {ex['kcc_id']}) is not a domain/KCC link"
                )
    seen = {}
    for ex in EXAMPLES:
        key = (ex["domain_id"], ex["sort_order"])
        if key in seen:
            problems.append(f"{ex['id']}: duplicate sort_order with {seen[key]}")
        seen[key] = ex["id"]
    return problems


def _ensure_reference(con: sqlite3.Connection) -> str:
    """Insert the simulation-paper reference if absent. Returns added/unchanged."""
    row = con.execute('SELECT id FROM "references" WHERE id = ?', (SOURCE_REF["id"],)).fetchone()
    if row:
        return "unchanged"
    cols = ", ".join(SOURCE_REF)
    marks = ", ".join("?" for _ in SOURCE_REF)
    con.execute(f'INSERT INTO "references" ({cols}) VALUES ({marks})', tuple(SOURCE_REF.values()))
    return "added"


def diff(con: sqlite3.Connection) -> dict[str, list[str]]:
    """What ``--apply`` would do, per example id."""
    out: dict[str, list[str]] = {"added": [], "updated": [], "unchanged": []}
    have = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='candidate_domain_validation_examples'"
    ).fetchone()
    if not have:
        out["added"] = [ex["id"] for ex in EXAMPLES]
        return out
    cols = ", ".join(FIELDS)
    current = {
        r[0]: r
        for r in con.execute(f"SELECT {cols} FROM candidate_domain_validation_examples")
    }
    for ex in EXAMPLES:
        row = current.get(ex["id"])
        if row is None:
            out["added"].append(ex["id"])
        elif tuple(row) != tuple(ex[f] for f in FIELDS):
            out["updated"].append(ex["id"])
        else:
            out["unchanged"].append(ex["id"])
    return out


def migrate(con: sqlite3.Connection) -> str:
    con.execute("PRAGMA foreign_keys=ON")
    with con:
        con.execute(CREATE_TABLE)
        for stmt in INDEXES:
            con.execute(stmt)
        ref = _ensure_reference(con)
        cols = ", ".join(FIELDS)
        marks = ", ".join("?" for _ in FIELDS)
        # Upsert, so a re-run reconciles edited text instead of failing or
        # silently leaving a stale row behind.
        updates = ", ".join(f"{f}=excluded.{f}" for f in FIELDS if f != "id")
        con.executemany(
            f"INSERT INTO candidate_domain_validation_examples ({cols}) VALUES ({marks}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            [tuple(ex[f] for f in FIELDS) for ex in EXAMPLES],
        )
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    if bad:
        raise SystemExit(f"foreign key check failed after migration: {bad[:5]}")
    return ref


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=default_db())
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    print(f"{args.db}\n")

    problems = validate(con)
    if problems:
        for p in problems:
            print(f"  ERROR  {p}")
        raise SystemExit(f"\n{len(problems)} validation error(s) - nothing written")

    by_domain: dict[str, int] = {}
    for ex in EXAMPLES:
        by_domain[ex["domain_id"]] = by_domain.get(ex["domain_id"], 0) + 1
    print("  " + "   ".join(f"{d}: {n}" for d, n in sorted(by_domain.items())))

    d = diff(con)
    print(f"\n  {len(d['added'])} to add, {len(d['updated'])} to update, "
          f"{len(d['unchanged'])} unchanged")
    for kind, label in (("added", "add"), ("updated", "update")):
        for eid in d[kind]:
            print(f"    {label:>7}  {eid}")

    if not args.apply:
        print("\ndry run - re-run with --apply to write")
        return

    ref = migrate(con)
    total = con.execute("SELECT COUNT(*) FROM candidate_domain_validation_examples").fetchone()[0]
    print(f"\nwritten. {total} validation examples; reference {SOURCE_REF['id']} {ref}.")
    print("evidence was not touched: these are annotation rules, not evidence rows.")
    con.close()


if __name__ == "__main__":
    main()
