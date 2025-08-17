"""Sensor adapter classes for ESP32 leaf node.

Each sensor exposes a common ``read`` interface returning a dictionary with
``value``, ``ts`` (epoch seconds) and ``quality`` fields.  The concrete sensor
classes wrap callables that perform the actual hardware interaction so that
unit tests can inject deterministic readers.  Basic calibration hooks
(offset, scale and optional temperature compensation) and range validation are
provided.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple, Dict, Any
import time
import random


ReadFn = Callable[[], float]


@dataclass
class Calibration:
    """Simple calibration parameters for a sensor."""

    offset: float = 0.0
    scale: float = 1.0
    # Temperature compensation factor or function.  When a float is supplied the
    # raw value is adjusted by ``factor * ambient_temp``.  When a callable is
    # provided it receives ``(value, ambient_temp)`` and should return the
    # compensated value.
    temp_comp: Optional[Callable[[float, float], float]] | float = None


class Sensor:
    """Base sensor implementing the common read interface."""

    def __init__(
        self,
        reader: ReadFn,
        *,
        calibration: Optional[Calibration] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> None:
        self.reader = reader
        self.calibration = calibration or Calibration()
        self.min_value = min_value
        self.max_value = max_value

    # ------------------------------------------------------------------
    def _apply_calibration(self, value: float, ambient_temp: Optional[float]) -> float:
        value = (value + self.calibration.offset) * self.calibration.scale
        if self.calibration.temp_comp is not None and ambient_temp is not None:
            tc = self.calibration.temp_comp
            if callable(tc):
                value = tc(value, ambient_temp)
            else:
                value = value + tc * ambient_temp
        return value

    # ------------------------------------------------------------------
    def read(self, ambient_temp: Optional[float] = None) -> Dict[str, Any]:
        """Return a calibrated sensor reading.

        ``ambient_temp`` may be supplied for sensors requiring temperature
        compensation (e.g. humidity).  Out-of-range values raise ``ValueError``.
        """

        raw = self.reader()
        value = self._apply_calibration(raw, ambient_temp)
        if (self.min_value is not None and value < self.min_value) or (
            self.max_value is not None and value > self.max_value
        ):
            raise ValueError("sensor reading out of range")
        return {"value": value, "ts": time.time(), "quality": "ok"}


# ---------------------------------------------------------------------------
# Concrete sensor implementations

class DHT22Sensor(Sensor):
    """Adapter for DHT22 providing temperature or humidity readings."""

    def __init__(
        self,
        metric: str = "temperature",
        reader: Optional[Callable[[], Tuple[float, float]]] = None,
        *,
        calibration: Optional[Calibration] = None,
        temp_comp: Optional[Callable[[float, float], float] | float] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
    ) -> None:
        self.metric = metric
        reader = reader or (lambda: (random.uniform(20, 30), random.uniform(40, 70)))
        super().__init__(
            lambda: self._select(reader()),
            calibration=calibration or Calibration(temp_comp=temp_comp),
            min_value=min_value,
            max_value=max_value,
        )

    def _select(self, pair: Tuple[float, float]) -> float:
        temp, hum = pair
        return temp if self.metric == "temperature" else hum


class LightSensor(Sensor):
    def __init__(
        self,
        reader: Optional[ReadFn] = None,
        *,
        calibration: Optional[Calibration] = None,
        min_value: Optional[float] = 0.0,
        max_value: Optional[float] = 1023.0,
    ) -> None:
        reader = reader or (lambda: random.uniform(0.0, 1023.0))
        super().__init__(
            reader,
            calibration=calibration,
            min_value=min_value,
            max_value=max_value,
        )


class SoilMoistureSensor(Sensor):
    def __init__(
        self,
        reader: Optional[ReadFn] = None,
        *,
        calibration: Optional[Calibration] = None,
        min_value: Optional[float] = 0.0,
        max_value: Optional[float] = 100.0,
    ) -> None:
        reader = reader or (lambda: random.uniform(0.0, 100.0))
        super().__init__(reader, calibration=calibration, min_value=min_value, max_value=max_value)


class PHSensor(Sensor):
    def __init__(
        self,
        reader: Optional[ReadFn] = None,
        *,
        calibration: Optional[Calibration] = None,
        min_value: Optional[float] = 0.0,
        max_value: Optional[float] = 14.0,
    ) -> None:
        reader = reader or (lambda: random.uniform(0.0, 14.0))
        super().__init__(reader, calibration=calibration, min_value=min_value, max_value=max_value)


class WaterLevelSensor(Sensor):
    def __init__(
        self,
        reader: Optional[ReadFn] = None,
        *,
        calibration: Optional[Calibration] = None,
        min_value: Optional[float] = 0.0,
        max_value: Optional[float] = 100.0,
    ) -> None:
        reader = reader or (lambda: random.uniform(0.0, 100.0))
        super().__init__(reader, calibration=calibration, min_value=min_value, max_value=max_value)


__all__ = [
    "Calibration",
    "Sensor",
    "DHT22Sensor",
    "LightSensor",
    "SoilMoistureSensor",
    "PHSensor",
    "WaterLevelSensor",
]
