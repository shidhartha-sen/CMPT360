# timing experiments for the report: python3 experiments.py scaling [--quick]
# instances have o = c = s (N = 3s), radii all 10 ("equal") or uniform in [1, 20] ("varied"),
# line length chosen so a point is reached by d sprinklers on average (default d = 4).
import os
import sys
import time
from gen import generate
from baseline import solve_baseline, SearchLimit
from fasterAlgo import solve

# "reasonable time" per run, in seconds
LIMIT = 10.0
os.makedirs("results", exist_ok=True)


def instance(s, d=4.0, radii="varied", seed=1, o=None, c=None):
    rmin, rmax = (10, 10) if radii == "equal" else (1, 20)
    # 2 * average radius + 1
    avg_len = rmin + rmax + 1
    # line length that gives density d
    L = max(1, round(s * avg_len / d))
    return generate(s, s if o is None else o, s if c is None else c, L, rmin, rmax, seed)


# time one algorithm on one instance, returns (seconds, stats) or (None, stats) on timeout.
def run(algo, inst, limit=LIMIT):
    st = {}
    t0 = time.perf_counter()
    try:
        if algo == "baseline":
            solve_baseline(*inst, time_limit=limit, stats=st)
        else:
            solve(*inst, method=algo, stats=st)
    except SearchLimit:
        return None, st
    return time.perf_counter() - t0, st


# median where a timed-out run counts as slower than every finished run, None if the median timed out.
def median_with_timeouts(times, timeouts):
    vals = sorted(times) + [float("inf")] * timeouts
    if not vals:
        return None
    n = len(vals)
    m = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return None if m == float("inf") else m


def write_csv(name, header, rows):
    path = os.path.join("results", name)
    with open(path, "w") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    print(f"wrote {path} ({len(rows)} rows)")


def exp_scaling(quick=False):
    if quick:
        # tiny sizes, just to test the script
        plans = [("baseline", "varied", [10, 20, 30], 3),
                 ("quadratic", "varied", [250, 500, 1000], 3),
                 ("segtree", "varied", [1000, 2000, 4000], 3),
                 ("segtree", "equal", [1000, 2000, 4000], 3),
                 ("linear", "equal", [1000, 2000, 4000], 3)]
    else:
        # the real run (step 19)
        plans = [("baseline", "varied", list(range(10, 71, 4)), 5),
                 ("baseline", "equal", list(range(10, 71, 4)), 5),
                 ("quadratic", "varied", [250 * 2 ** k for k in range(10)], 3),
                 ("segtree", "varied", [1000 * 2 ** k for k in range(12)], 3),
                 ("segtree", "equal", [1000 * 2 ** k for k in range(12)], 3),
                 ("linear", "equal", [1000 * 2 ** k for k in range(12)], 3)]
    rows = []
    for algo, radii, sizes, seeds in plans:
        for s in sizes:
            times, nodes, timeouts = [], [], 0
            for seed in range(seeds):
                t, st = run(algo, instance(s, radii=radii, seed=seed))
                if t is None:
                    timeouts += 1
                else:
                    times.append(t)
                    nodes.append(st.get("nodes", 0))
            med = median_with_timeouts(times, timeouts)
            mid_nodes = sorted(nodes)[len(nodes) // 2] if nodes else ""
            rows.append([algo, radii, s, 3 * s, f"{med:.6f}" if med is not None else "",
                         timeouts, seeds, mid_nodes])
            shown = f"{med:.4f} s" if med is not None else "> limit"
            print(f"{algo:9s} {radii:6s} s={s:<8d} median={shown:12s} timeouts={timeouts}/{seeds}",
                  flush=True)
            # too slow now: stop growing this one
            if med is None or med > LIMIT:
                break
    write_csv("scaling_quick.csv" if quick else "scaling.csv",
              ["algo", "radii", "s", "N", "median_sec", "timeouts", "runs", "median_nodes"], rows)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "scaling"
    if what == "scaling":
        exp_scaling(quick="--quick" in sys.argv)
