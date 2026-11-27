import sys
import time
from common import read_instance, build_intervals, check_feasible, format_solution, InfeasibleError, bisect_left

INF = float("inf")

# positions inside an interval record
# (left end, right end, sprinkler index, first tree, end tree, first cactus, end cactus)
L_, R_, IDX, OA, OB, CA, CB = range(7)


# raised when linear is asked for but some range is nested in another
class NotProperError(ValueError):
    pass


# Removes intervals that are exact duplicates of another one
#
# parameters:
#   intervals: the sprinkler intervals
#
# returns: the intervals with duplicates removed, sorted by (left, right)
def reduce_intervals(intervals):
    intervals = sorted(intervals, key=lambda iv: (iv[L_], iv[R_], iv[IDX]))
    unique = []

    for iv in intervals:
        if len(unique) > 0:
            last = unique[-1]

            # same interval as the previous one
            if last[L_] == iv[L_] and last[R_] == iv[R_]:
                continue

        unique.append(iv)

    return unique


# R2: among intervals that water exactly the same trees,
# drops any interval that contains another one
#
# parameters:
#   intervals: the sprinkler intervals
#
# returns: the kept intervals, sorted by (left, right)
def reduce_r2(intervals):
    # group the intervals by the trees they water
    groups = {}
    for iv in intervals:
        trees_watered = (iv[OA], iv[OB])
        if trees_watered not in groups:
            groups[trees_watered] = []
        groups[trees_watered].append(iv)

    keep = []
    for group in groups.values():
        # largest left end first, so every earlier interval starts at or after this one
        group.sort(key=lambda iv: (-iv[L_], iv[R_]))

        smallest_right = INF
        for iv in group:
            # it contains no earlier interval, so keep it
            if iv[R_] < smallest_right:
                keep.append(iv)
                smallest_right = iv[R_]

    keep.sort(key=lambda iv: (iv[L_], iv[R_]))
    return keep


# Checks whether no interval is nested in another one,
# it is enough to check neighbours since the list is sorted
#
# parameters:
#   intervals: sorted by (left, right) with no duplicates
#
# returns: True if both ends strictly increase, False otherwise
def is_proper(intervals):
    for i in range(len(intervals) - 1):
        current = intervals[i]
        following = intervals[i + 1]

        if current[L_] >= following[L_] or current[R_] >= following[R_]:
            return False

    return True


# O(s^2) DP: finds the cheapest chain of sprinklers ending at each sprinkler
#
# parameters:
#   trees: sorted orange tree positions
#   cacti: sorted cactus positions
#   intervals: sprinkler intervals sorted by (left, right)
#
# returns: (cost, parent) lists, cost[j] = fewest cacti for a chain ending at
#          sprinkler j that waters every tree up to its right end,
#          parent[j] = the previous sprinkler in that chain or -1
def dp_quadratic(trees, cacti, intervals):
    n = len(intervals)
    cost = [INF] * n
    parent = [-1] * n

    for j in range(n):
        left, right, _, first_tree, end_tree, first_cactus, end_cactus = intervals[j]

        # start a chain if j waters the first tree
        best_cost = INF
        best_parent = -1
        if first_tree == 0:
            best_cost = end_cactus - first_cactus

        for i in range(j):
            if cost[i] == INF:
                continue

            prev_right = intervals[i][R_]

            # chain needs the previous sprinkler to end first
            if prev_right >= right:
                continue

            if prev_right >= left:
                # overlap, only count the new cacti
                new_cost = cost[i] + end_cactus - intervals[i][CB]
            elif intervals[i][OB] == first_tree:
                # gap with no tree inside
                new_cost = cost[i] + end_cactus - first_cactus
            else:
                continue

            if new_cost < best_cost:
                best_cost = new_cost
                best_parent = i

        cost[j] = best_cost
        parent[j] = best_parent

    return cost, parent


# Minimum over positions 0..n-1 with point updates, O(log n) each.
# array layout like a binary heap tree, node k has children 2k and 2k+1,
# leaves start at index size.
class MinTree:

    def __init__(self, n, sentinel):
        size = 1
        while size < max(1, n):
            size *= 2
        self.size = size
        # t[0] is never written, it stays the sentinel
        self.t = [sentinel] * (2 * size)

    def update(self, pos, key):
        # set position pos to key then fix the minimums on the way up
        t = self.t
        pos += self.size
        t[pos] = key
        pos >>= 1
        while pos:
            a, b = t[2 * pos], t[2 * pos + 1]
            t[pos] = a if a < b else b
            pos >>= 1

    def query(self, lo, hi):
        # minimum over positions lo to hi - 1, or the sentinel if the range is empty
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


