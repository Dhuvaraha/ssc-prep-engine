"""Editorial validator for categorical set statements, not a natural-language parser.

Enumerate occupied Venn regions: one witness per occupied region suffices for
all/no/some/some-not propositions. Universal statements have no existential
import unless nonempty terms are explicitly supplied. This convention must be
recorded by an editor; it is not a claim about every exam's conventions.
"""
from itertools import product


def evaluate(premises, conclusion, *, nonempty=()):
    premises, nonempty = list(premises), tuple(nonempty)
    statements = [*premises, conclusion]
    terms = sorted({term for _, left, right in statements for term in (left, right)} | set(nonempty))
    if not 1 <= len(terms) <= 4:
        raise ValueError("Editorial validator supports one to four terms")
    if any(kind not in {"all", "no", "some", "some_not"} for kind, _, _ in statements):
        raise ValueError("Unknown categorical proposition")
    regions = list(product((False, True), repeat=len(terms)))
    indices = {term: index for index, term in enumerate(terms)}

    def holds(statement, occupied):
        kind, left, right = statement
        a, b = indices[left], indices[right]
        overlap = any(region[a] and region[b] for region in occupied)
        outside = any(region[a] and not region[b] for region in occupied)
        return {"all": not outside, "no": not overlap,
                "some": overlap, "some_not": outside}[kind]

    valid = supporting = 0
    counterexample = None
    for mask in range(1 << len(regions)):
        occupied = [region for i, region in enumerate(regions) if mask & (1 << i)]
        if any(not any(region[indices[t]] for region in occupied) for t in nonempty):
            continue
        if not all(holds(statement, occupied) for statement in premises):
            continue
        valid += 1
        if holds(conclusion, occupied):
            supporting += 1
        elif counterexample is None:
            counterexample = [[term for term, member in zip(terms, region) if member]
                              for region in occupied]
    return {"consistent": valid > 0, "must_follow": valid > 0 and supporting == valid,
            "possible": supporting > 0, "counterexample": counterexample,
            "existence_assumptions": sorted(nonempty)}
