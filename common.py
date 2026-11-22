import sys
from bisect import bisect_right


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
        toks.extend(line.split("#", 1)[0].split())     # drop comments
    o, c, s = int(toks[0]), int(toks[1]), int(toks[2])
    nums = [_num(t) for t in toks[3:]]
    if len(nums) != o + c + 2 * s:
        raise ValueError(f"expected {o + c + 2 * s} numbers, got {len(nums)}")
    O = nums[:o]
    C = nums[o:o + c]
    S = nums[o + c:o + c + s]
    R = nums[o + c + s:]
    return O, C, S, R


#Return ( true or false based on if all trees are watered, the exact number of watered cacti) for an set of sprinkler indices
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