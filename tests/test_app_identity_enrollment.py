import importlib.util
import sys
import types
from pathlib import Path


def _stub(*args, **kwargs):
    return None


def test_ensure_admin_enrollment_invokes_enroll_identity(monkeypatch, tmp_path):
    fake_client = types.ModuleType("hlf_client")
    for name in [
        "record_sensor_data",
        "register_device",
        "log_event",
        "get_sensor_data",
        "get_sensor_history",
        "get_all_sensor_data",
        "get_state_on",
        "get_latest_readings",
        "list_devices",
        "get_block",
        "get_incidents",
        "get_quarantined",
        "get_attestations",
        "get_block_events",
        "log_security_incident",
        "attest_device",
    ]:
        setattr(fake_client, name, _stub)
    monkeypatch.setitem(sys.modules, "hlf_client", fake_client)

    fake_incident = types.ModuleType("incident_responder")
    fake_incident.watch = _stub
    monkeypatch.setitem(sys.modules, "incident_responder", fake_incident)

    spec = importlib.util.spec_from_file_location("flask_app.app", Path("flask_app/app.py"))
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)  # type: ignore

    calls = []

    def fake_enroll(name, ca_url, msp_dir, tls_dir, peer_endpoint, orderer_endpoint, **kwargs):
        calls.append(
            {
                "name": name,
                "ca_url": ca_url,
                "msp_dir": Path(msp_dir),
                "tls_dir": Path(tls_dir),
                "peer": peer_endpoint,
                "orderer": orderer_endpoint,
                "kwargs": kwargs,
            }
        )
        return True

    monkeypatch.setattr(app, "enroll_identity", fake_enroll)

    net_dir = tmp_path
    app.ensure_admin_enrollment(net_dir)

    assert len(calls) == 2
    first, second = calls
    assert first["name"] == "admin"
    assert first["ca_url"] == "http://localhost:7054"
    assert first["msp_dir"] == net_dir / "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp"
    assert first["tls_dir"] == net_dir / "organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/tls"
    assert second["ca_url"] == "http://localhost:8054"
    assert second["peer"] == "peer0.org2.example.com:9051"
