"""Fair baseline (Fable review, change #1a): a brute-force ENUMERATING policy.

The published head-to-heads pit the LLM agent against a `NAIVE_MAP` policy whose
map is hand-authored to OMIT the winning move — so it gives up. That measures the
authored incompleteness of the map, not a capability gap. The honest control is a
policy that, when stuck, installs ANY uninstalled library mechanism (brute force).

If the winning mechanism sits in the (≤3-item) library, enumeration finds it, so
the task does NOT demonstrate that an LLM agent is required. Only tasks whose real
fix cannot be expressed as "install a library item" would survive this baseline.

Run:  python scripts/enumerating_baseline.py
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))


def enumerate_solve(mechanisms, npass_of):
    """Install library mechanisms one at a time until all tests pass or exhausted."""
    active = set()
    edits = 0
    trail = []
    np_, nh, ap = npass_of(active)
    trail.append((sorted(active), np_, nh))
    for m in mechanisms:
        if ap:
            break
        active = set(active)
        active.add(m)
        edits += 1
        np_, nh, ap = npass_of(active)
        trail.append((sorted(active), np_, nh))
    return {"state": "DONE" if ap else "GIVE_UP", "edits": edits, "trail": trail,
            "n_mechanisms": len(mechanisms)}


def diauxie_case():
    import diauxie_demo as D

    def npass(active):
        axes = D.grade(D.simulate(active, {}))
        n = sum(a["verdict"] == "within_tol" for a in axes)
        return n, len(D.TESTS), n == len(D.TESTS)
    return enumerate_solve(list(D.LIBRARY), npass)


def diagnosis_case():
    import diagnosis_task as T

    def npass(active):
        v, _, _ = T.grade(active)
        n = sum(x == "within_tol" for x in v.values())
        return n, len(T.TESTS), n == len(T.TESTS)
    return enumerate_solve(T.MECHANISMS, npass)


def bistable_case():
    import bistable_task as T

    def npass(active):
        v, _, _ = T.grade(active)
        n = sum(x == "within_tol" for x in v.values())
        return n, len(T.TESTS), n == len(T.TESTS)
    return enumerate_solve(T.MECHANISMS, npass)


CASES = [("diauxie", diauxie_case), ("diagnosis", diagnosis_case), ("bistable", bistable_case)]


def main():
    print("FAIR ENUMERATING BASELINE — brute-force install-anything-when-stuck\n")
    solved = 0
    for name, fn in CASES:
        r = fn()
        if r["state"] == "DONE":
            solved += 1
        print(f"=== {name}: {r['state']} in {r['edits']} edits "
              f"(library of {r['n_mechanisms']}) ===")
        for act, np_, nh in r["trail"]:
            print(f"     {np_}/{nh}  {act}")
        print()
    print(f"SUMMARY: the brute-force baseline solves {solved}/{len(CASES)} menu tasks. "
          f"Where it reaches DONE, the naive-map policy's GIVE_UP reflects the authored "
          f"map, not a capability the task requires an agent for.")


if __name__ == "__main__":
    main()
