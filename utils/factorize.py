from itertools import product


def factorize(cond):
    values = list(cond.values())
    for i in range(0, len(values)):
        if not isinstance(values[i], list):
            values[i] = [values[i]]

    conds = list(dict(zip(cond, x)) for x in product(*values))
    return conds
