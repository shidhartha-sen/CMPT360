import sys

def bisect_left(a, x):
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def bisect_right(a, x):
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def _num(tok):
    try:
        return int(tok)
    except ValueError:
        return float(tok)


#read 'o c s' then O, C, S, R. 
def read_instance(path):
    text = open(path).read()
    toks = []
    for line in text.splitlines():
        toks.extend(line.split("#", 1)[0].split())     
    o, c, s = int(toks[0]), int(toks[1]), int(toks[2])
    nums = [_num(t) for t in toks[3:]]
    if len(nums) != o + c + 2 * s:
        raise ValueError(f"expected {o + c + 2 * s} numbers, got {len(nums)}")
    O = nums[:o]
    C = nums[o:o + c]
    S = nums[o + c:o + c + s]
    R = nums[o + c + s:]
    return O, C, S, R


#return ( true or false based on if all trees are watered, the exact number of watered cacti) for an set of sprinkler indices
def evaluate(O, C, S, R, chosen):
    segs = sorted((S[i] - R[i], S[i] + R[i]) for i in set(chosen))
    merged = []                                  
    for l, r in segs:
        if merged and l <= merged[-1][1]:        
            merged[-1][1] = max(merged[-1][1], r)
        else:
            merged.append([l, r])
    lefts = [m[0] for m in merged]

    def inside(x):
        k = bisect_right(lefts, x) - 1           
        return k >= 0 and x <= merged[k][1]

    ok = all(inside(x) for x in O)
    wet = sum(1 for x in C if inside(x))
    return ok, wet


class InfeasibleError(Exception):
    """Raised when some orange tree is not watered by any sprinkler"""


#sort O and C:  describe each sprinkler as (l, r, idx, oa, ob, ca, cb): it waters trees [oa, ob) and cacti [ca, cb) in sorted order.
def build_intervals(O, C, S, R):
    Os = sorted(O)
    Cs = sorted(C)
    ivs = []
    for idx in range(len(S)):
        l = S[idx] - R[idx]
        r = S[idx] + R[idx]
        oa = bisect_left(Os, l)
        ob = bisect_right(Os, r)
        # waters no tree: never useful
        if oa == ob:                 
            continue
        ca = bisect_left(Cs, l)
        cb = bisect_right(Cs, r)
        ivs.append((l, r, idx, oa, ob, ca, cb))
    return Os, Cs, ivs


#every tree must be inside some interval.
def check_feasible(o, ivs):
    diff = [0] * (o + 1)
    for (_, _, _, oa, ob, _, _) in ivs:
        diff[oa] += 1
        diff[ob] -= 1
    run = 0
    for t in range(o):
        run += diff[t]
        if run == 0:
            raise InfeasibleError(f"orange tree #{t} (sorted order) is not watered by any sprinkler")
            d

# readable summary of a solution, long lists are shortened and re-checked with evaluate().
def format_solution(O, C, S, R, chosen, cost, label, show=20):
    # left to right along the line
    chosen = sorted(chosen, key=lambda i: (S[i], i))
    ok, wet = evaluate(O, C, S, R, chosen)
    ids = [str(i + 1) for i in chosen]
    pos = [str(S[i]) for i in chosen]
    more = ""
    if len(chosen) > show:
        more = f" ... (+{len(chosen) - show} more)"
        ids, pos = ids[:show], pos[:show]
    lines = [f"[{label}]",
             f"Sprinklers chosen: {len(chosen)} of {len(S)}",
             f"Indices (1-based): {' '.join(ids) or '(none)'}{more}",
             f"Positions:         {' '.join(pos) or '(none)'}{more}",
             f"All orange trees watered: {'yes' if ok else 'NO'}",
             f"Cacti watered: {cost}   (independent check: {'OK' if ok and wet == cost else 'MISMATCH'})"]
    return "\n".join(lines)
