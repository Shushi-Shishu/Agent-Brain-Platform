# Review settings helpers

Review `settings.py` for a command-line service. Retry counts must be plain
integers from zero through ten; booleans are not valid counts. Timeouts are
bounded to the inclusive interval supplied by the caller.

This is a near-clean change, so avoid speculative findings. Report only
actionable defects. For each finding, provide `file`, `line`, `category`,
`severity`, and a concise explanation of impact and repair. Do not rewrite the
file.