# O(N log N) DP: same recurrence as dp_quadratic
# gap steps use a monotone queue, overlap steps use the min tree
#
# parameters:
#   trees: sorted orange tree positions
#   cacti: sorted cactus positions
#   intervals: sprinkler intervals sorted by (left, right)
#
# returns: (cost, parent) lists, same meaning as dp_quadratic
def dp_segtree(trees, cacti, intervals):
    n = len(intervals)
    cost = [INF] * n
    parent = [-1] * n

    # sprinklers sorted by right end, and their right ends
    by_right = sorted(range(n), key=lambda k: intervals[k][R_])
    right_ends = [intervals[k][R_] for k in by_right]

    # rank[k] = position of sprinkler k in the min tree
    rank = [0] * n
    for pos in range(n):
        rank[by_right[pos]] = pos

    # the tree stores key = (value + OFFSET) * BASE + index, so one minimum gives both
    BASE = n + 1
    # makes value + OFFSET >= 1
    OFFSET = len(cacti) + 1
    # bigger than any real key
    SENTINEL = (2 * len(cacti) + 3) * BASE
    tree = MinTree(n, SENTINEL)

    # gap queue of sprinkler ids, right end increasing and cost increasing
    gap_queue = []
    # gap_queue[gap_head:] is the live part
    gap_head = 0
    # next position in by_right to enter the queue
    next_to_enter = 0

    for j in range(n):
        left, right, _, first_tree, end_tree, first_cactus, end_cactus = intervals[j]

        # start a chain if j waters the first tree
        best_cost = INF
        best_parent = -1
        if first_tree == 0:
            best_cost = end_cactus - first_cactus

        # gap steps
        if first_tree > 0:
            # sprinklers that now end left of j join the queue
            while next_to_enter < n and right_ends[next_to_enter] < left:
                k = by_right[next_to_enter]
                next_to_enter += 1

                if cost[k] < INF:
                    # worse and leaves sooner, so never the best again
                    while len(gap_queue) > gap_head and cost[gap_queue[-1]] >= cost[k]:
                        gap_queue.pop()
                    gap_queue.append(k)

            # last tree left of j
            last_tree = trees[first_tree - 1]

            # these would leave that tree dry
            while gap_head < len(gap_queue) and intervals[gap_queue[gap_head]][R_] < last_tree:
                gap_head += 1

            # front of the queue has the smallest cost
            if gap_head < len(gap_queue):
                i = gap_queue[gap_head]
                best_cost = cost[i] + end_cactus - first_cactus
                best_parent = i

        # overlap steps: predecessors with left <= right_i < right
        lo = bisect_left(right_ends, left)
        hi = bisect_left(right_ends, right)
        if lo < hi:
            key = tree.query(lo, hi)
            if key < SENTINEL:
                i = key % BASE
                new_cost = key // BASE - OFFSET + end_cactus

                if new_cost < best_cost:
                    best_cost = new_cost
                    best_parent = i

        cost[j] = best_cost
        parent[j] = best_parent

        # now j can be a predecessor
        if best_cost < INF:
            tree.update(rank[j], (best_cost - end_cactus + OFFSET) * BASE + j)

    return cost, parent


# O(N) DP for proper families only: order by left = order by right,
# so the overlap and gap blocks both slide right and two monotone queues are enough
#
# parameters:
#   trees: sorted orange tree positions
#   cacti: sorted cactus positions
#   intervals: sprinkler intervals sorted by left, both ends strictly increasing
#
# returns: (cost, parent) lists, same meaning as dp_quadratic
def dp_linear(trees, cacti, intervals):
    n = len(intervals)
    cost = [INF] * n
    parent = [-1] * n

    # overlap queue, cost[i] - end_cactus_i increasing
    overlap_queue = []
    overlap_head = 0
    # gap queue, cost[i] increasing
    gap_queue = []
    gap_head = 0
    # sprinklers before this index end left of the current one
    boundary = 0

    for j in range(n):
        left, right, _, first_tree, end_tree, first_cactus, end_cactus = intervals[j]

        # j - 1 joins the overlap block
        if j > 0 and cost[j - 1] < INF:
            value = cost[j - 1] - intervals[j - 1][CB]
            while len(overlap_queue) > overlap_head:
                back = overlap_queue[-1]
                if cost[back] - intervals[back][CB] < value:
                    break
                overlap_queue.pop()
            overlap_queue.append(j - 1)

        # ends before j starts, so it moves from the overlap block to the gap block
        while boundary < j and intervals[boundary][R_] < left:
            if cost[boundary] < INF:
                while len(gap_queue) > gap_head and cost[gap_queue[-1]] >= cost[boundary]:
                    gap_queue.pop()
                gap_queue.append(boundary)
            boundary += 1

        # no longer reaches j
        while overlap_head < len(overlap_queue) and overlap_queue[overlap_head] < boundary:
            overlap_head += 1

        best_cost = INF
        best_parent = -1

        if first_tree == 0:
            # start a chain
            best_cost = end_cactus - first_cactus
        else:
            # last tree left of j
            last_tree = trees[first_tree - 1]

            # these would leave that tree dry
            while gap_head < len(gap_queue) and intervals[gap_queue[gap_head]][R_] < last_tree:
                gap_head += 1

            if gap_head < len(gap_queue):
                i = gap_queue[gap_head]
                best_cost = cost[i] + end_cactus - first_cactus
                best_parent = i

        # overlap
        if overlap_head < len(overlap_queue):
            i = overlap_queue[overlap_head]
            new_cost = cost[i] - intervals[i][CB] + end_cactus

            if new_cost < best_cost:
                best_cost = new_cost
                best_parent = i

        cost[j] = best_cost
        parent[j] = best_parent

    return cost, parent


