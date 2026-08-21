"""Widen ``candidate_domain_kccs.relation`` from primary/secondary to four relations.

The two-value vocabulary was carrying four distinct meanings at once: *this is
where the evidence files*, *the domain causes this*, *this causes the domain*,
and *this is the opposite of the domain*. Collapsing them made two links point
the wrong way down the causal chain and left one link (EMD2 -> KCC2) unstatable,
even though the platform already ships a colibactin assay under EMD2.

Section 3 of the manuscript requires "explicit attribution of direction". This
migration is what makes the database able to express it.

New vocabulary
--------------
``home``
    The KCC an observation files under, in essentially every instance of the
    domain. Unconditional. The only relation that reads as "the domain belongs
    here", and the only one that should ever be summarised as a primary overlap.
``downstream``
    A KCC endpoint the domain can produce. Case-dependent.
``upstream``
    A KCC that induces or enables the domain. Same pair of nodes, arrow
    reversed - previously indistinguishable from ``downstream``.
``contrastive``
    A KCC of opposing polarity: evidentially adjacent, informative, and never a
    positive. EMD4 -> KCC9 is the only such link (a domain measuring induction
    of senescence against a characteristic defined as *bypass* of it).

Migration is not mechanical: ``primary`` does not map onto ``home``. The values
below come from the link-by-link audit against sections 4 and 5.1-5.4, the KCC
scope text in ``kccs``, and the shipped assay annotations. CD5 is the one
exception - it is outside the manuscript's scope and was not audited, so it is
carried over structurally (primary -> home, secondary -> downstream) and should
be reviewed separately.

Usage::

    python -m hkcc.pipelines.migrate_domain_relations            # dry-run report
    python -m hkcc.pipelines.migrate_domain_relations --apply    # write changes
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

RELATIONS = ("home", "downstream", "upstream", "contrastive")

# domain code -> {KCC number: relation}. The audited mapping.
TARGET: dict[str, dict[int, str]] = {
    "EMD1": {
        4: "home",          # nonmutational control of gene expression; the one unconditional home
        2: "downstream",    # only indirectly, via impaired genome maintenance
        3: "downstream",    # section 4's own worked example: altered RNA fate -> less DNA-repair protein
        10: "downstream",   # section 5.1 conditions it ("when altered RNA fate changes proliferation")
        5: "upstream",      # section 5.1: redox stress *mediates* the m6A change
    },
    "EMD2": {
        1: "home",          # section 4's worked example; microbial metabolism of nitrosamines
        6: "home",          # the domain's second limb - host inflammation is not a side case
        2: "downstream",    # ADDED: colibactin, already annotated as an EMD2 assay
        7: "downstream",
        8: "downstream",    # bile-acid / AhR ligands, after the metabolite crosses the barrier
        10: "downstream",
    },
    "EMD3": {
        4: "home",          # a durable identity change is epigenetically implemented
        9: "home",          # section 5.3's strong overlap (see the KCC9 scope caveat in the paper)
        10: "downstream",
        8: "upstream",      # section 5.3: receptor signalling *controls the transition*
    },
    "EMD4": {
        6: "home",          # a SASP is a chronic inflammatory secretory programme
        7: "downstream",
        10: "downstream",   # KCC10 covers angiogenesis and is bidirectional by definition
        5: "upstream",      # oxidative stress is the canonical inducer of premature senescence
        9: "contrastive",   # KCC9 is *bypass* of replicative senescence - opposite sign
    },
    # Not audited: outside the manuscript's four domains. Structural carry-over only.
    "CD5": {10: "home", 4: "downstream", 8: "downstream"},
}

NEW_TABLE = """
CREATE TABLE candidate_domain_kccs_new (
	domain_id VARCHAR(32) NOT NULL,
	kcc_id VARCHAR(32) NOT NULL,
	relation VARCHAR(16) NOT NULL,
	PRIMARY KEY (domain_id, kcc_id),
	CONSTRAINT ck_domain_kcc_relation CHECK (relation IN ('home','downstream','upstream','contrastive')),
	FOREIGN KEY(domain_id) REFERENCES candidate_domains (id) ON DELETE CASCADE,
	FOREIGN KEY(kcc_id) REFERENCES kccs (id) ON DELETE CASCADE
)
"""


def default_db() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "hkcc.db"


def current(con: sqlite3.Connection) -> dict[str, dict[int, str]]:
    out: dict[str, dict[int, str]] = {}
    for code, n, rel in con.execute(
        """SELECT d.code, k.n, l.relation FROM candidate_domain_kccs l
           JOIN candidate_domains d ON d.id = l.domain_id
           JOIN kccs k ON k.id = l.kcc_id"""
    ):
        out.setdefault(code, {})[n] = rel
    return out


def report(con: sqlite3.Connection) -> list[tuple[str, int, str, str]]:
    """Every (domain, kcc, before, after). ``before`` is '-' for an added link."""
    now = current(con)
    rows = []
    for code, links in TARGET.items():
        was = now.get(code, {})
        for n in sorted(set(was) | set(links)):
            rows.append((code, n, was.get(n, "-"), links.get(n, "DROPPED")))
    return rows


def migrate(con: sqlite3.Connection) -> None:
    ids = {c: i for c, i in con.execute("SELECT code, id FROM candidate_domains")}
    kcc_ids = {n: i for n, i in con.execute("SELECT n, id FROM kccs")}
    unknown = set(TARGET) - set(ids)
    if unknown:
        raise SystemExit(f"unknown domain codes: {sorted(unknown)}")

    con.execute("PRAGMA foreign_keys=OFF")
    with con:
        con.execute(NEW_TABLE)
        con.executemany(
            "INSERT INTO candidate_domain_kccs_new VALUES (?,?,?)",
            [(ids[c], kcc_ids[n], rel) for c, links in TARGET.items() for n, rel in links.items()],
        )
        con.execute("DROP TABLE candidate_domain_kccs")
        con.execute("ALTER TABLE candidate_domain_kccs_new RENAME TO candidate_domain_kccs")
    con.execute("PRAGMA foreign_keys=ON")
    if con.execute("PRAGMA foreign_key_check").fetchall():
        raise SystemExit("foreign key check failed after migration")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=default_db())
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    rows = report(con)
    changed = [r for r in rows if r[2] != r[3]]

    print(f"{args.db}\n")
    print(f"  {'domain':<7} {'kcc':<6} {'before':<12} {'after':<12}")
    print("  " + "-" * 40)
    for code, n, before, after in rows:
        mark = "  " if before == after else " *"
        print(f" {mark}{code:<7} KCC{n:<3} {before:<12} {after:<12}")
    print(f"\n  {len(rows)} links, {len(changed)} changing, "
          f"{sum(b == '-' for _, _, b, _ in rows)} added")

    if not args.apply:
        print("\ndry run - re-run with --apply to write")
        return
    migrate(con)
    after = current(con)
    assert all(after[c] == links for c, links in TARGET.items()), "post-migration mismatch"
    print("\nwritten. relation vocabulary is now: " + ", ".join(RELATIONS))
    con.close()


if __name__ == "__main__":
    main()
