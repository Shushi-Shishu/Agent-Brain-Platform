"""Sealed scorer entry point for TST-P003."""

import importlib.util
from pathlib import Path

from workloads.code_testing import score_candidate


CASE_ID = "TST-P003"


def _faults():
    path = Path(__file__).with_name("fault_set.py")
    spec = importlib.util.spec_from_file_location("tst_p003_faults", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FAULTS


def evaluate(candidate_test, public_root):
    return score_candidate(
        task_id=CASE_ID,
        public_root=Path(public_root),
        module_filename="labels.py",
        candidate_test=Path(candidate_test),
        faults=_faults(),
    )
