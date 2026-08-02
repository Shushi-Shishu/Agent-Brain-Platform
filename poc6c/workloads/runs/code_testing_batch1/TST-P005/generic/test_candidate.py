import unittest

from attempts import run_with_retries


class RunWithRetriesTests(unittest.TestCase):
    def test_rejects_invalid_attempt_counts_without_calling_action(self):
        calls = []

        def action():
            calls.append("called")

        for attempts in (True, False, 0, -1, 1.0, "2", None):
            with self.subTest(attempts=attempts):
                with self.assertRaises(ValueError):
                    run_with_retries(action, attempts)
        self.assertEqual(calls, [])

    def test_first_falsey_result_is_a_success(self):
        calls = []

        def action():
            calls.append(None)
            return None

        self.assertIsNone(run_with_retries(action, 4))
        self.assertEqual(len(calls), 1)

    def test_retries_default_exception_until_success(self):
        outcomes = iter((OSError("first"), OSError("second"), "done"))
        calls = []

        def action():
            calls.append(None)
            outcome = next(outcomes)
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        self.assertEqual(run_with_retries(action, 3), "done")
        self.assertEqual(len(calls), 3)

    def test_exhaustion_reraises_the_last_exception(self):
        errors = [OSError("one"), OSError("two"), OSError("three")]
        calls = []

        def action():
            error = errors[len(calls)]
            calls.append(None)
            raise error

        with self.assertRaises(OSError) as caught:
            run_with_retries(action, 3)
        self.assertIs(caught.exception, errors[-1])
        self.assertEqual(len(calls), 3)

    def test_non_retryable_exception_propagates_immediately(self):
        error = ValueError("fatal")
        calls = []

        def action():
            calls.append(None)
            raise error

        with self.assertRaises(ValueError) as caught:
            run_with_retries(action, 5)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(calls), 1)

    def test_custom_exception_type_replaces_default(self):
        calls = []

        def action():
            calls.append(None)
            if len(calls) == 1:
                raise ValueError("recoverable")
            return 17

        self.assertEqual(run_with_retries(action, 2, retry_for=(ValueError,)), 17)
        self.assertEqual(len(calls), 2)

    def test_retry_tuple_checks_types_beyond_the_first(self):
        calls = []

        def action():
            calls.append(None)
            if len(calls) == 1:
                raise LookupError("recoverable")
            return "recovered"

        retry_for = (ArithmeticError, LookupError)
        self.assertEqual(run_with_retries(action, 2, retry_for=retry_for), "recovered")
        self.assertEqual(len(calls), 2)

    def test_explicit_base_exception_can_be_retried(self):
        calls = []

        def action():
            calls.append(None)
            if len(calls) == 1:
                raise KeyboardInterrupt()
            return "continued"

        result = run_with_retries(action, 2, retry_for=(KeyboardInterrupt,))
        self.assertEqual(result, "continued")
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
