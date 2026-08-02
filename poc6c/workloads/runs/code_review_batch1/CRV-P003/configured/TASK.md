# Review cache helper changes

Review `cache.py` for a reusable library. Separate callers must not share state
unless they explicitly pass the same cache, and any cached value, including
false-like values, must be returned without calling the factory again.

Report only actionable defects. For each finding, provide `file`, `line`,
`category`, `severity`, and a concise explanation of impact and repair. Do not
rewrite the file.
