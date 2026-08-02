"""Parse a compact line-oriented label format."""


def parse_labels(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    result = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"line {line_number} has no separator")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key:
            raise ValueError(f"line {line_number} has an empty key")
        if key in result:
            raise ValueError(f"line {line_number} repeats {key!r}")
        result[key] = value
    return result
