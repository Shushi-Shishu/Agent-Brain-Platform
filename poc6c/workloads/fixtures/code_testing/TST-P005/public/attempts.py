"""Run an action with a bounded number of recoverable attempts."""


def run_with_retries(action, attempts, retry_for=(OSError,)):
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")
    for index in range(attempts):
        try:
            return action()
        except retry_for:
            if index == attempts - 1:
                raise
