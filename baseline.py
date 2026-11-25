import sys
import time
from common import read_instance, build_intervals, check_feasible, format_solution, InfeasibleError

# raised when the search runs longer than the time limit
class SearchLimit(Exception):
    pass


def solve_baseline(O, C, S, R, time_limit=None, stats=None):
    Os, Cs, ivs = build_intervals(O, C, S, R)
    o = len(Os)
    if o == 0:
        return [], 0
    check_feasible(o, ivs)

    covering = [[] for _ in range(o)]          
    for k, iv in enumerate(ivs):
        for t in range(iv[3], iv[4]):
            covering[t].append(k)
    for lst in covering:
        lst.sort(key=lambda k: -ivs[k][1])     

    # all the useful sprinklers (feasible by check_feasible)
    wet_all = set()
    for iv in ivs:
        wet_all.update(range(iv[5], iv[6]))
    best_cost = len(wet_all)
    best_set = [iv[2] for iv in ivs]

    hits = [0] * len(Cs)                        
    chosen = []
    nodes = 0
    start = time.perf_counter()
    sys.setrecursionlimit(max(10000, 4 * o + 100))

    def dfs(p, cost):
        # invariant: trees 0..p-1 watered, tree p dry, cost < best_cost
        nonlocal best_cost, best_set, nodes
        nodes += 1
        # checked every 1024 nodes
        if time_limit is not None and (nodes & 1023) == 0 \
                and time.perf_counter() - start > time_limit:
            raise SearchLimit()
        for k in covering[p]:
            l, r, idx, oa, ob, ca, cb = ivs[k]
            added = 0
            # water this sprinkler's cacti
            for t in range(ca, cb):              
                if hits[t] == 0:
                    added += 1
                hits[t] += 1
            # bound
            if cost + added < best_cost:         
                chosen.append(idx)
                if ob == o:                      
                    # every tree watered: new best
                    best_cost, best_set = cost + added, chosen[:]
                else:
                    # next dry tree is index ob
                    dfs(ob, cost + added)        

                chosen.pop()
            # undo
            for t in range(ca, cb):              
                hits[t] -= 1

    try:
        dfs(0, 0)
    finally:
        if stats is not None:
            stats["nodes"] = nodes              # recorded even if we stopped early
    return best_set, best_cost


def main():
    if len(sys.argv) < 2:
        print("usage: python3 baseline.py instance.txt [--limit SECONDS]")
        sys.exit(1)
    O, C, S, R = read_instance(sys.argv[1])
    limit = float(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    st = {}
    t0 = time.perf_counter()
    try:
        chosen, cost = solve_baseline(O, C, S, R, time_limit=limit, stats=st)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    except SearchLimit:
        print(f"stopped after {limit} s ({st.get('nodes')} search nodes): optimum not proven")
        sys.exit(3)
    dt = time.perf_counter() - t0
    print(format_solution(O, C, S, R, chosen, cost, "baseline: branch-and-bound search"))
    if "--stats" in sys.argv:
        print(f"search nodes: {st['nodes']}   time: {dt:.4f} s")


if __name__ == "__main__":
    main()