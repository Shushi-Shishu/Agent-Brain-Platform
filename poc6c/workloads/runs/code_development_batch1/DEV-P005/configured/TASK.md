# Produce retry delays

`retry_delays(attempts, base_seconds, cap_seconds)` returns one delay for each
retry attempt. The first delay is `base_seconds`; later delays double until
reaching the cap. No returned delay may exceed the cap.

Return an empty list for zero attempts. Raise `ValueError` for negative
attempts, non-positive base values, or a cap smaller than the base. The
function must be deterministic and dependency-free.
