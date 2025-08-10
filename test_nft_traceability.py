import nft_traceability as nt


def test_traceability_merkle_proof():
    ledger = nt.TraceabilityLedger()
    ledger.add_transaction(1, {"batch": 1, "weight": 10})
    ledger.add_transaction(1, {"batch": 2, "weight": 12})

    root = ledger.get_merkle_root(1)
    nft = nt.AgriNFT(
        token_id=1,
        produce_type="corn",
        harvest_date=20230101,
        zone_ids=[1],
        merkle_roots=[root],
        quality_score=90,
        storage_conditions="cool",
    )
    ledger.add_nft(nft)

    assert nt.verify_product(1, ledger) == "Authentic Product"

    trace = nt.trace_product(1, ledger)
    zone_trace = trace[1]
    tx_info = zone_trace["transactions"][0]
    assert ledger.verify_merkle_proof(tx_info["tx"], tx_info["proof"], zone_trace["root"])
