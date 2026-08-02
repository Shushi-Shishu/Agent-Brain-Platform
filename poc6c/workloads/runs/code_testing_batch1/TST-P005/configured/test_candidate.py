import unittest

from attempts import run_with_retries


class RunWithRetriesTests(unittest.TestCase):
    def test_falsey_success_is_returned_without_extra_calls(self):
        calls = []

        def action():
            calls.append(None)
            return None

        self.assertIsNone(run_with_retries(action, 4))
        self.assertEqual(len(calls), 1)

    def test_retries_default_exception_subclass_until_success(self):
        calls = []

        def action():
            calls.append(None)
            if len(calls) < 3:
                raise FileNotFoundError("temporarily unavailable")
            return "ready"

        self.assertEqual(run_with_retries(action, 3), "ready")
        self.assertEqual(len(calls), 3)

    def test_exhaustion_reraises_the_last_exception_instance(self):
        errors = [OSError("first"), OSError("second"), OSError("last")]
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
        error = ValueError("invalid result")
        calls = []

        def action():
            calls.append(None)
            raise error

        with self.assertRaises(ValueError) as caught:
            run_with_retries(action, 5)

        self.assertIs(caught.exception, error)
        self.assertEqual(len(calls), 1)

    def test_custom_exception_policy_is_honored(self):
        calls = []

        def action():
            calls.append(None)
            if len(calls) == 1:
                raise LookupError("retry me")
            return 17

        self.assertEqual(
            run_with_retries(action, 2, retry_for=(LookupError,)),
            17,
        )
        self.assertEqual(len(calls), 2)

    def test_custom_exception_policy_replaces_default(self):
        error = OSError("not selected")
        calls = []

        def action():
            calls.append(None)
            raise error

        with self.assertRaises(OSError) as caught:
            run_with_retries(action, 4, retry_for=(LookupError,))

        self.assertIs(caught.exception, error)
        self.assertEqual(len(calls), 1)

    def test_invalid_attempt_counts_fail_before_action_runs(self):
        invalid_counts = (True, False, 0, -1, 1.0, "2", None)

        for attempts in invalid_counts:
            with self.subTest(attempts=attempts):
                calls = []

                def action():
                    calls.append(None)
                    return "unexpected"

                with self.assertRaises(ValueError):
                    run_with_retries(action, attempts)
                self.assertEqual(calls, [])

    def test_one_attempt_means_exactly_one_execution(self):
        error = OSError("failed")
        calls = []

        def action():
            calls.append(None)
            raise error

        with self.assertRaises(OSError) as caught:
            run_with_retries(action, 1)

        self.assertIs(caught.exception, error)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
