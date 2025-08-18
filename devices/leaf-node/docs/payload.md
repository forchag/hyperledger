# ESP32 Payload Schema

Leaf nodes publish aggregated sensor windows to Raspberry Pi gateways using the
following JSON structure:

```json
{
  "device_id": "<string>",
  "seq": <integer>,
  "window_id": [<start_ts>, <end_ts>],
  "stats": {
    "min": <number>,
    "avg": <number>,
    "max": <number>,
    "std": <number>,
    "count": <integer>
  },
  "last_ts": <integer>,
  "tail": [<number>, ...],
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
* `window_id` – `[start_ts, end_ts]` pair identifying the aggregation window
  aligned to the configured uplink period.
* `stats` – windowed statistics for the sensor readings.
* `last_ts` – epoch timestamp of the most recent sample in the window.
* `tail` – optional raw tail of recent readings for diagnostics.
* `sensor_set` – list of sensors included in the payload.
* `urgent` – signals that the payload contains threshold breaches and should
  be processed immediately.
* `crt` – optional Chinese Remainder Theorem values supporting polynomial commitments.
* `sig` – authentication tag or signature over the payload.

