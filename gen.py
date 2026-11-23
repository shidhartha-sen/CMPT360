import random
import sys


def generate(s, o, c, L, rmin, rmax, seed):
    rng = random.Random(seed)
    S = [rng.randrange(L) for _ in range(s)]
    R = [rng.randint(rmin, rmax) for _ in range(s)]
    O = []
    for _ in range(o):
        k = rng.randrange(s)                      
        O.append(rng.randint(S[k] - R[k], S[k] + R[k]))
    C = [rng.randrange(L) for _ in range(c)]
    return O, C, S, R


if __name__ == "__main__":
    s, o, c, L, rmin, rmax, seed = map(int, sys.argv[1:8])
    O, C, S, R = generate(s, o, c, L, rmin, rmax, seed)
    print(len(O), len(C), len(S))
    for arr in (O, C, S, R):
        print(" ".join(map(str, arr)))