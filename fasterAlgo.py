import sys
import time
from common import read_instance, build_intervals, check_feasible, format_solution, InfeasibleError, bisect_left

INF = float("inf")
L_, R_, IDX, OA, OB, CA, CB = range(7)        # positions

# raised when linear is asked for but some range is nested in another
class NotProperError(ValueError):
    pass

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

# true if no interval is nested in another, enough to check neighbours.
def is_proper(ivs):
    for a, b in zip(ivs, ivs[1:]):
        if not (a[L_] < b[L_] and a[R_] < b[R_]):
            return False
    return True

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
array layout like a binary heap tree for node k has children 2k and and then 2k+1,
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
        #set position pos to keythen later fix the minimums on the way up
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

# same recurrence as dp_quadratic, sprinklers processed in (l, r) order.
def dp_segtree(Os, Cs, ivs):
    n = len(ivs)
    c = len(Cs)
    dp = [INF] * n
    par = [-1] * n
    order_r = sorted(range(n), key=lambda k: ivs[k][R_])   # sprinklers sorted by r
    rs = [ivs[k][R_] for k in order_r]                      # their right ends, sorted
    rank = [0] * n                                          # rank[k] = tree position of k
    for pos, k in enumerate(order_r):
        rank[k] = pos
    M = n + 1                       # key = (value + OFF) * M + index
    OFF = c + 1                     # makes value + OFF >= 1
    SENT = (2 * c + 3) * M          # bigger than any real key
    tree = MinTree(n, SENT)
    gap = []                        # monotone queue: r increasing, dp increasing
    head = 0                        # gap[head:] is the live part
    ent = 0                         # next position in order_r to enter the queue
    for j in range(n):
        l, r, _, oa, ob, ca, cb = ivs[j]
        best, bp = (cb - ca, -1) if oa == 0 else (INF, -1)      # start
        if oa > 0:                                               # gap steps
            while ent < n and rs[ent] < l:                       # these now end left of l_j
                k = order_r[ent]
                ent += 1
                dk = dp[k]
                if dk < INF:
                    while len(gap) > head and dp[gap[-1]] >= dk: # worse and leaves sooner
                        gap.pop()
                    gap.append(k)
            a = Os[oa - 1]                                       # last tree left of l_j
            while head < len(gap) and ivs[gap[head]][R_] < a:    # would leave tree a dry
                head += 1
            if head < len(gap):                                  # front = smallest dp
                i = gap[head]
                best, bp = dp[i] + cb - ca, i
        lo = bisect_left(rs, l)                                  # overlap: l <= r_i < r
        hi = bisect_left(rs, r)
        if lo < hi:
            key = tree.query(lo, hi)
            if key < SENT:
                i = key % M                                      # unpack index
                cand = key // M - OFF + cb                       # unpack value, add cb_j
                if cand < best:
                    best, bp = cand, i
        dp[j], par[j] = best, bp
        if best < INF:                                           # now j can be a predecessor
            tree.update(rank[j], (best - cb + OFF) * M + j)
    return dp, par

# proper family only, order by l = order by r, so overlap and gap blocks both slide right.
def dp_linear(Os, Cs, ivs):
    n = len(ivs)
    dp = [INF] * n
    par = [-1] * n
    ov, ov_head = [], 0             # overlap queue: dp[i] - cb_i increasing
    gp, gp_head = [], 0             # gap queue: dp[i] increasing
    left = 0                        # indices < left end before l_j
    for j in range(n):
        l, r, _, oa, ob, ca, cb = ivs[j]
        if j > 0 and dp[j - 1] < INF:                            # j-1 joins the overlap block
            v = dp[j - 1] - ivs[j - 1][CB]
            while len(ov) > ov_head and dp[ov[-1]] - ivs[ov[-1]][CB] >= v:
                ov.pop()
            ov.append(j - 1)
        while left < j and ivs[left][R_] < l:                    # ends before l_j: overlap -> gap
            if dp[left] < INF:
                while len(gp) > gp_head and dp[gp[-1]] >= dp[left]:
                    gp.pop()
                gp.append(left)
            left += 1
        while ov_head < len(ov) and ov[ov_head] < left:          # no longer reaches l_j
            ov_head += 1
        if oa == 0:
            best, bp = cb - ca, -1                               # start
        else:
            best, bp = INF, -1
            a = Os[oa - 1]                                       # last tree left of l_j
            while gp_head < len(gp) and ivs[gp[gp_head]][R_] < a:
                gp_head += 1                                     # would leave tree a dry
            if gp_head < len(gp):
                i = gp[gp_head]
                best, bp = dp[i] + cb - ca, i
        if ov_head < len(ov):                                    # overlap
            i = ov[ov_head]
            cand = dp[i] - ivs[i][CB] + cb
            if cand < best:
                best, bp = cand, i
        dp[j], par[j] = best, bp
    return dp, par

METHODS = {"quadratic": dp_quadratic, "segtree": dp_segtree, "linear": dp_linear}


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


# auto (default): linear if the reduced family is proper, else segtree.
def solve(O, C, S, R, method="auto", stats=None):
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
    proper = is_proper(ivs)
    if stats is not None:
        stats["s_after_r2"] = len(ivs)
        stats["proper"] = proper
    if method == "auto":
        method = "linear" if proper else "segtree"
    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from: auto, {', '.join(METHODS)}")
    if method == "linear" and not proper:
        raise NotProperError("method 'linear' needs a proper family (no nested ranges)")
    if stats is not None:
        stats["method"] = method
    dp, par = METHODS[method](Os, Cs, ivs)
    return _finish(o, ivs, dp, par)             

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    O, C, S, R = read_instance(sys.argv[1])
    method = sys.argv[sys.argv.index("--method") + 1] if "--method" in sys.argv else "auto"
    st = {}
    t0 = time.perf_counter()
    try:
        chosen, cost = solve(O, C, S, R, method=method, stats=st)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    except NotProperError as e:
        print("Error:", e)
        sys.exit(2)
    dt = time.perf_counter() - t0
    print(format_solution(O, C, S, R, chosen, cost, f"fasterAlgo: {st.get('method', method)} DP"))
    if "--stats" in sys.argv:
        print(f"time: {dt:.4f} s")
        print(f"sprinklers: input {st.get('s_input')}, after R1 {st.get('s_after_r1')}, "
              f"after duplicates {st.get('s_after_dup')}, after R2 {st.get('s_after_r2')}")
        print(f"proper family (no nested ranges): {st.get('proper')}")

if __name__ == "__main__":
    main()