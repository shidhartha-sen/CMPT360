# CMPT360

## Timing: quadratic vs segtree

| s    | quadratic        | segtree          | segtree speedup |
|------|------------------|------------------|-----------------|
| 2000 | 0.096 s          | 0.019 s          | 5×             |
| 4000 | 0.399 s          | 0.026 s          | 16×            |
| 8000 | 1.786 s          | 0.061 s          | 29×            |

Both methods give the same cacti count at every size.
Quadratic grows about ×4 per doubling, as O(s²) predicts; segtree grows about ×2 at the larger sizes (small sizes are dominated by fixed overhead).
