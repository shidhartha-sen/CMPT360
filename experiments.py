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


# Makes a random instance with the given coverage density
#
# parameters:
#   s: number of sprinklers
#   d: coverage density, how many sprinklers reach a point on average
#   radii: "equal" (all 10) or "varied" (uniform in [1, 20])
#   seed: random seed
#   o, c: number of trees and cacti, both default to s
#
# returns: (O, C, S, R)
def instance(s, d=4.0, radii="varied", seed=1, o=None, c=None):
    if radii == "equal":
        rmin = 10
        rmax = 10
    else:
        rmin = 1
        rmax = 20

    if o is None:
        o = s
    if c is None:
        c = s

    # 2 * average radius + 1
    average_length = rmin + rmax + 1
    # line length that gives density d
    line_length = max(1, round(s * average_length / d))

    return generate(s, o, c, line_length, rmin, rmax, seed)


# Times one algorithm on one instance
#
# parameters:
#   algo: "baseline", or a method for solve()
#   inst: the instance (O, C, S, R)
#   limit: time limit for the baseline, in seconds
#
# returns: (seconds, stats), or (None, stats) if the baseline timed out
def run(algo, inst, limit=LIMIT):
    stats = {}
    start = time.perf_counter()
    try:
        if algo == "baseline":
            solve_baseline(*inst, time_limit=limit, stats=stats)
        else:
            solve(*inst, method=algo, stats=stats)
    except SearchLimit:
        return None, stats

    return time.perf_counter() - start, stats


