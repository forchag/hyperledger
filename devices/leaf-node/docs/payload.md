# ESP32 Payload Schema

Leaf nodes publish aggregated sensor windows to Raspberry Pi gateways using the
following JSON structure:

```json
{
  "device_id": "<string>",
  "seq": <integer>,
  "window_id": <integer>,
  "stats": {
    "min": <number>,
    "avg": <number>,
    "max": <number>,
    "std": <number>,
    "count": <integer>
  },
  "last_ts": <integer>,
  "sensor_set": ["<sensor id>", ...],
  "urgent": <boolean>,
  "crt": {
    "m": [<int>, ...],
    "r": [<int>, ...]
  },
  "sig": "<base64 signature>"
}
```

* `device_id` – unique identifier for the ESP32 leaf node.
* `seq` – monotonically increasing sequence number used for deduplication.
* `window_id` – identifier for the aggregation window.
* `stats` – windowed statistics for the sensor readings.
* `last_ts` – epoch timestamp of the most recent sample in the window.
* `sensor_set` – list of sensors included in the payload.
* `urgent` – signals that the payload contains threshold breaches and should
  be processed immediately.
* `crt` – optional Chinese Remainder Theorem values supporting polynomial commitments.
* `sig` – authentication tag or signature over the payload.

