# Cover — CMPT 360 Project, Option 4

Choose a subset of sprinklers on a line that waters every orange tree while watering
as few cacti as possible. Sprinkler i waters the closed interval [S[i] − R[i], S[i] + R[i]].

Requirements: Python 3.8+. No external packages are used by the algorithms
(binary search and queues are implemented in the code itself).

## Files

| File | What it is |
|---|---|
| `baseline.py` | Exact branch-and-bound search: branch on the sprinklers that reach the leftmost dry tree. Exponential worst case. |
| `fasterAlgo.py` | Exact polynomial algorithms based on the chain lemma: `quadratic` O(s²) DP, `segtree` O(N log N) DP (min-tree + monotone queue), `linear` O(N)-after-sorting DP for proper families (no nested ranges, e.g. equal radii). `auto` (default) picks `linear` when possible, else `segtree`. |
| `common.py` | Input reading, binary search, preprocessing (sorting, ranks, reduction R1), feasibility check, independent solution checker, output formatting. |
| `bruteforce.py` | Tries all 2^s subsets. Only for testing on tiny inputs. |
| `gen.py` | Random instance generator. |
| `test_correctness.py` | Randomized tests: all algorithms vs. brute force (small), and vs. each other (medium). |
| `examples/` | The handout example as printed, and a corrected version. |

## Input format

Whitespace separated; `#` starts a comment.

```
o c s
# orange tree positions
O[1] ... O[o]
# cactus positions
C[1] ... C[c]
# sprinkler positions
S[1] ... S[s]
# sprinkler radii
R[1] ... R[s]
```

Integers or decimals are fine. Endpoints count as watered.

## Running

```bash
python3 baseline.py   examples/handout_corrected.txt --stats
# stop after 10 s
python3 baseline.py   instance.txt --limit 10
python3 fasterAlgo.py examples/handout_corrected.txt --stats
# auto | quadratic | segtree | linear
python3 fasterAlgo.py instance.txt --method segtree
```

The output lists the chosen sprinklers (1-based index and position), whether every
orange tree is watered, and the number of watered cacti, re-checked independently.
`--stats` adds the running time and how many sprinklers the reductions removed.

Generate a random instance:

```bash
# s o c L rmin rmax seed   (rmin = rmax gives equal radii, a proper family)
python3 gen.py 5000 5000 5000 26250 1 20 1 > instance.txt
```

## Tests

```bash
# every algorithm vs. brute force on small instances
python3 test_correctness.py 2000
# larger instances
python3 test_correctness.py --medium
```

## Timing notes (my machine)

| s    | quadratic        | segtree          | segtree speedup |
|------|------------------|------------------|-----------------|
| 2000 | 0.096 s          | 0.019 s          | ~5×             |
| 4000 | 0.399 s (×4.2)   | 0.026 s          | ~16×            |
| 8000 | 1.786 s (×4.5)   | 0.061 s (×2.4)   | ~29×            |

Both methods give the same cacti count at every size.
Quadratic grows about ×4 per doubling of s (O(s²)); segtree about ×2 (O(N log N)).

## Note on the handout example

With the radii as printed, R = {2, 2, 1}, sprinkler 1 waters [1, 5] and cannot reach the
tree at 6, so every sprinkler is forced and the optimum waters 2 cacti
(`examples/handout.txt`). With R[1] = 3 the stated answer (sprinklers at 3 and
12, one cactus) is optimal (`examples/handout_corrected.txt`).
