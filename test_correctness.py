import random
import sys
from common import evaluate, InfeasibleError
from bruteforce import brute_force
from baseline import solve_baseline, SearchLimit
from fasterAlgo import solve, MinTree, NotProperError
from gen import generate

SOLVERS = [("baseline", solve_baseline),
           ("quadratic", lambda O, C, S, R: solve(O, C, S, R, "quadratic")),
           ("segtree", lambda O, C, S, R: solve(O, C, S, R, "segtree")),
           ("linear", lambda O, C, S, R: solve(O, C, S, R, "linear")),   # only on proper instances
           ("auto", lambda O, C, S, R: solve(O, C, S, R, "auto"))]


def random_instance(rng):
    L = rng.randint(5, 40)
    s = rng.randint(0, 11)
    S = [rng.randint(0, L) for _ in range(s)]
    R = [rng.choice([rng.randint(0, 6), 2]) for _ in range(s)]
    if rng.random() < 0.3:                        
        R = [rng.randint(0, 5)] * s
    O = []
    for _ in range(rng.randint(0, 8)):
        if s and rng.random() < 0.9:
            k = rng.randrange(s)
            O.append(rng.randint(S[k] - R[k], S[k] + R[k]))
        else:
            O.append(rng.randint(0, L))           
    C = [rng.randint(-2, L + 2) for _ in range(rng.randint(0, 12))]
    if rng.random() < 0.2:                        
        O = [x + 0.5 for x in O]
        C = [x + 0.5 for x in C]
    return O, C, S, R


def test_mintree(trials=300):
    """MinTree must agree with Python's min() after random updates and queries."""
    rng = random.Random(1)
    SENT = 10 ** 9
    for _ in range(trials):
        n = rng.randint(1, 40)
        tree = MinTree(n, SENT)
        arr = [SENT] * n                          # plain list kept in sync, for comparison
        for _ in range(60):
            if rng.random() < 0.5:
                pos, key = rng.randrange(n), rng.randint(0, 1000)
                tree.update(pos, key)
                arr[pos] = key
            else:
                lo = rng.randint(0, n)
                hi = rng.randint(lo, n)
                expect = min(arr[lo:hi], default=SENT)
                assert tree.query(lo, hi) == expect, ("MinTree wrong", n, lo, hi, arr)
    print(f"OK: MinTree agrees with min() on {trials} random arrays")


def main():
    test_mintree()
    trials = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    rng = random.Random(360)
    infeasible = 0
    linear_runs = 0
    for t in range(trials):
        O, C, S, R = random_instance(rng)
        _, opt = brute_force(O, C, S, R)
        if opt is None:
            infeasible += 1
        for name, solver in SOLVERS:
            try:
                chosen, cost = solver(O, C, S, R)
            except InfeasibleError:
                assert opt is None, (name, "said infeasible but brute force found", opt, O, C, S, R)
                continue
            except NotProperError:
                continue                          # linear doesn't apply here
            if name == "linear":
                linear_runs += 1
            ok, wet = evaluate(O, C, S, R, chosen)
            assert ok, (name, "returned a set that leaves a tree dry", O, C, S, R, chosen)
            assert wet == cost, (name, "reported cost", cost, "but real cost is", wet)
            assert cost == opt, (name, "found", cost, "but optimum is", opt, O, C, S, R)
    print(f"OK: {trials} random instances, all solvers match brute force "
          f"({infeasible} infeasible; linear DP ran on {linear_runs} proper instances)")


# bigger instances (s up to 60), too slow for brute force so the exact algorithms must agree.
def medium_check(trials=300):
    rng = random.Random(7)
    baseline_done = 0
    for t in range(trials):
        s = rng.randint(10, 60)
        L = rng.randint(50, 400)
        rmin = rng.randint(1, 10)
        rmax = rmin if rng.random() < 0.4 else rmin + rng.randint(1, 20)   # 40%: equal radii
        O, C, S, R = generate(s, rng.randint(1, 3 * s), rng.randint(0, 3 * s), L, rmin, rmax, t)
        answers = {}
        for m in ("quadratic", "segtree", "auto"):
            chosen, cost = solve(O, C, S, R, m)
            ok, wet = evaluate(O, C, S, R, chosen)
            assert ok and wet == cost, (m, "bad solution on medium instance", t)
            answers[m] = cost
        if s <= 40:                               # baseline joins if it finishes in 2 s
            try:
                _, cost = solve_baseline(O, C, S, R, time_limit=2)
                answers["baseline"] = cost
                baseline_done += 1
            except SearchLimit:
                pass                              # too slow on this one: skip it
        assert len(set(answers.values())) == 1, ("algorithms disagree", t, answers)
    print(f"OK: {trials} medium instances (s up to 60), all exact algorithms agree "
          f"(baseline finished within 2 s on {baseline_done} of them)")


if __name__ == "__main__":
    if "--medium" in sys.argv:
        medium_check()
    else:
        main()
