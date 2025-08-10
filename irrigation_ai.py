"""AI-driven irrigation analysis and command structures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from crt_agri import CRTResidues, recover_values

# Constants used by the decision algorithm.
CROP_DB: Dict[str, Dict[str, float]] = {
    "Tomato": {"moisture": 25.0},
}

ZONE_AREA = 1000  # square meters
DEFAULT_FLOW_RATE = 12  # liters/minute
FLOW_RATES: Dict[int, int] = {12: DEFAULT_FLOW_RATE}


def analyze_zone(report: Dict, weather: Dict) -> Dict:
    """Analyze a sensor report and compute irrigation needs.

    Args:
        report: Hourly sensor report for a single zone.
        weather: Weather forecast information.

    Returns:
        Mapping with irrigation deficit, priority and duration.
    """
    residues = CRTResidues(*report["residues"])
    recovered = recover_values(residues)
    mean_moisture = recovered["mean"]
    std_moisture = recovered["std"]
    crop_threshold = CROP_DB.get(report["crop_type"], {}).get("moisture", 0)
    deficit = max(0.0, (crop_threshold - mean_moisture)) * ZONE_AREA

    if weather.get("rain_1h", 0) > 5:  # millimeters
        deficit *= 0.3

    priority = std_moisture * deficit
    flow_rate = FLOW_RATES.get(report["zone_id"], DEFAULT_FLOW_RATE)
    duration = deficit / flow_rate if flow_rate else 0

    return {
        "zone_id": report["zone_id"],
        "deficit_liters": deficit,
        "priority": priority,
        "duration": duration,
    }


@dataclass
class IrrigationCommand:
    """Structure for valve control commands."""

    zone_id: int
    valve_id: int
    duration_sec: int
    flow_rate: int  # liters per minute


def build_command(analysis: Dict, valve_id: int) -> IrrigationCommand:
    """Create a valve control command from analysis results."""
    duration_sec = int(analysis["duration"] * 60)
    flow_rate = FLOW_RATES.get(analysis["zone_id"], DEFAULT_FLOW_RATE)
    return IrrigationCommand(
        zone_id=analysis["zone_id"],
        valve_id=valve_id,
        duration_sec=duration_sec,
        flow_rate=flow_rate,
    )
