import os
import sys
import tempfile
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from telemetry.seq_store import SeqStore


def test_sequence_persists_across_reinitialisation(tmp_path):
    seq_path = tmp_path / "seq.dat"
    store = SeqStore(str(seq_path))
    first = store.next()
    second = store.next()
    assert second == first + 1

    # Recreate store to simulate reboot
    store2 = SeqStore(str(seq_path))
    assert store2.next() == second + 1
