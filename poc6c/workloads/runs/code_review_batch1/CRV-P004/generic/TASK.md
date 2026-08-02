# Review audit-record changes

Review `audit.py` for a service that processes credentials. Audit records must
never include credential values. Redaction must cover a matching secret even
when the message uses different letter casing.

Report only actionable defects. For each finding, provide `file`, `line`,
`category`, `severity`, and a concise explanation of impact and repair. Do not
rewrite the file.
