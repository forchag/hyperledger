import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # leaf-node

from telemetry.transport import PiClient, create_debug_app  # noqa: E402


class DummyResponse:
    def __init__(self, json_data=None):
        self._json = json_data or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


class DummySession:
    def __init__(self):
        self.handshakes = 0
        self.posts = []
        self.fail = False

    def get(self, url, timeout=5):
        if self.fail:
            raise RuntimeError("down")
        self.handshakes += 1
        return DummyResponse({"nonce": "n"})

    def post(self, url, json=None, timeout=5):
        if self.fail:
            raise RuntimeError("down")
        self.posts.append((url, json))
        return DummyResponse()


def test_sign_and_handshake():
    client = PiClient(["http://pi"], hmac_key=b"secret")
    sess = DummySession()
    client.session = sess
    client.send({"data": 1})
    # one GET for nonce and two POSTs (handshake + ingest)
    assert sess.handshakes == 1
    assert len(sess.posts) == 2
    ingest = sess.posts[1][1]
    assert ingest["seq"] == 1
    assert ingest["kid"] == "hmac"
    assert "sig" in ingest


def test_failover_after_handshake_failure():
    client = PiClient(["http://a", "http://b"], hmac_key=b"k", max_failures=1)
    sess = DummySession()
    sess.fail = True
    client.session = sess
    client.send({"data": 1})
    # payload buffered and target switched to index 1
    assert client.buffer
    assert client._current == 1


def test_health_status_endpoint():
    client = PiClient(["http://pi"], hmac_key=b"k")
    app = create_debug_app(client)
    with app.test_client() as c:
        assert c.get("/health").json == {"status": "ok"}
        client.buffer.append({"x": 1})
        data = c.get("/status").json
        assert data["buffer_depth"] == 1
