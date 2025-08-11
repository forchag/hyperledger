import json
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from flask_app.hlf_client import record_sensor_data, register_device

GPIO_PINS = [4, 17, 27, 22, 5, 6, 13, 19, 26, 18, 23, 24, 25, 12, 16, 20, 21]


def _simulate_sensor(sensor_id: str, node_id: str, gpio_pin: int) -> None:
    """Send periodic fake readings for a single sensor."""
    register_device(sensor_id, node_id)
    while True:
        temperature = round(random.uniform(10, 35), 2)
        humidity = round(random.uniform(30, 90), 2)
        soil_moisture = round(random.uniform(20, 80), 2)
        ph = round(random.uniform(5.5, 7.5), 2)
        light = round(random.uniform(200, 800), 2)
        water_level = round(random.uniform(0, 100), 2)
        ts = datetime.utcnow().isoformat()
        record_sensor_data(
            sensor_id,
            temperature,
            humidity,
            soil_moisture,
            ph,
            light,
            water_level,
            ts,
            {"gpio": gpio_pin, "simulated": True},
        )
        print(
            f"{sensor_id} GPIO{gpio_pin} -> T:{temperature} H:{humidity} "
            f"Soil:{soil_moisture} pH:{ph} Light:{light} Water:{water_level}"
        )
        time.sleep(5)


def build_mapping(config: dict) -> dict:
    """Return mapping of nodes to sensors and GPIO pins.

    Exposed as a public function so the web application can reuse the same
    logic when presenting GPIO assignments to the user before launching the
    simulator.
    """
    mapping = {}
    for node in config.get("nodes", []):
        node_id = node.get("id")
        sensors = {}
        for idx, sensor in enumerate(node.get("sensors", [])):
            gpio = GPIO_PINS[idx % len(GPIO_PINS)]
            sensors[sensor] = gpio
        mapping[node_id] = sensors
    return mapping


def main() -> None:
    if len(sys.argv) > 1:
        cfg_path = Path(sys.argv[1])
        config = json.loads(cfg_path.read_text())
    else:
        nodes = int(input("How many nodes? "))
        config = {"nodes": []}
        for i in range(nodes):
            sensors = (
                input(f"Enter sensors for node {i + 1} (comma separated): ")
                .split(",")
            )
            config["nodes"].append(
                {
                    "id": f"node{i + 1}",
                    "sensors": [s.strip() for s in sensors if s.strip()],
                }
            )
    mapping = build_mapping(config)
    print("GPIO mapping:")
    print(json.dumps(mapping, indent=2))

    threads = []
    for node_id, sensors in mapping.items():
        for sensor_name, gpio_pin in sensors.items():
            sensor_id = f"{node_id}_{sensor_name}"
            t = threading.Thread(
                target=_simulate_sensor,
                args=(sensor_id, node_id, gpio_pin),
                daemon=True,
            )
            t.start()
            threads.append(t)

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
