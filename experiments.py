# timing experiments for the report:
# python3 experiments.py scaling|density|density_baseline|reductions|greedy|phases|memory [--quick]
# instances have o = c = s (N = 3s), radii all 10 ("equal") or uniform in [1, 20] ("varied"),
# line length chosen so a point is reached by d sprinklers on average (default d = 4).
import os
import subprocess
import sys
import time
from gen import generate
from common import build_intervals, check_feasible, evaluate
from baseline import solve_baseline, SearchLimit
from fasterAlgo import solve, reduce_intervals, reduce_r2, dp_quadratic, dp_segtree, dp_linear

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


# how many sprinklers R1, duplicates and R2 remove, for sparse vs dense trees.
def exp_reductions(quick=False):
    s = 10000 if quick else 100000
    rows = []
    # orange trees per sprinkler
    for ratio in [0.01, 0.1, 0.5, 1.0, 2.0]:
        for d in [1, 4, 16]:
            o = max(1, int(ratio * s))
            st = {}
            t0 = time.perf_counter()
            solve(*instance(s, d=d, radii="varied", seed=3, o=o), stats=st)
            dt = time.perf_counter() - t0
            kept = st["s_after_r2"] / s
            rows.append([s, o, ratio, d, st["s_after_r1"], st["s_after_dup"], st["s_after_r2"],
                         f"{kept:.3f}", f"{dt:.4f}"])
            print(f"o/s={ratio:<5} d={d:<3d} after R1 {st['s_after_r1']:>7}  after dup "
                  f"{st['s_after_dup']:>7}  after R2 {st['s_after_r2']:>7}  kept {100 * kept:.1f}%",
                  flush=True)
    write_csv("reductions_quick.csv" if quick else "reductions.csv",
              ["s", "o", "o_over_s", "density", "after_R1", "after_dup", "after_R2",
               "kept_fraction", "sec"], rows)


# leftmost dry tree, take the sprinkler reaching it that wets the fewest new cacti
# (ties: the one reaching farthest right), fast but not always optimal.
def greedy(O, C, S, R):
    Os, Cs, ivs = build_intervals(O, C, S, R)
    wet = [False] * len(Cs)
    chosen, p, total = [], 0, 0
    while p < len(Os):
        best = None
        for v in ivs:
            # reaches tree p
            if v[3] <= p < v[4]:
                new = sum(1 for t in range(v[5], v[6]) if not wet[t])
                key = (new, -v[1])
                if best is None or key < best[0]:
                    best = (key, v)
        v = best[1]
        for t in range(v[5], v[6]):
            if not wet[t]:
                wet[t] = True
                total += 1
        chosen.append(v[2])
        # next dry tree
        p = v[4]
    return chosen, total


def exp_greedy(quick=False):
    trials = 100 if quick else 1000
    rows = []
    for d in [2, 4, 8]:
        worse, excess, rel = 0, [], []
        for seed in range(trials):
            inst = instance(60, d=d, radii="varied", seed=seed)
            _, opt = solve(*inst)
            gch, g = greedy(*inst)
            # greedy's answer is at least valid
            assert evaluate(*inst, gch) == (True, g)
            if g > opt:
                worse += 1
                excess.append(g - opt)
                rel.append((g - opt) / max(1, opt))
        mean_ex = sum(excess) / len(excess) if excess else 0
        mean_rel = sum(rel) / len(rel) if rel else 0
        rows.append([d, trials, worse, f"{100 * worse / trials:.1f}", f"{mean_ex:.2f}",
                     max(excess) if excess else 0, f"{100 * mean_rel:.1f}"])
        print(f"d={d}: greedy suboptimal on {worse}/{trials} ({100 * worse / trials:.1f}%), "
              f"{mean_ex:.2f} extra cacti on average when wrong", flush=True)
    write_csv("greedy_quick.csv" if quick else "greedy.csv",
              ["density", "trials", "greedy_suboptimal", "pct_suboptimal",
               "mean_excess_when_wrong", "max_excess", "mean_rel_excess_pct"], rows)


# split the time into preprocessing (sort, ranks, reductions) and the DP itself.
def exp_phases(quick=False):
    plan = ([(2000, ["quadratic", "segtree", "linear"]), (64000, ["segtree", "linear"])] if quick
            else [(8000, ["quadratic", "segtree", "linear"]), (512000, ["segtree", "linear"])])
    dps = {"quadratic": dp_quadratic, "segtree": dp_segtree, "linear": dp_linear}
    rows = []
    for s, algos in plan:
        for seed in range(3):
            # equal radii: all three DPs apply
            inst = instance(s, radii="equal", seed=seed)
            t0 = time.perf_counter()
            Os, Cs, ivs = build_intervals(*inst)
            check_feasible(len(Os), ivs)
            ivs = reduce_r2(reduce_intervals(ivs))
            t_pre = time.perf_counter() - t0
            for a in algos:
                t1 = time.perf_counter()
                dps[a](Os, Cs, ivs)
                t_dp = time.perf_counter() - t1
                rows.append([s, seed, a, f"{t_pre:.4f}", f"{t_dp:.4f}"])
                print(f"s={s:<7d} seed={seed} {a:9s} preprocessing {t_pre:.3f} s   DP {t_dp:.3f} s",
                      flush=True)
    write_csv("phases_quick.csv" if quick else "phases.csv",
              ["s", "seed", "dp", "preprocess_sec", "dp_sec"], rows)


# runs in a fresh process, prints peak memory (KB) before and after solving.
def _mem_child(algo, s, radii):
    import resource
    inst = instance(s, radii=radii, seed=0)
    base = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    run(algo, inst, limit=60)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(base, peak)


def exp_memory(quick=False):
    plan = ([("baseline", 30, "varied"), ("quadratic", 2000, "varied"),
             ("segtree", 64000, "varied"), ("linear", 64000, "equal")] if quick else
            [("baseline", 40, "varied"), ("quadratic", 16000, "varied"),
             ("segtree", 1024000, "varied"), ("linear", 1024000, "equal")])
    rows = []
    for algo, s, radii in plan:
        out = subprocess.run([sys.executable, __file__, "_mem", algo, str(s), radii],
                             capture_output=True, text=True).stdout.split()
        base, peak = int(out[0]) / 1024, int(out[1]) / 1024
        rows.append([algo, radii, s, f"{base:.1f}", f"{peak:.1f}"])
        print(f"{algo:9s} s={s:<8d} peak memory {peak:.0f} MB (instance alone: {base:.0f} MB)",
              flush=True)
    write_csv("memory_quick.csv" if quick else "memory.csv",
              ["algo", "radii", "s", "rss_after_generation_MB", "peak_rss_MB"], rows)


if __name__ == "__main__":
    # used by exp_memory
    if len(sys.argv) > 1 and sys.argv[1] == "_mem":
        _mem_child(sys.argv[2], int(sys.argv[3]), sys.argv[4])
        sys.exit(0)
    jobs = {"scaling": exp_scaling,
            "density": exp_density,
            "density_baseline": exp_density_baseline,
            "reductions": exp_reductions,
            "greedy": exp_greedy,
            "phases": exp_phases,
            "memory": exp_memory}
    what = sys.argv[1] if len(sys.argv) > 1 else "scaling"
    if what not in jobs:
        print("choose one of:", ", ".join(jobs))
        sys.exit(1)
    jobs[what](quick="--quick" in sys.argv)
