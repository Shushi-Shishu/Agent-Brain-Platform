# Add high-value tests for `bucket_index`

Create `test_candidate.py` using only the standard-library `unittest` framework.
Test the documented behavior of `bucket_index` without changing `buckets.py`.

Constraints:

- add at most 8 test functions or methods;
- each execution must finish within 3 seconds;
- assert behavior through the public function only;
- do not read or inspect source files or bytecode;
- keep every test deterministic and independent.

The score rewards the number of distinct behavioral faults exposed while the
current correct implementation continues to pass.
