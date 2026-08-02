# Review pagination changes

Review `pagination.py` for a JSON API. Page numbers are one-based, page size
must be positive, and the reported page count must include a final partial
page. Empty collections have zero pages.

Report only actionable defects. For each finding, provide `file`, `line`,
`category`, `severity`, and a concise explanation of impact and repair. Do not
rewrite the file.
