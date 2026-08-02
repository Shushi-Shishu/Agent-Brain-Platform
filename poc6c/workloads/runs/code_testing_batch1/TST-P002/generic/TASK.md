# Add high-value tests for `SlidingGate`

Create `test_candidate.py` with standard-library `unittest` tests for the public
class in `gate.py`. Do not alter the supplied module.

Constraints:

- add at most 8 test functions or methods;
- each execution must finish within 3 seconds;
- exercise behavior only through construction and `allow`;
- do not read or inspect source files, object internals, or bytecode;
- avoid clocks, sleeps, randomness, and order-dependent tests.

The score counts distinct state and boundary faults exposed while requiring the
supplied implementation to pass on repeated executions.
