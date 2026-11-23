import sys
from common import read_instance, evaluate


def brute_force(O, C, S, R):
    s = len(S)
    best_cost, best_set = None, None
    # each number 0..2^s-1 is a subset
    for mask in range(1 << s):                   
        chosen = [i for i in range(s) if mask >> i & 1]
        ok, wet = evaluate(O, C, S, R, chosen)
        if ok and (best_cost is None or wet < best_cost):
            best_cost, best_set = wet, chosen
        # if its none and none its not feasible ans 
    return best_set, best_cost                  


if __name__ == "__main__":
    O, C, S, R = read_instance(sys.argv[1])
    chosen, cost = brute_force(O, C, S, R)
    if chosen is None:
        print("some orange tree cannot be watered")
    else:
        print("chosen sprinklers (1-based):", [i + 1 for i in chosen])
        print("cacti watered:", cost)
