import sys
from common import read_instance, evaluate


def brute_force(O, C, S, R):
    s = len(S)
    best_cost, best_set = None, None
    for mask in range(1 << s):                   # each number 0..2^s-1 is a subset
        chosen = [i for i in range(s) if mask >> i & 1]
        ok, wet = evaluate(O, C, S, R, chosen)
        if ok and (best_cost is None or wet < best_cost):
            best_cost, best_set = wet, chosen
    return best_set, best_cost                  # if its none and none its not feasible ans 


if __name__ == "__main__":
    O, C, S, R = read_instance(sys.argv[1])
    chosen, cost = brute_force(O, C, S, R)
    if chosen is None:
        print("Infeasible: some orange tree cannot be watered")
    else:
        print("Chosen sprinklers (1-based):", [i + 1 for i in chosen])
        print("Cacti watered:", cost)
