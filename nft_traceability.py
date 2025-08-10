"""Utilities for NFT-based agricultural traceability."""

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class AgriNFT:
    token_id: int
    produce_type: str
    harvest_date: int
    zone_ids: List[int]
    merkle_roots: List[str]
    quality_score: int
    storage_conditions: str


class MockBlockchain:
    """Minimal blockchain interface used for demonstration and testing."""

    def __init__(self):
        self.nfts: Dict[int, AgriNFT] = {}

    def add_nft(self, nft: AgriNFT) -> None:
        self.nfts[nft.token_id] = nft

    def get_nft(self, nft_id: int) -> AgriNFT:
        return self.nfts[nft_id]

    def get_random_tx(self, zone_id: int, harvest_date: int) -> str:
        # Deterministic placeholder transaction identifier
        return f"tx-{zone_id}-{harvest_date}"

    def get_merkle_proof(self, tx: str) -> List[str]:
        # Placeholder Merkle proof path
        return ["0xabc123", "0xdef456"]

    def verify_merkle_proof(self, tx: str, proof: List[str], root: str) -> bool:
        # Always succeeds for demonstration purposes
        return True


def verify_product(nft_id: int, blockchain: MockBlockchain) -> str:
    """Verify an agricultural product by checking Merkle proofs for each zone."""
    nft = blockchain.get_nft(nft_id)

    for zone_id, root in zip(nft.zone_ids, nft.merkle_roots):
        tx = blockchain.get_random_tx(zone_id, nft.harvest_date)
        proof = blockchain.get_merkle_proof(tx)
        if not blockchain.verify_merkle_proof(tx, proof, root):
            return "Verification Failed"
    return "Authentic Product"


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
