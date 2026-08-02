# Add high-value tests for `run_with_retries`

Create `test_candidate.py` using standard-library `unittest`. Test observable
retry, success, and exception behavior without editing `attempts.py`.

Constraints:

- add at most 8 test functions or methods;
- each execution must finish within 3 seconds;
- use deterministic in-memory callables;
- do not read or inspect source files, callable bytecode, or module internals;
- do not use sleeps, networking, or third-party packages.

The score rewards distinct error-handling faults exposed while the current
implementation passes consistently.
