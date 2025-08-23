# Five-Tier System Architecture (Per-Tier Diagrams)

Each tier now has its own standalone Mermaid diagram for readability. Tier 1 and Tier 2 include Data Schemas with explicit sensor fields and CRT budget rules, while Tier 4 includes a Consensus & Block Policy justification section per reviewer feedback.

## Index

- [Tier 1 (ESP32 & Sensors)](#tier-1--esp32--sensors-standalone-diagram--data-schemas--crt-budget)
- [Tier 2 (Pi Ingress & Bundler)](#tier-2-pi-ingress--bundler)
- [Tier 3 (Mesh/Link)](#tier-3-meshlink)
- [Tier 4 (Hyperledger Fabric)](#tier-4-hyperledger-fabric)
- [Tier 5 (Observability & Ops)](#tier-5-observability--ops)

## Tier 1 — ESP32 & Sensors (Standalone Diagram + Data Schemas + CRT Budget)

Purpose & cadence. Tier 1 reads local sensors at a fixed interval (e.g., every few minutes), builds a compact windowed summary, and sends it to the nearest Raspberry Pi gateway. The leaf favors small packets with statistics and optional event flags to keep radio use and power low.

Coverage planning. The number of leaf nodes depends on farm surface area and radio range; using CRT can increase the need for secondary/relay nodes (processing/memory trade-offs).

Mathematically, each sensor \(s\) produces a time series of readings \(x_s(t)\). Over a sampling window \(W\) with \(|W|\) samples, the node derives
\[
\text{avg}_s = \frac{1}{|W|} \sum_{t\in W} x_s(t),\qquad
\text{min}_s = \min_{t\in W} x_s(t),\qquad
\text{max}_s = \max_{t\in W} x_s(t),
\]
\[
\text{std}_s = \sqrt{\frac{1}{|W|}\sum_{t\in W} (x_s(t)-\text{avg}_s)^2},\qquad
\text{count}_s = |W|.
\]
The statistics for sensor \(s\) form the tuple \(S_s=(\text{min}_s,\text{avg}_s,\text{max}_s,\text{std}_s,\text{count}_s)\), which is encoded in the outgoing payload.


```mermaid
flowchart LR
  subgraph Farm_Plot["ESP32 Plot (~500 m²)"]
    direction LR
    subgraph Tier_1_ESP32_Leaf
      direction LR
      ESP32(("ESP32 Controller\nwindowed stats\n≤100B payload")):::device

      subgraph ENV["Environmental Sensors"]
        direction TB
        DHT22[["DHT22 Sensor"]]:::sensor
        SOIL[["Soil Moisture Probe"]]:::sensor
        PH[["pH Sensor"]]:::sensor
        LIGHT[["Light Sensor"]]:::sensor
        WATER[["Water Level Sensor"]]:::sensor
      end

      subgraph SYS["System Monitors"]
        direction TB
        BAT[["Battery Monitor"]]:::battery
        RSSI[["LoRa Radio"]]:::link
      end

      DHT22 --> TEMP(("temperature_c")):::reading --> ESP32
      DHT22 --> HUM(("humidity_rh")):::reading --> ESP32
      SOIL --> MOIST(("soil_moisture_vwc")):::reading --> ESP32
      PH --> PH_R(("soil_ph")):::reading --> ESP32
      LIGHT --> LUX(("light_lux")):::reading --> ESP32
      WATER --> LEVEL(("water_level_cm")):::reading --> ESP32
      BAT --> VBAT(("battery_v")):::reading --> ESP32
      RSSI --> RSSI_R(("rssi_dbm")):::reading --> ESP32
    end
  end

  ESP32 -->|compact window| PI_GW["Raspberry Pi Gateway"]:::device
  ESP32 --- CRT_NOTE
  ESP32 --- COV

  CRT_NOTE[CRT residues when\npayload > budget]:::note
  COV[Coverage planning:\n~500 m² per ESP32\nFarm area ↔ Node count]:::note

  classDef device fill:#e0f7fa,stroke:#006064,color:#00363a;
  classDef sensor fill:#fff3e0,stroke:#ef6c00,color:#e65100;
  classDef battery fill:#fffde7,stroke:#fbc02d,color:#f57f17;
  classDef link fill:#e8eaf6,stroke:#303f9f,color:#1a237e;
  classDef reading fill:#e0f2f1,stroke:#004d40,color:#00251a;
  classDef note fill:#eeeeee,stroke:#616161,color:#212121;
```


### Leaf → Pi Payload (with actual sensor data)

Envelope (IDs & timing)

- device_id (string/bytes): unique leaf identifier  
- seq (uint32): monotonic packet sequence  
- window_id (uint32): sliding/rolling window identifier  
- last_ts (uint64): last sample timestamp (epoch ms)

Sensor set (environmental & system vitals) — include all that apply

- temperature_c (°C)  
- soil_moisture_vwc (% volumetric water content)  
- humidity_rh (% relative humidity)  
- soil_ph (pH, unitless)  
- light_lux (lux)
- battery_v (V battery voltage)
- rssi_dbm (dBm, link quality during last uplink)
- water_level_cm (cm water level)

For each sensor in sensor_set, embed windowed statistics in stats:  
{min, avg, max, std, count} (numeric, fixed-point or scaled int). This preserves trends but keeps packets small.

Event & control flags

- urgent (bool/bitfield): fast-path submit for threshold breaches (e.g., temp high, moisture low).

Optional CRT residues (size relief)

- crt: { m[], r[] }: residues r_i = x mod m_i for selected large numeric fields when the payload risks exceeding the byte budget; moduli m[] are pairwise coprime and their product covers the numeric range; the Pi recombines via Garner’s algorithm.

Integrity

- sig (Ed25519 or HMAC) over the envelope + stats (protects integrity/identity using the device registry).

#### Example JSON (illustrative)

```json
{
  "device_id": "leaf-13",
  "seq": 4821,
  "window_id": 109,
  "last_ts": 1693212345678,
  "sensor_set": ["temperature_c","soil_moisture_vwc","humidity_rh","soil_ph","light_lux","water_level_cm","battery_v","rssi_dbm"],
  "stats": {
    "temperature_c": {"min": 24.1, "avg": 25.7, "max": 27.8, "std": 0.6, "count": 36},
    "soil_moisture_vwc": {"min": 23.0, "avg": 24.4, "max": 26.9, "std": 0.8, "count": 36},
    "humidity_rh": {"min": 58.2, "avg": 61.0, "max": 63.4, "std": 1.1, "count": 36},
    "soil_ph": {"min": 6.2, "avg": 6.3, "max": 6.4, "std": 0.05, "count": 36},
    "light_lux": {"min": 1200, "avg": 2400, "max": 4000, "std": 500, "count": 36},
    "water_level_cm": {"min": 42, "avg": 48, "max": 55, "std": 3.2, "count": 36},
    "battery_v": {"min": 3.78, "avg": 3.81, "max": 3.84, "std": 0.02, "count": 36},
    "rssi_dbm": {"min": -86, "avg": -78, "max": -72, "std": 3.1, "count": 6}
  },
  "urgent": false,
  "sig": "<64B>"
}
```

### Byte-Budget & CRT (When/Why)

Define a target payload budget (e.g., ≤ ~100 B) and compute it from the actual fields above (IDs/timestamps + N sensors × 5 stats + signature + flags). If the computed size for a given window exceeds the budget, enable `crt{m[], r[]}` for selected large numeric groups (e.g., multi-field stats), choosing moduli so that the product covers their range; Pi recombines to canonical values before bundling and Merkle hashing. This answers “How is the budget established to enable CRT?” → by summing concrete field sizes and switching CRT only when the sum exceeds the set budget. The choice can influence secondary/relay node planning due to processing/memory trade-offs.

CRT is **optional**: if the calculated size remains under the budget, the node omits the `crt` field and transmits canonical integers directly. When the window threatens to overflow the limit (e.g., many sensors or high‑precision counts), the node selects pairwise coprime moduli \(m_i\) (e.g., \(97,101,103\)) whose product covers the numeric range and sends residues \(r_i = x \bmod m_i\). The Pi reconstructs \(x\) using the Chinese Remainder Theorem—typically via Garner’s algorithm—verifies that \(x < \prod m_i\), and restores the original integer before computing the Merkle hash. Thus CRT reduces wire size without changing the deterministic value hashed into the tree or seeding the blockchain.

### Hand-off to Tier 2

The leaf transmits the compact window summary (and any urgent events) to the nearest Pi gateway, which verifies/deduplicates and stages by `window_id` for bundling and Merkle-root computation downstream.

For each payload \(P_i\) the gateway computes a cryptographic hash
\[ h_i = H(P_i) \]
using a function such as SHA-256, yielding the Merkle tree leaves. Hashes are paired and folded iteratively,
\[ h_{i,j} = H(h_{2i} \Vert h_{2i+1}) \]
until a single root \(R\) remains. The inaugural root \(R_0\) seeds the ledger by forming the first block \(B_0=(R_0, t_0)\), and each subsequent window contributes a new root \(R_k\) appended as block \(B_k\). This process both compacts Tier 1 data and begins the blockchain.

### Reviewer alignment (Tier 1)

- Actual sensor data explicitly listed (temperature, soil moisture, humidity, pH, light, water level, battery, RSSI) → fixes the payload gap.
- Node counts & CRT note included for planning and readability.  
- CRT budget clearly defined and justified.

## Tier 2 (Pi Ingress & Bundler)

Role. Tier 2 is the gateway that receives leaf packets, verifies and de-duplicates them, stages per time window, and assembles bundles for downstream commit. It submits bundles on a schedule and immediately for events.

---

1) **Ingress (verify → dedupe → stage)**
- **Packet verification & identity.** Validate message structure and the device identity; verify HMAC/Ed25519 signatures using the device registry that maps `device_id → key_id`.
- **De-duplication.** Drop repeats (e.g., using `device_id + seq/window_id` as an idempotency key) and keep a counter for duplicates; only clean, unique records proceed to staging.
- **Window staging.** Organize valid readings by `window_id` into queues on disk so that the Bundler can efficiently build a periodic `IntervalBundle` for that window.

*Ops/metrics exposure.* Gateways expose `/healthz`, `/readyz`, and `/metrics` so Tier 5 can scrape packet counts/latency/system load from Tier 2.

---

2) **Bundler (build → hash → forward)**

Tier 2 produces two bundle types (define them concretely in the doc so they're unambiguous):

- **IntervalBundle** — periodic summaries for a time window  
  `bundle_id`, `window_id`, `readings[]`, `created_ts`, `count`, `merkle_root`
- **EventBundle** — immediate submits for thresholded/urgent events  
  `bundle_id`, `events[{device_id, ts, type, before[], after[], thresholds}]`, `created_ts`, `merkle_root`

*Merkle root (bundle proof).* For each bundle, hash each item (reading/event), build the tree, and record the Merkle root inside the bundle. Tier 4 (Fabric) stores summary + `merkle_root`; later, any raw item can be proven with a Merkle path instead of storing all raw data on-chain.

*Cadence & triggers.* The scheduler submits periodic bundles every 30–120 min, and event bundles immediately; this choice directly impacts end-to-end latency vs. storage trade-offs that should be justified with measurements/plots.

*Failure handling (CRT edge cases).* When upstream uses CRT at Tier 1, recombine residues at the Pi via Garner’s algorithm; if some item can't be reconstructed, mark that record invalid (log reason) but continue others, and prefer canonical (recovered) values for Merkle hashing so proofs align with on-chain roots.

---

3) **On-chain mapping (how Tier 2 output is stored/indexed)**

- **Key patterns.**
  - `reading:device_id:window_id` → summary stats (+ proof hash/`merkle_root`)
  - `event:device_id:ts` → event details  
    Rationale: store summaries to keep the ledger compact; rely on Merkle proofs to recover/verify raw items when needed.
- **Handoff to Tier 4.** Bundler acts as the client that submits transactions to Fabric; ordering/commit latency and block timing are governed in Consensus & Block Policy (Tier 4), which should be defined and justified (`BatchTimeout`, orderer count, latency bands).

---

4) **Tier-2 gateway diagram**

```mermaid
flowchart TB
  %% ========= TIER 2: PI GATEWAY =========
  subgraph T2["Tier 2 — Raspberry Pi Gateway\n(Ingest • Verify • Bundle • Schedule)"]
    direction TB

    %% Ingress pipeline
    subgraph IN["Ingress"]
      direction TB
      REG["DeviceRegistry\n(device_id → key_id)"]:::data
      VER["Verify HMAC/Ed25519\n/metrics: ingress_packets_total, ingress_latency_seconds"]:::proc
      DEDUPE["De-duplicate\n(device_id + seq/window)\n/metrics: duplicates_total"]:::proc
      CRT["CRT recombination (Garner)\n(recover canonical values)"]:::proc
      STAGE["Stage by window_id"]:::proc
      DROP["Drop invalid/failed\n/metrics: drops_total"]:::proc

      REG --> VER
      VER --> DEDUPE --> CRT --> STAGE
      VER -- fail --> DROP
      CRT -- fail --> DROP
    end

    %% Bundle creation
    subgraph BD["Bundler"]
      direction TB
      BUILD["Assemble Interval/Event Bundles"]:::proc
      HASH["Compute merkle_root\n/metrics: bundle_latency_seconds"]:::proc
      BUILD --> HASH
    end

    %% Durable queue with retries
    subgraph SF["Store & Forward"]
      direction TB
      QUEUE["Durable queue (STORE_DIR)\n/metrics: store_backlog_files"]:::box
      RETRY["Retry with backoff + jitter"]:::box
      QUEUE --> RETRY
    end

    %% Submission scheduling
    subgraph SCH["Scheduler"]
      direction TB
      COAL["Event coalesce 60–120 s\nRate-limit ≤ 6/h\n/metrics: events_rate_limited_total"]:::proc
      INTERVAL["Interval submit (30–120 min)"]:::proc
      EVENT["Event submit (immediate)"]:::proc
    end

    %% Flow between groups
    STAGE --> BUILD
    HASH --> QUEUE
    RETRY --> COAL
    COAL --> EVENT
    RETRY --> INTERVAL

    %% Merkle hashing and Fabric submit
    MR["Merkle Tree\nleaf: item hash → root: merkle_root"]:::proc
    HASH --> MR

    TX["Fabric client submit\n(summary + merkle_root)"]:::proc
    INTERVAL --> TX
    EVENT --> TX

    %% Bundle schemas (make merkle_root explicit)
    IB["IntervalBundle fields:\n{bundle_id, window_id, readings[], created_ts, count, merkle_root}"]:::data
    EB["EventBundle fields:\n{bundle_id, events[{device_id, ts, type, before[], after[], thresholds}], created_ts, merkle_root}"]:::data
    HASH --> IB
    HASH --> EB

    %% On-chain mapping (what Tier 4 stores/indexes)
    ONCHAIN["On-chain keys:\nreading:device_id:window_id → summary + merkle_root\nevent:device_id:ts → event details"]:::data
    TX --> ONCHAIN

    %% Ops endpoints
    OPS["Ops endpoints exposed:\n/healthz  /readyz  /metrics"]:::data
  end

  %% Styles
  classDef box fill:#fff8e1,stroke:#ff8f00,color:#4e342e;
  classDef proc fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
  classDef data fill:#eeeeee,stroke:#616161,color:#212121;
```

---

5) **Reviewer emphasis**

- Clear Tier-2 responsibilities: verify, de-dup, stage, bundle, Merkle, forward.
- Bundle schemas defined with `merkle_root` explicitly present.
- Cadence is critical: periodic 30–120 min vs. immediate events → justify values with data (latency/storage trade-offs).
- Architecture ↔ Merkle linkage shown (where the root is produced and how it's used on-chain).



## Tier 3 (Mesh/Link)

```mermaid
flowchart TB
  %% ========= TIER 3: MESH NETWORK =========
  subgraph T3["Tier 3 — Pi⇄Pi Mesh Network\n(WokFi directional links + BATMAN-adv L2 + WireGuard overlay)"]
    direction TB

    %% Mesh interfaces on Pis
    P1["Pi #1\nbat0 + wg0"]:::pi -->|"ETX≈1.2 • RSSI≈-65 dBm"| P2["Pi #2\nbat0 + wg0"]:::pi -->|"ETX≈1.4 • RSSI≈-70 dBm"| P3["Pi #3\nbat0 + wg0"]:::pi -->|"ETX≈1.3 • RSSI≈-68 dBm"| GW["Gateway Pi\nbat0 + wg0"]:::pi

    %% Self-healing / reroute behavior
    FAIL["Link down or ETX↑\n→ auto reroute (few ms/hop)"]:::proc
    P2 -. monitor .- FAIL
    P3 -. monitor .- FAIL

    %% Mesh monitoring & metrics
    MON["MeshMonitor (batctl + exporters)\n• neighbors • ETX • path changes • flaps\n/metrics: mesh_neighbors, mesh_retries_total,\nmesh_rssi_avg, per_hop_latency_ms"]:::obs
    MON --- P1
    MON --- P2
    MON --- P3
    MON --- GW
  end

  %% Styles
  classDef pi fill:#fff8e1,stroke:#ff8f00,color:#4e342e;
  classDef proc fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
  classDef obs fill:#fce4ec,stroke:#ad1457,color:#880e4f;
```

- Topology & radio planning. Use directional links (“WokFi” or equivalent) to increase SNR and extend range between Pis; plan node spacing so the expected hop count keeps end-to-end delay within your cadence target. The mesh should tolerate single-link failures without violating latency SLOs.
- Protocol stack. Radios run WPA2/3; BATMAN-adv provides Layer-2 meshing and path selection via ETX; WireGuard encrypts payloads end-to-end across bat0.
- Performance targets. Document measured per-hop latency (aim “few ms per hop”), packet delivery ratio, route-flap rate, and jitter under varying traffic. These feed the thesis-level QoS trade-offs the reviewer asked for.
- Metrics to export. mesh_neighbors, mesh_retries_total, mesh_rssi_avg, per_hop_latency_ms, and path_change_total (or equivalent) for Grafana.
- Failure modes. Show how the mesh re-routes when a link’s ETX rises or RSSI falls; log an alert if ETX stays above a threshold for N windows to force maintenance.

## Tier 4 (Hyperledger Fabric)

## Tier 5 (Observability & Ops)