# Median where a timed-out run counts as slower than every finished run
#
# parameters:
#   times: the times of the finished runs
#   timeouts: how many runs timed out
#
# returns: the median, or None if the median run itself timed out
def median_with_timeouts(times, timeouts):
    values = sorted(times) + [float("inf")] * timeouts
    if len(values) == 0:
        return None

    n = len(values)
    if n % 2 == 1:
        median = values[n // 2]
    else:
        median = (values[n // 2 - 1] + values[n // 2]) / 2

    if median == float("inf"):
        return None
    return median


# formats a median for the csv, empty if there is none
def fmt(median):
    if median is None:
        return ""
    return f"{median:.6f}"


# Writes a csv file into results/ by hand
#
# parameters:
#   name: the file name
#   header: list of column names
#   rows: list of rows, each a list of values
def write_csv(name, header, rows):
    path = os.path.join("results", name)
    with open(path, "w") as f:
        f.write(",".join(header) + "\n")
        for row in rows:
            values = []
            for value in row:
                values.append(str(value))
            f.write(",".join(values) + "\n")

    print(f"wrote {path} ({len(rows)} rows)")


# Times each algorithm at growing sizes, stops growing one once its median goes over the limit
#
# parameters:
#   quick: tiny sizes, just to test the script
def exp_scaling(quick=False):
    # each plan is (algorithm, radii, sizes, seeds per size)
    if quick:
        plans = [("baseline", "varied", [10, 20, 30], 3),
                 ("quadratic", "varied", [250, 500, 1000], 3),
                 ("segtree", "varied", [1000, 2000, 4000], 3),
                 ("segtree", "equal", [1000, 2000, 4000], 3),
                 ("linear", "equal", [1000, 2000, 4000], 3)]
    else:
        # the real run (step 19)
        baseline_sizes = list(range(10, 71, 4))
        quadratic_sizes = []
        for k in range(10):
            quadratic_sizes.append(250 * 2 ** k)
        fast_sizes = []
        for k in range(12):
            fast_sizes.append(1000 * 2 ** k)

        plans = [("baseline", "varied", baseline_sizes, 5),
                 ("baseline", "equal", baseline_sizes, 5),
                 ("quadratic", "varied", quadratic_sizes, 3),
                 ("segtree", "varied", fast_sizes, 3),
                 ("segtree", "equal", fast_sizes, 3),
                 ("linear", "equal", fast_sizes, 3)]

    rows = []
    for algo, radii, sizes, seeds in plans:
        for s in sizes:
            times = []
            nodes = []
            timeouts = 0

            for seed in range(seeds):
                seconds, stats = run(algo, instance(s, radii=radii, seed=seed))
                if seconds is None:
                    timeouts += 1
                else:
                    times.append(seconds)
                    nodes.append(stats.get("nodes", 0))

            median = median_with_timeouts(times, timeouts)

            median_nodes = ""
            if len(nodes) > 0:
                median_nodes = sorted(nodes)[len(nodes) // 2]

            rows.append([algo, radii, s, 3 * s, fmt(median), timeouts, seeds, median_nodes])

            shown = "> limit"
            if median is not None:
                shown = f"{median:.4f} s"
            print(f"{algo:9s} {radii:6s} s={s:<8d} median={shown:12s} timeouts={timeouts}/{seeds}",
                  flush=True)

            # too slow now, stop growing this one
            if median is None or median > LIMIT:
                break

    name = "scaling.csv"
    if quick:
        name = "scaling_quick.csv"
    write_csv(name, ["algo", "radii", "s", "N", "median_sec", "timeouts", "runs", "median_nodes"], rows)


# Times the three DPs at a fixed size while the coverage density d changes
#
# parameters:
#   quick: smaller sizes, just to test the script
def exp_density(quick=False):
    if quick:
        sizes = {"quadratic": 1000, "segtree": 20000, "linear": 20000}
    else:
        sizes = {"quadratic": 4000, "segtree": 200000, "linear": 200000}

    rows = []
    for d in [1, 2, 3, 4, 6, 8, 12]:
        for algo in ["quadratic", "segtree", "linear"]:
            # linear only works on a proper family
            radii = "varied"
            if algo == "linear":
                radii = "equal"
            s = sizes[algo]

            times = []
            for seed in range(3):
                seconds, _ = run(algo, instance(s, d=d, radii=radii, seed=seed))
                times.append(seconds)

            median = median_with_timeouts(times, 0)
            rows.append([algo, radii, s, d, fmt(median)])
            print(f"d={d:<3d} {algo:9s} s={s:<7d} median={median:.4f} s", flush=True)

    name = "density.csv"
    if quick:
        name = "density_quick.csv"
    write_csv(name, ["algo", "radii", "s", "density", "median_sec"], rows)


# Times the baseline at a fixed size while d changes,
# with more seeds since its times vary a lot
#
# parameters:
#   quick: smaller size and fewer seeds, just to test the script
def exp_density_baseline(quick=False):
    if quick:
        s = 25
        seeds = 5
    else:
        s = 40
        seeds = 11

    rows = []
    for d in [1, 2, 3, 4, 6, 8, 12, 16]:
        times = []
        nodes = []
        timeouts = 0

        for seed in range(seeds):
            seconds, stats = run("baseline", instance(s, d=d, radii="varied", seed=100 + seed))
            if seconds is None:
                timeouts += 1
            else:
                times.append(seconds)
                nodes.append(stats["nodes"])

        median = median_with_timeouts(times, timeouts)

        median_nodes = ""
        if len(nodes) > 0:
            median_nodes = sorted(nodes)[len(nodes) // 2]

        rows.append([s, d, fmt(median), timeouts, seeds, median_nodes])

        shown = "> limit"
        if median is not None:
            shown = f"{median:.4f} s"
        print(f"d={d:<3d} baseline s={s} median={shown:12s} timeouts={timeouts}/{seeds}", flush=True)

    name = "density_baseline.csv"
    if quick:
        name = "density_baseline_quick.csv"
    write_csv(name, ["s", "density", "median_sec", "timeouts", "runs", "median_nodes_finished"], rows)


# Counts how many sprinklers R1, duplicates and R2 remove, for sparse vs dense trees
#
# parameters:
#   quick: smaller size, just to test the script
def exp_reductions(quick=False):
    s = 100000
    if quick:
        s = 10000

    rows = []
    # orange trees per sprinkler
    for ratio in [0.01, 0.1, 0.5, 1.0, 2.0]:
        for d in [1, 4, 16]:
            o = max(1, int(ratio * s))
            stats = {}

            start = time.perf_counter()
            solve(*instance(s, d=d, radii="varied", seed=3, o=o), stats=stats)
            seconds = time.perf_counter() - start

            after_r1 = stats["s_after_r1"]
            after_dup = stats["s_after_dup"]
            after_r2 = stats["s_after_r2"]
            kept = after_r2 / s

            rows.append([s, o, ratio, d, after_r1, after_dup, after_r2, f"{kept:.3f}", f"{seconds:.4f}"])
            print(f"o/s={ratio:<5} d={d:<3d} after R1 {after_r1:>7}  after dup "
                  f"{after_dup:>7}  after R2 {after_r2:>7}  kept {100 * kept:.1f}%",
                  flush=True)

    name = "reductions.csv"
    if quick:
        name = "reductions_quick.csv"
    write_csv(name, ["s", "o", "o_over_s", "density", "after_R1", "after_dup", "after_R2",
                     "kept_fraction", "sec"], rows)


# Greedy: at the leftmost dry tree, take the sprinkler reaching it that wets the
# fewest new cacti (ties: the one reaching farthest right), fast but not always optimal
#
# parameters:
#   O, C, S, R: tree positions, cactus positions, sprinkler positions, radii
#
# returns: (chosen sprinkler indices, cacti watered)
def greedy(O, C, S, R):
    trees, cacti, intervals = build_intervals(O, C, S, R)
    wet = [False] * len(cacti)
    chosen = []
    dry_tree = 0
    total = 0

    while dry_tree < len(trees):
        best_key = None
        best_interval = None

        for iv in intervals:
            left, right, index, first_tree, end_tree, first_cactus, end_cactus = iv

            # reaches the dry tree
            if first_tree <= dry_tree < end_tree:
                new_cacti = 0
                for t in range(first_cactus, end_cactus):
                    if not wet[t]:
                        new_cacti += 1

                key = (new_cacti, -right)
                if best_key is None or key < best_key:
                    best_key = key
                    best_interval = iv

        left, right, index, first_tree, end_tree, first_cactus, end_cactus = best_interval
        for t in range(first_cactus, end_cactus):
            if not wet[t]:
                wet[t] = True
                total += 1

        chosen.append(index)
        # next dry tree
        dry_tree = end_tree

    return chosen, total


# Compares greedy with the optimum on many random instances
#
# parameters:
#   quick: fewer trials, just to test the script
def exp_greedy(quick=False):
    trials = 1000
    if quick:
        trials = 100

    rows = []
    for d in [2, 4, 8]:
        worse = 0
        excess = []
        relative = []

        for seed in range(trials):
            inst = instance(60, d=d, radii="varied", seed=seed)
            _, optimum = solve(*inst)
            greedy_chosen, greedy_cost = greedy(*inst)

            # greedy's answer is at least valid
            assert evaluate(*inst, greedy_chosen) == (True, greedy_cost)

            if greedy_cost > optimum:
                worse += 1
                excess.append(greedy_cost - optimum)
                relative.append((greedy_cost - optimum) / max(1, optimum))

        mean_excess = 0
        max_excess = 0
        mean_relative = 0
        if len(excess) > 0:
            mean_excess = sum(excess) / len(excess)
            max_excess = max(excess)
            mean_relative = sum(relative) / len(relative)

        percent_worse = 100 * worse / trials
        rows.append([d, trials, worse, f"{percent_worse:.1f}", f"{mean_excess:.2f}",
                     max_excess, f"{100 * mean_relative:.1f}"])
        print(f"d={d}: greedy suboptimal on {worse}/{trials} ({percent_worse:.1f}%), "
              f"{mean_excess:.2f} extra cacti on average when wrong", flush=True)

    name = "greedy.csv"
    if quick:
        name = "greedy_quick.csv"
    write_csv(name, ["density", "trials", "greedy_suboptimal", "pct_suboptimal",
                     "mean_excess_when_wrong", "max_excess", "mean_rel_excess_pct"], rows)


# Splits the time into preprocessing (sort, ranks, reductions) and the DP itself
#
# parameters:
#   quick: smaller sizes, just to test the script
def exp_phases(quick=False):
    # each plan is (size, DPs to time)
    if quick:
        plan = [(2000, ["quadratic", "segtree", "linear"]), (64000, ["segtree", "linear"])]
    else:
        plan = [(8000, ["quadratic", "segtree", "linear"]), (512000, ["segtree", "linear"])]

    dps = {"quadratic": dp_quadratic, "segtree": dp_segtree, "linear": dp_linear}

    rows = []
    for s, algos in plan:
        for seed in range(3):
            # equal radii, so all three DPs apply
            inst = instance(s, radii="equal", seed=seed)

            start = time.perf_counter()
            trees, cacti, intervals = build_intervals(*inst)
            check_feasible(len(trees), intervals)
            intervals = reduce_intervals(intervals)
            intervals = reduce_r2(intervals)
            preprocess_seconds = time.perf_counter() - start

            for algo in algos:
                start = time.perf_counter()
                dps[algo](trees, cacti, intervals)
                dp_seconds = time.perf_counter() - start

                rows.append([s, seed, algo, f"{preprocess_seconds:.4f}", f"{dp_seconds:.4f}"])
                print(f"s={s:<7d} seed={seed} {algo:9s} preprocessing {preprocess_seconds:.3f} s   "
                      f"DP {dp_seconds:.3f} s", flush=True)

    name = "phases.csv"
    if quick:
        name = "phases_quick.csv"
    write_csv(name, ["s", "seed", "dp", "preprocess_sec", "dp_sec"], rows)


# Runs in a fresh process, prints peak memory (KB) before and after solving
#
# parameters:
#   algo: the algorithm to run
#   s: number of sprinklers
#   radii: "equal" or "varied"
def _mem_child(algo, s, radii):
    import resource
    inst = instance(s, radii=radii, seed=0)
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    run(algo, inst, limit=60)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(before, peak)


# Measures peak memory of each algorithm, each one in its own process
#
# parameters:
#   quick: smaller sizes, just to test the script
def exp_memory(quick=False):
    # each plan is (algorithm, size, radii)
    if quick:
        plan = [("baseline", 30, "varied"), ("quadratic", 2000, "varied"),
                ("segtree", 64000, "varied"), ("linear", 64000, "equal")]
    else:
        plan = [("baseline", 40, "varied"), ("quadratic", 16000, "varied"),
                ("segtree", 1024000, "varied"), ("linear", 1024000, "equal")]

    rows = []
    for algo, s, radii in plan:
        command = [sys.executable, __file__, "_mem", algo, str(s), radii]
        output = subprocess.run(command, capture_output=True, text=True).stdout.split()

        # KB to MB (Linux)
        before_mb = int(output[0]) / 1024
        peak_mb = int(output[1]) / 1024

        rows.append([algo, radii, s, f"{before_mb:.1f}", f"{peak_mb:.1f}"])
        print(f"{algo:9s} s={s:<8d} peak memory {peak_mb:.0f} MB (instance alone: {before_mb:.0f} MB)",
              flush=True)

    name = "memory.csv"
    if quick:
        name = "memory_quick.csv"
    write_csv(name, ["algo", "radii", "s", "rss_after_generation_MB", "peak_rss_MB"], rows)


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

    what = "scaling"
    if len(sys.argv) > 1:
        what = sys.argv[1]

    if what not in jobs:
        print("choose one of:", ", ".join(jobs))
        sys.exit(1)

    jobs[what](quick="--quick" in sys.argv)
