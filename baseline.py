import sys
import time
from common import read_instance, build_intervals, check_feasible, format_solution, InfeasibleError


# raised when the search runs longer than the time limit
class SearchLimit(Exception):
    pass


# Exact branch-and-bound search: branches on the sprinklers that reach
# the leftmost dry tree, and cuts any branch that can't beat the best so far
#
# parameters:
#   O, C, S, R: tree positions, cactus positions, sprinkler positions, radii
#   time_limit: optional, seconds before giving up with SearchLimit
#   stats: optional dict, filled with the number of search nodes
#
# returns: (chosen sprinkler indices, cacti watered)
# raises: InfeasibleError if some tree cant be watered, SearchLimit on timeout
def solve_baseline(O, C, S, R, time_limit=None, stats=None):
    trees, cacti, intervals = build_intervals(O, C, S, R)
    num_trees = len(trees)
    if num_trees == 0:
        return [], 0

    check_feasible(num_trees, intervals)

    # covering[t] = the sprinklers that water tree t, farthest reaching first
    covering = []
    for t in range(num_trees):
        covering.append([])
    for k in range(len(intervals)):
        first_tree = intervals[k][3]
        end_tree = intervals[k][4]
        for t in range(first_tree, end_tree):
            covering[t].append(k)
    for sprinklers in covering:
        sprinklers.sort(key=lambda k: -intervals[k][1])

    # starting best: use every useful sprinkler (feasible by check_feasible)
    all_wet_cacti = set()
    for iv in intervals:
        first_cactus = iv[5]
        end_cactus = iv[6]
        for t in range(first_cactus, end_cactus):
            all_wet_cacti.add(t)
    best_cost = len(all_wet_cacti)
    best_set = []
    for iv in intervals:
        best_set.append(iv[2])

    # hits[t] = number of chosen sprinklers watering cactus t
    hits = [0] * len(cacti)
    chosen = []
    nodes = 0
    start = time.perf_counter()
    sys.setrecursionlimit(max(10000, 4 * num_trees + 100))

    # trees 0..dry_tree-1 are watered, tree dry_tree is dry, cost < best_cost
    def search(dry_tree, cost):
        nonlocal best_cost, best_set, nodes
        nodes += 1

        # only check the clock every 1024 nodes
        if time_limit is not None and nodes % 1024 == 0:
            if time.perf_counter() - start > time_limit:
                raise SearchLimit()

        for k in covering[dry_tree]:
            left, right, index, first_tree, end_tree, first_cactus, end_cactus = intervals[k]

            # water this sprinkler's cacti, counting the new ones
            added = 0
            for t in range(first_cactus, end_cactus):
                if hits[t] == 0:
                    added += 1
                hits[t] += 1

            # bound: only go deeper if this can still beat the best
            if cost + added < best_cost:
                chosen.append(index)

                if end_tree == num_trees:
                    # every tree watered, new best
                    best_cost = cost + added
                    best_set = chosen[:]
                else:
                    # next dry tree is end_tree
                    search(end_tree, cost + added)

                chosen.pop()

            # undo
            for t in range(first_cactus, end_cactus):
                hits[t] -= 1

    try:
        search(0, 0)
    finally:
        # recorded even if we stopped early
        if stats is not None:
            stats["nodes"] = nodes

    return best_set, best_cost


def main():
    if len(sys.argv) < 2:
        print("usage: python3 baseline.py instance.txt [--limit SECONDS] [--stats]")
        sys.exit(1)

    O, C, S, R = read_instance(sys.argv[1])

    limit = None
    if "--limit" in sys.argv:
        limit = float(sys.argv[sys.argv.index("--limit") + 1])

    stats = {}
    start = time.perf_counter()
    try:
        chosen, cost = solve_baseline(O, C, S, R, time_limit=limit, stats=stats)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    except SearchLimit:
        print(f"stopped after {limit} s ({stats.get('nodes')} search nodes): optimum not proven")
        sys.exit(3)
    elapsed = time.perf_counter() - start

    print(format_solution(O, C, S, R, chosen, cost, "baseline: branch-and-bound search"))

    if "--stats" in sys.argv:
        print(f"search nodes: {stats['nodes']}   time: {elapsed:.4f} s")


if __name__ == "__main__":
    main()
