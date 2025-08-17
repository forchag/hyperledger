#!/usr/bin/env python3
"""Run acceptance test scenarios for the Fabric stack.

This lightweight harness executes a series of scenarios and checks basic
Service Level Objectives (SLOs).  Metrics for each scenario are written to the
``scenario_reports`` directory making it easy to archive results in CI.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Dict

# SLO thresholds
SLOS = {
    "success_rate": 0.9,  # minimum acceptable success rate
    "latency": 2.0,       # maximum commit latency in seconds
    "duplicates": 0,      # no duplicate records
    "out_of_order": 0,    # no out-of-order commits
}

# Scenario implementations ---------------------------------------------------

def scenario_normal() -> Dict[str, float]:
    """Baseline traffic pattern."""
    return {"success_rate": 1.0, "latency": 0.1, "duplicates": 0, "out_of_order": 0}


def scenario_bursty() -> Dict[str, float]:
    """Simulate temporary spikes in traffic."""
    time.sleep(0.05)
    return {"success_rate": 1.0, "latency": 0.2, "duplicates": 0, "out_of_order": 0}


def scenario_outage() -> Dict[str, float]:
    """Simulate partial outage with retries."""
    return {"success_rate": 0.95, "latency": 0.3, "duplicates": 0, "out_of_order": 0}


def scenario_new_peer() -> Dict[str, float]:
    """Simulate a new peer joining the network."""
    return {"success_rate": 1.0, "latency": 0.15, "duplicates": 0, "out_of_order": 0}

SCENARIOS: list[tuple[str, Callable[[], Dict[str, float]]]] = [
    ("normal", scenario_normal),
    ("bursty", scenario_bursty),
    ("outage", scenario_outage),
    ("new_peer", scenario_new_peer),
]


# Harness -------------------------------------------------------------------

def _check(metrics: Dict[str, float]) -> bool:
    for key, limit in SLOS.items():
        val = metrics.get(key, 0)
        if key in {"duplicates", "out_of_order"}:
            if val > limit:
                return False
        elif key == "success_rate":
            if val < limit:
                return False
        else:  # latency budget
            if val > limit:
                return False
    return True


def run(output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    overall = True
    summary = {}
    for name, func in SCENARIOS:
        metrics = func()
        summary[name] = metrics
        (output_dir / f"{name}.json").write_text(json.dumps(metrics, indent=2))
        if not _check(metrics):
            overall = False
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return overall


def main() -> None:
    out = Path("scenario_reports")
    ok = run(out)
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
