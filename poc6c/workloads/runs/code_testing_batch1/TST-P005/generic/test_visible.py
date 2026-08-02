import unittest

from attempts import run_with_retries


class RetryTests(unittest.TestCase):
    def test_returns_successful_value(self):
        self.assertEqual(run_with_retries(lambda: "ok", 2), "ok")


if __name__ == "__main__":
    unittest.main()
