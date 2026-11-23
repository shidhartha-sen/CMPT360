import sys
from common import read_instance, build_intervals, check_feasible, evaluate, InfeasibleError

INF = float("inf")
L_, R_, IDX, OA, OB, CA, CB = range(7)        # positions in an interval record


#ivs sorted by (l, r). dp[j] = best chain ending with j that waters every tree <= r_j.
def dp_quadratic(Os, Cs, ivs):
    n = len(ivs)
    dp = [INF] * n
    par = [-1] * n
    for j in range(n):
        lj, rj, _, oaj, obj, caj, cbj = ivs[j]
        best, bp = (cbj - caj, -1) if oaj == 0 else (INF, -1)    
        for i in range(j):                                     
            di = dp[i]
            if di == INF:
                continue
            ri = ivs[i][R_]
            if ri >= rj:                                       
                continue
            if ri >= lj:                                       
                cand = di + cbj - ivs[i][CB]
            elif ivs[i][OB] == oaj:                            
                cand = di + cbj - caj
            else:
                continue
            if cand < best:
                best, bp = cand, i
        dp[j], par[j] = best, bp
    return dp, par


#Best chain that reaches past the last tree; follow parent pointers back.

def _finish(o, ivs, dp, par):
    best, last = INF, -1
    for j, v in enumerate(ivs):
        if v[OB] == o and dp[j] < best:
            best, last = dp[j], j
    if last < 0:
        raise InfeasibleError("no cover found")
    chosen = []
    while last >= 0:
        chosen.append(ivs[last][IDX])
        last = par[last]
    return chosen[::-1], best


def solve(O, C, S, R, method="quadratic", stats=None):
    Os, Cs, ivs = build_intervals(O, C, S, R)
    o = len(Os)
    if o == 0:
        return [], 0
    check_feasible(o, ivs)
    if stats is not None:
        stats.update(s_input=len(S), s_after_r1=len(ivs)) 
    ivs.sort(key=lambda v: (v[L_], v[R_]))
    dp, par = dp_quadratic(Os, Cs, ivs)
    return _finish(o, ivs, dp, par)


def main():
    O, C, S, R = read_instance(sys.argv[1])
    st = {}
    try:
        chosen, cost = solve(O, C, S, R, stats=st)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    ok, wet = evaluate(O, C, S, R, chosen)
    print("Chosen sprinklers (1-based):", sorted(i + 1 for i in chosen))
    print("Cacti watered:", cost, "| checker agrees:", ok and wet == cost)
    if "--stats" in sys.argv:
        print(f"Sprinklers: input {st.get('s_input')}, after R1 {st.get('s_after_r1')}")


if __name__ == "__main__":
    main()