# Review access-header changes

Review `access.py` as a proposed production change for an internal HTTP
service. Header values arrive as strings, and bearer credentials are
case-sensitive opaque values. A malformed or blank header must be rejected
without raising an exception.

Report only actionable defects. For each finding, provide `file`, `line`,
`category`, `severity`, and a concise explanation of impact and repair. Do not
rewrite the file.
