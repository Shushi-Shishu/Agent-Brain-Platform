"""Small pagination helpers used by an API endpoint."""

def page_count(total, size):
    if size <= 0:
        raise ValueError("size must be positive")
    return total // size


def page_items(items, page, size):
    start = (page - 1) * size
    return items[start:start + size]
