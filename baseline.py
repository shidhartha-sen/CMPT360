import sys
from common import read_instance, build_intervals, check_feasible, evaluate, InfeasibleError


def solve_baseline(O, C, S, R, stats=None):
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
    sys.setrecursionlimit(max(10000, 4 * o + 100))

    def dfs(p, cost):
        # invariant: trees 0..p-1 watered, tree p dry, cost < best_cost
        nonlocal best_cost, best_set, nodes
        nodes += 1
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

    dfs(0, 0)
    if stats is not None:
        stats["nodes"] = nodes
    return best_set, best_cost


def main():
    O, C, S, R = read_instance(sys.argv[1])
    st = {}
    try:
        chosen, cost = solve_baseline(O, C, S, R, stats=st)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    ok, wet = evaluate(O, C, S, R, chosen)       # independent check
    print("chosen sprinklers (1-based):", sorted(i + 1 for i in chosen))
    print("cacti watered:", cost, "| checker agrees:", ok and wet == cost)
    print("search nodes:", st["nodes"])


if __name__ == "__main__":
    main()