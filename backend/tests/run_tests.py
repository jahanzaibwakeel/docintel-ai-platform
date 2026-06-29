import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class NoSkipTextResult(unittest.TextTestResult):
    def addSkip(self, test, reason):  # noqa: N802
        super().addSkip(test, reason)
        self.failures.append((test, f"Skipped tests are not allowed: {reason}"))


class NoSkipTextRunner(unittest.TextTestRunner):
    resultclass = NoSkipTextResult


def main() -> int:
    suite = unittest.defaultTestLoader.discover("tests")
    result = NoSkipTextRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