METHODS = {"quadratic": dp_quadratic, "segtree": dp_segtree, "linear": dp_linear}


# Finds the best chain that reaches past the last tree, then follows
# the parent pointers back to get the chosen sprinklers
#
# parameters:
#   num_trees: number of orange trees
#   intervals: the intervals the DP ran on
#   cost, parent: the lists returned by the DP
#
# returns: (chosen sprinkler indices, cacti watered)
def _finish(num_trees, intervals, cost, parent):
    best_cost = INF
    last = -1

    for j in range(len(intervals)):
        # chain reaches past the last tree
        if intervals[j][OB] == num_trees and cost[j] < best_cost:
            best_cost = cost[j]
            last = j

    if last < 0:
        raise InfeasibleError("no cover found")

    chosen = []
    while last >= 0:
        chosen.append(intervals[last][IDX])
        last = parent[last]

    chosen.reverse()
    return chosen, best_cost


# Solves the Cover problem exactly
#
# parameters:
#   O, C, S, R: tree positions, cactus positions, sprinkler positions, radii
#   method: auto (default, linear if the reduced family is proper else segtree),
#           quadratic, segtree or linear
#   stats: optional dict, filled with sprinkler counts after each reduction
#
# returns: (chosen sprinkler indices, cacti watered)
# raises: InfeasibleError if some tree can't be watered,
#         NotProperError if linear is asked for on a family with nested ranges
def solve(O, C, S, R, method="auto", stats=None):
    # sorting + R1
    trees, cacti, intervals = build_intervals(O, C, S, R)
    num_trees = len(trees)
    if num_trees == 0:
        return [], 0

    check_feasible(num_trees, intervals)
    if stats is not None:
        stats["s_input"] = len(S)
        stats["s_after_r1"] = len(intervals)

    intervals = reduce_intervals(intervals)
    if stats is not None:
        stats["s_after_dup"] = len(intervals)

    # R2 has to happen before the DP
    intervals = reduce_r2(intervals)
    proper = is_proper(intervals)
    if stats is not None:
        stats["s_after_r2"] = len(intervals)
        stats["proper"] = proper

    if method == "auto":
        if proper:
            method = "linear"
        else:
            method = "segtree"

    if method not in METHODS:
        raise ValueError(f"unknown method {method!r}; choose from: auto, {', '.join(METHODS)}")
    if method == "linear" and not proper:
        raise NotProperError("method 'linear' needs a proper family (no nested ranges)")

    if stats is not None:
        stats["method"] = method

    dp = METHODS[method]
    cost, parent = dp(trees, cacti, intervals)
    return _finish(num_trees, intervals, cost, parent)


def main():
    if len(sys.argv) < 2:
        print("usage: python3 fasterAlgo.py instance.txt [--method auto|quadratic|segtree|linear] [--stats]")
        sys.exit(1)

    O, C, S, R = read_instance(sys.argv[1])

    method = "auto"
    if "--method" in sys.argv:
        method = sys.argv[sys.argv.index("--method") + 1]

    stats = {}
    start = time.perf_counter()
    try:
        chosen, cost = solve(O, C, S, R, method=method, stats=stats)
    except InfeasibleError as e:
        print("Infeasible:", e)
        sys.exit(2)
    except NotProperError as e:
        print("Error:", e)
        sys.exit(2)
    elapsed = time.perf_counter() - start

    print(format_solution(O, C, S, R, chosen, cost, f"fasterAlgo: {stats.get('method', method)} DP"))

    if "--stats" in sys.argv:
        print(f"time: {elapsed:.4f} s")
        print(f"sprinklers: input {stats.get('s_input')}, after R1 {stats.get('s_after_r1')}, "
              f"after duplicates {stats.get('s_after_dup')}, after R2 {stats.get('s_after_r2')}")
        print(f"proper family (no nested ranges): {stats.get('proper')}")


if __name__ == "__main__":
    main()
