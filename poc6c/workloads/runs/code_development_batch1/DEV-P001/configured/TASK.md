# Normalize article slugs

`slugify(text)` should return a lowercase ASCII slug.

Requirements:

- trim whitespace at both ends;
- replace every run of non-alphanumeric characters with one `-`;
- remove `-` from the beginning and end;
- return an empty string when no alphanumeric characters remain.

Examples: `"  Blue Sky!  "` becomes `"blue-sky"` and `"A___B"` becomes
`"a-b"`.
