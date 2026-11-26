# timing experiments for the report: python3 experiments.py scaling|density|density_baseline [--quick]
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


def fmt(med):
    return f"{med:.6f}" if med is not None else ""


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
            rows.append([algo, radii, s, 3 * s, fmt(med), timeouts, seeds, mid_nodes])
            shown = f"{med:.4f} s" if med is not None else "> limit"
            print(f"{algo:9s} {radii:6s} s={s:<8d} median={shown:12s} timeouts={timeouts}/{seeds}",
                  flush=True)
            # too slow now: stop growing this one
            if med is None or med > LIMIT:
                break
    write_csv("scaling_quick.csv" if quick else "scaling.csv",
              ["algo", "radii", "s", "N", "median_sec", "timeouts", "runs", "median_nodes"], rows)


# the three DPs at a fixed size while the coverage density d changes.
def exp_density(quick=False):
    sizes = ({"quadratic": 1000, "segtree": 20000, "linear": 20000} if quick else
             {"quadratic": 4000, "segtree": 200000, "linear": 200000})
    rows = []
    for d in [1, 2, 3, 4, 6, 8, 12]:
        for algo in ("quadratic", "segtree", "linear"):
            radii = "equal" if algo == "linear" else "varied"
            s = sizes[algo]
            times = [run(algo, instance(s, d=d, radii=radii, seed=seed))[0] for seed in range(3)]
            med = median_with_timeouts(times, 0)
            rows.append([algo, radii, s, d, fmt(med)])
            print(f"d={d:<3d} {algo:9s} s={s:<7d} median={med:.4f} s", flush=True)
    write_csv("density_quick.csv" if quick else "density.csv",
              ["algo", "radii", "s", "density", "median_sec"], rows)


# the baseline at a fixed size while d changes, more seeds since its times vary a lot.
def exp_density_baseline(quick=False):
    s, seeds = (25, 5) if quick else (40, 11)
    rows = []
    for d in [1, 2, 3, 4, 6, 8, 12, 16]:
        times, nodes, timeouts = [], [], 0
        for seed in range(seeds):
            t, st = run("baseline", instance(s, d=d, radii="varied", seed=100 + seed))
            if t is None:
                timeouts += 1
            else:
                times.append(t)
                nodes.append(st["nodes"])
        med = median_with_timeouts(times, timeouts)
        mid_nodes = sorted(nodes)[len(nodes) // 2] if nodes else ""
        rows.append([s, d, fmt(med), timeouts, seeds, mid_nodes])
        shown = f"{med:.4f} s" if med is not None else "> limit"
        print(f"d={d:<3d} baseline s={s} median={shown:12s} timeouts={timeouts}/{seeds}", flush=True)
    write_csv("density_baseline_quick.csv" if quick else "density_baseline.csv",
              ["s", "density", "median_sec", "timeouts", "runs", "median_nodes_finished"], rows)


if __name__ == "__main__":
    jobs = {"scaling": exp_scaling,
            "density": exp_density,
            "density_baseline": exp_density_baseline}
    what = sys.argv[1] if len(sys.argv) > 1 else "scaling"
    if what not in jobs:
        print("choose one of:", ", ".join(jobs))
        sys.exit(1)
    jobs[what](quick="--quick" in sys.argv)
