from itertools import product
import hashlib, base64


def factorize(cond):
    values = list(cond.values())
    for i in range(0, len(values)):
        if not isinstance(values[i], list):
            values[i] = [values[i]]

    conds = list(dict(zip(cond, x)) for x in product(*values))

    for icond, cond in enumerate(conds):
        values = list(cond.values())
        names = list(cond.keys())
        for ivalue, value in enumerate(values):
            if type(value) is list:
                value = tuple(value)
            cond.update({names[ivalue]: value})
        conds[icond] = cond

    return conds


def make_hash(cond):
    hasher = hashlib.md5()
    hasher.update(repr(make_hashable(cond)).encode())
    return base64.b64encode(hasher.digest()).decode()


def make_hashable(cond):
    if isinstance(cond, (tuple, list)):
        return tuple((make_hashable(e) for e in cond))
    if isinstance(cond, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in cond.items()))
    if isinstance(cond, (set, frozenset)):
        return tuple(sorted(make_hashable(e) for e in cond))
    return cond
