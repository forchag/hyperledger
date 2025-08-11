import pytest
from hierarchical_consensus import run_advanced_consensus


def test_run_advanced_consensus():
    result = run_advanced_consensus(19.25)
    assert result["S1"] == pytest.approx(19.25)
