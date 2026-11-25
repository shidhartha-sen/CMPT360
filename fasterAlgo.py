import sys
import time
from common import read_instance, build_intervals, check_feasible, evaluate, InfeasibleError

INF = float("inf")
L_, R_, IDX, OA, OB, CA, CB = range(7)        # positions 

#remove exact duplicate intervals. Returns intervals sorted by (l, r).
def reduce_intervals(ivs):
    ivs = sorted(ivs, key=lambda v: (v[L_], v[R_], v[IDX]))
    dedup = []
    for v in ivs:
        if dedup and dedup[-1][L_] == v[L_] and dedup[-1][R_] == v[R_]:
            continue                      # same interval as the previous one
        dedup.append(v)
    return dedup

# among intervals that water exactly the same trees, drop any interval that contains another one.
def reduce_r2(ivs):
    groups = {}
    for v in ivs:
        groups.setdefault((v[OA], v[OB]), []).append(v)    
    keep = []
    for g in groups.values():
        g.sort(key=lambda v: (-v[L_], v[R_]))              
        min_r = INF                                        
        for v in g:                                        
            if v[R_] < min_r:                              
                keep.append(v)
                min_r = v[R_]
    keep.sort(key=lambda v: (v[L_], v[R_]))
    return keep


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


"""Minimum over positions 0..n-1 with point updates, O(log n) each.
array layout like a binary heap tree: node k has children 2k and and then 2k+1,
leaves start at index size."""
class MinTree:

    def __init__(self, n, sentinel):
        size = 1
        while size < max(1, n):
            size *= 2
        self.size = size
        # t[0] is never written, it stays the sentinel
        self.t = [sentinel] * (2 * size)     

    def update(self, pos, key):
        #Set position pos to keythen later fix the minimums on the way up
        t = self.t
        pos += self.size
        t[pos] = key
        pos >>= 1
        while pos:
            a, b = t[2 * pos], t[2 * pos + 1]
            t[pos] = a if a < b else b
            pos >>= 1

    def query(self, lo, hi):
        #Minimum over positions lo to hi minus 1 or whatever happens to be the sentinel if the range is empty
        t = self.t
        res = t[0]
        lo += self.size
        hi += self.size
        while lo < hi:
            # lo is a right child: take it, step right
            if lo & 1:                       
                if t[lo] < res:
                    res = t[lo]
                lo += 1
            # node just left of hi is inside: take it
            if hi & 1:                       
                hi -= 1
                if t[hi] < res:
                    res = t[hi]
            lo >>= 1
            hi >>= 1
        return res

METHODS = {"quadratic": dp_quadratic}       # more will be added in later steps


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
    ivs = reduce_intervals(ivs)                 
    if stats is not None:
        stats["s_after_dup"] = len(ivs)
    ivs = reduce_r2(ivs)                        
    if stats is not None:
        stats["s_after_r2"] = len(ivs)
    dp, par = dp_quadratic(Os, Cs, ivs)         
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from: {', '.join(METHODS)}")
    if stats is not None:
        stats["method"] = method
    dp, par = METHODS[method](Os, Cs, ivs)
    return _finish(o, ivs, dp, par)             

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    O, C, S, R = read_instance(sys.argv[1])
    method = sys.argv[sys.argv.index("--method") + 1] if "--method" in sys.argv else "quadratic"
    st = {}
    t0 = time.perf_counter()
    try:
        chosen, cost = solve(O, C, S, R, method=method, stats=st)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    dt = time.perf_counter() - t0
    ok, wet = evaluate(O, C, S, R, chosen)
    print("chosen sprinklers (1-based):", sorted(i + 1 for i in chosen))
    print("cacti watered:", cost, "| checker agrees:", ok and wet == cost)
    if "--stats" in sys.argv:
        print(f"method: {st.get('method')}   time: {dt:.4f} s")
        print(f"sprinklers: input {st.get('s_input')}, after R1 {st.get('s_after_r1')}, "
              f"after duplicates {st.get('s_after_dup')}, after R2 {st.get('s_after_r2')}")

if __name__ == "__main__":
    main()