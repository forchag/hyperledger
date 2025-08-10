"""Utilities for NFT-based agricultural traceability.

This module now provides a small in-memory ledger that performs *real*
Merkle-tree based traceability rather than relying on mocked placeholder
values.  Transactions for each agricultural zone are recorded, a Merkle
root is calculated and stored in the NFT metadata and proofs can be
generated/verified for end-to-end traceability.
"""

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, List


@dataclass
class AgriNFT:
    token_id: int
    produce_type: str
    harvest_date: int
    zone_ids: List[int]
    merkle_roots: List[str]
    quality_score: int
    storage_conditions: str


class TraceabilityLedger:
    """In-memory ledger providing basic Merkle-tree traceability."""

    def __init__(self) -> None:
        self.nfts: Dict[int, AgriNFT] = {}
        self.zone_transactions: Dict[int, List[str]] = {}

    # ------------------------------------------------------------------
    # NFT management
    def add_nft(self, nft: AgriNFT) -> None:
        self.nfts[nft.token_id] = nft

    def get_nft(self, nft_id: int) -> AgriNFT:
        return self.nfts[nft_id]

    # ------------------------------------------------------------------
    # Transaction handling and Merkle utilities
    def add_transaction(self, zone_id: int, tx_data: Dict[str, Any]) -> None:
        """Record a transaction for a zone.

        Transactions are stored as canonical JSON strings to guarantee the
        same hash when computing Merkle roots and verifying proofs.
        """

        tx_json = json.dumps(tx_data, sort_keys=True)
        self.zone_transactions.setdefault(zone_id, []).append(tx_json)

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def _build_tree(self, leaves: List[str]) -> List[List[str]]:
        tree = [leaves]
        level = leaves
        while len(level) > 1:
            if len(level) % 2 == 1:
                level = level + [level[-1]]
            new_level = []
            for i in range(0, len(level), 2):
                new_level.append(self._hash(level[i] + level[i + 1]))
            tree.append(new_level)
            level = new_level
        return tree

    def get_merkle_root(self, zone_id: int) -> str:
        txs = self.zone_transactions.get(zone_id, [])
        if not txs:
            return ""
        leaves = [self._hash(tx) for tx in txs]
        return self._build_tree(leaves)[-1][0]

    def get_merkle_proof(self, zone_id: int, tx_index: int) -> List[Dict[str, str]]:
        txs = self.zone_transactions[zone_id]
        leaves = [self._hash(tx) for tx in txs]
        tree = self._build_tree(leaves)
        index = tx_index
        proof: List[Dict[str, str]] = []
        for level in tree[:-1]:
            if len(level) % 2 == 1:
                level = level + [level[-1]]
            sibling_index = index ^ 1
            position = "left" if sibling_index < index else "right"
            proof.append({"hash": level[sibling_index], "position": position})
            index //= 2
        return proof

    def verify_merkle_proof(
        self, tx_data: Dict[str, Any], proof: List[Dict[str, str]], root: str
    ) -> bool:
        current = self._hash(json.dumps(tx_data, sort_keys=True))
        for step in proof:
            if step["position"] == "left":
                current = self._hash(step["hash"] + current)
            else:
                current = self._hash(current + step["hash"])
        return current == root

    def trace_zone(self, zone_id: int) -> Dict[str, Any]:
        """Return all transactions for ``zone_id`` along with Merkle proofs.

        Args:
            zone_id (int): Zone whose transaction history should be traced.

        Returns:
            Dict[str, Any]: A mapping with two keys:

                ``root`` (str):
                    Hex-encoded Merkle root derived from the zone's current
                    transactions. An empty string is returned when the zone has
                    no recorded transactions.

                ``transactions`` (List[Dict[str, Any]]):
                    Items are ordered identically to how transactions were
                    added. Each item contains:

                    ``tx`` (Dict[str, Any]):
                        The original transaction data as provided to
                        :meth:`add_transaction`.

                    ``proof`` (List[Dict[str, str]]):
                        Merkle inclusion proof for ``tx``. Each step contains a
                        sibling ``hash`` (hex digest) and its ``position`` which
                        is either ``"left"`` or ``"right"``. The list is ordered
                        from the leaf level up to the root. A proof is empty
                        when the zone only has a single transaction.

        Invariants:
            * ``len(transactions)`` equals the number of recorded transactions
              for ``zone_id``.
            * Proofs always verify against the returned ``root`` using
              :meth:`verify_merkle_proof`.
        """

        txs = self.zone_transactions.get(zone_id, [])
        root = self.get_merkle_root(zone_id)
        trace = []
        for idx, tx in enumerate(txs):
            trace.append(
                {
                    "tx": json.loads(tx),
                    "proof": self.get_merkle_proof(zone_id, idx),
                }
            )
        return {"root": root, "transactions": trace}


def verify_product(nft_id: int, ledger: TraceabilityLedger) -> str:
    """Verify an agricultural product by checking Merkle roots for each zone."""
    nft = ledger.get_nft(nft_id)

    for zone_id, root in zip(nft.zone_ids, nft.merkle_roots):
        if ledger.get_merkle_root(zone_id) != root:
            return "Verification Failed"
    return "Authentic Product"


def trace_product(nft_id: int, ledger: TraceabilityLedger) -> Dict[int, Dict[str, Any]]:
    """Return full traceability information for an NFT."""
    nft = ledger.get_nft(nft_id)
    return {zone_id: ledger.trace_zone(zone_id) for zone_id in nft.zone_ids}


def calculate_quality_score(zone_data: Dict[str, Any]) -> int:
    """Compute quality score using zone metrics.

    Returns a value between 60 and 100.
    """
    score = 100
    score -= zone_data["anomaly_days"] * 5
    if 45 < zone_data["avg_moisture"] < 55:
        score += 5
    if 18 < zone_data["min_temp"] and zone_data["max_temp"] < 28:
        score += 5
    if zone_data["fertilizer_events"] > 4:
        score -= 10
    return max(60, min(100, score))

