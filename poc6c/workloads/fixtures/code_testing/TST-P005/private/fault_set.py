"""Evaluator-only deterministic faults for TST-P005."""

FAULTS = [
    {
        "fault_id": "TST-P005-F01-one-fewer-attempt",
        "source": '''def run_with_retries(action, attempts, retry_for=(OSError,)):
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")
    for index in range(max(1, attempts - 1)):
        try:
            return action()
        except retry_for:
            if index == max(1, attempts - 1) - 1:
                raise
''',
    },
    {
        "fault_id": "TST-P005-F02-retries-unselected-error",
        "source": '''def run_with_retries(action, attempts, retry_for=(OSError,)):
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")
    for index in range(attempts):
        try:
            return action()
        except Exception:
            if index == attempts - 1:
                raise
''',
    },
    {
        "fault_id": "TST-P005-F03-swallows-final-error",
        "source": '''def run_with_retries(action, attempts, retry_for=(OSError,)):
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")
    for index in range(attempts):
        try:
            return action()
        except retry_for:
            if index == attempts - 1:
                return None
''',
    },
]
