import unittest

from attempts import run_with_retries


class ReferenceRetryTests(unittest.TestCase):
    def test_uses_last_available_attempt(self):
        calls = []
        def action():
            calls.append(1)
            if len(calls) < 3:
                raise OSError("again")
            return "done"
        self.assertEqual(run_with_retries(action, 3), "done")
        self.assertEqual(len(calls), 3)

    def test_unselected_exception_is_not_retried(self):
        calls = []
        def action():
            calls.append(1)
            raise ValueError("stop")
        with self.assertRaises(ValueError):
            run_with_retries(action, 4)
        self.assertEqual(len(calls), 1)

    def test_final_selected_exception_is_raised(self):
        with self.assertRaises(OSError):
            run_with_retries(lambda: (_ for _ in ()).throw(OSError("no")), 2)


if __name__ == "__main__":
    unittest.main()
