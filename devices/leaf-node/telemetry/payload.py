"""Payload construction with optional CRT compaction."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from crt_parallel import crt_decompose


def crt_encoder(values: Iterable[int], moduli: Iterable[int]) -> Dict[str, List[int]]:
    """Pack ``values`` into CRT residues using ``moduli``.

    The values are concatenated in a base equal to the smallest modulus.  All
    values must therefore be strictly smaller than that modulus for the packing
    to be reversible.
    """

    vals = [int(v) for v in values]
    mods = list(int(m) for m in moduli)
    base = min(mods)
    if any(v >= base for v in vals):
        raise ValueError("values must be smaller than smallest modulus")

    block = 0
    for v in vals:
        block = block * base + v
    residues = crt_decompose(block, mods)
    return {"m": mods, "r": residues}


def build_payload(
    summary: Dict[str, Any], *, moduli: Optional[List[int]] = None, size_limit: int = 100
) -> Dict[str, Any]:
    """Return a payload ensuring it fits within ``size_limit`` bytes.

    When the JSON representation exceeds ``size_limit`` and ``moduli`` are
    supplied, numeric stats are replaced with a compact ``crt`` field.  If the
    payload remains too large the raw ``tail`` data is dropped.
    """

    payload: Dict[str, Any] = {
        "window_id": summary["window_id"],
        "stats": summary["stats"],
        "last_ts": summary["last_ts"],
        "tail": summary.get("tail", []),
    }

    body = json.dumps(payload, separators=(",", ":")).encode()
    if len(body) > size_limit and moduli:
        stats = payload.pop("stats")
        numbers = [
            int(round(stats["min"] * 100)),
            int(round(stats["avg"] * 100)),
            int(round(stats["max"] * 100)),
            int(round(stats["std"] * 100)),
            int(stats["count"]),
        ]
        payload["crt"] = crt_encoder(numbers, moduli)
        body = json.dumps(payload, separators=(",", ":")).encode()
    if len(body) > size_limit and "tail" in payload:
        payload.pop("tail")
    return payload


__all__ = ["crt_encoder", "build_payload"]
