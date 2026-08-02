# Add high-value tests for `parse_labels`

Create `test_candidate.py` using standard-library `unittest`. Cover the public
contract implied by the docstring, implementation, and error messages without
editing `labels.py`.

Constraints:

- add at most 8 test functions or methods;
- each execution must finish within 3 seconds;
- call only the public function;
- do not read or inspect source files or bytecode;
- use fixed input strings and deterministic assertions.

The score is based on distinct parsing and validation faults exposed, provided
the current implementation passes twice with identical results.
