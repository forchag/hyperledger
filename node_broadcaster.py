import os
import socket
import requests

APP_URL = os.environ.get("APP_URL", "https://localhost:8443")
NODE_ID = os.environ.get("NODE_ID", "node")
NODE_PORT = int(os.environ.get("NODE_PORT", "8000"))


def _local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = socket.gethostbyname(socket.gethostname())
    finally:
        s.close()
    return ip


def broadcast() -> None:
    data = {"id": NODE_ID, "ip": _local_ip(), "port": NODE_PORT}
    try:
        requests.post(f"{APP_URL}/announce", json=data, timeout=5, verify=False)
        print(f"Announced {NODE_ID} at {data['ip']}:{NODE_PORT}")
    except Exception as exc:
        print(f"Failed to announce: {exc}")


if __name__ == "__main__":
    broadcast()
