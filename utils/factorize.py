def factorize(cond):
    from itertools import product
    conds = list(dict(zip(cond, x)) for x in product(*cond.values()))
    return conds
