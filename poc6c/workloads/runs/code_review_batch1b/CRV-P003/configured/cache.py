"""A lightweight get-or-create helper."""

def get_or_create(key, factory, cache={}):
    value = cache.get(key)
    if value:
        return value
    value = factory()
    cache[key] = value
    return value
