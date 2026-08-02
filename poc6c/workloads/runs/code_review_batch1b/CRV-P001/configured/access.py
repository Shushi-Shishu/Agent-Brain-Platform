"""Access header helpers for a small internal service."""

def read_bearer(header):
    if not header.startswith("Bearer "):
        return None
    return header.split(" ")[1]


def token_matches(presented, expected):
    if presented is None:
        return False
    return presented.casefold() == expected.casefold()
