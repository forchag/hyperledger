````markdown
# Figure — Full Communication Scheme (ESP32 ↔ Pi ↔ Mesh ↔ Fabric ↔ Observability)

> Copy this whole file into your repo (e.g., `figure_comm_all_nodes.md`).  
> ASCII only (no special bullets/arrows) so GitHub’s Mermaid renders cleanly.

---

## End-to-end sequence (periodic and event flows)

```mermaid
sequenceDiagram
    autonumber
    participant ESP32 as ESP32 Node
    participant PI as Pi (Wi-Fi AP)
    participant INGRESS as IngressService
    participant BUNDLER as Bundler
    participant SCHED as Scheduler
    participant MESH as Mesh (BATMAN-adv + WireGuard)
    participant ORDERER as Fabric Orderer (Raft)
    participant PEERS as Fabric Peers
    participant CC as Chaincode
    participant METRICS as Metrics Exporter
    participant PROM as Prometheus
    participant DASH as Dashboard
    participant ALERTS as Alertmanager
    participant OP as Operator

    Note over ESP32: Sample sensors every 1-5 min. Detect thresholds and delta-rate events. Maintain monotonic seq.
    ESP32->>PI: Leaf payload {device_id, seq, window_id, stats, last_ts, sensor_set, urgent, [crt?], sig}<br/>Wi-Fi WPA2/3
    PI-->>ESP32: ACK or keepalive (optional commands)
    Note over ESP32,PI: HMAC or Ed25519 signature. Optional CRT residues at leaf.

    PI->>INGRESS: Forward payload (local)
    INGRESS->>INGRESS: Verify signature, dedupe (device_id, seq), reconstruct CRT (Garner) if present
    INGRESS->>BUNDLER: NormalizedReading

    alt Periodic window
        BUNDLER->>SCHED: Interval bundle (window 30-120 min)
        SCHED->>MESH: Submit bundle on cadence (gRPC over TLS, tunneled via WireGuard)
    else Event flow
        BUNDLER->>SCHED: Event bundle (coalesce 60-120 s, rate limit)
        SCHED->>MESH: Submit bundle immediately (gRPC over TLS)
    end

    Note over MESH: L2 routing via BATMAN-adv on bat0. 2-5 ms per hop. Tens of Mbps with WokFi links.
    MESH->>ORDERER: Fabric envelope to orderer cluster (Raft)
    ORDERER->>PEERS: Ordered block broadcast
    PEERS->>CC: Endorse-validate-commit (chaincode invoked)
    CC-->>PEERS: Chaincode events emitted

    PEERS->>METRICS: Increment counters and gauges on commit
    METRICS->>PROM: Expose /metrics for scraping (HTTP pull)
    PROM->>DASH: Render graphs and tables (15s scrape)
    PROM->>ALERTS: Fire alerts on rules (latency, backlog, health)
    ALERTS->>OP: Notify (email or webhook)
    DASH->>OP: Visualization and drilldowns

    Note over SCHED,PEERS: After submit, wait for commit event; do read-back verification of one key; log submit_to_commit latency.
````

---

## What is transmitted (by hop)

| Hop                        | Protocol or Layer                                    | Message / Fields                                                                                               |                 Size target | Timing                                                     | Reliability (retry / SOF)                       |
| -------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | --------------------------: | ---------------------------------------------------------- | ----------------------------------------------- |
| ESP32 -> Pi                | Wi-Fi (WPA2/3), HTTP or MQTT (LAN)                   | `{device_id, seq, window_id, stats{min,avg,max,std,count}, last_ts, sensor_set, urgent, [crt{m[],r[]}] , sig}` |            <= 100 B typical | Every 10-15 min and/or at window close; immediate on event | ESP32 retries; rotate pi\_targets\[] on failure |
| Pi -> ESP32                | Wi-Fi                                                | ACK / optional control (sample\_period, thresholds)                                                            |                      < 50 B | Immediate                                                  | 802.11 retry                                    |
| Pi -> Ingress              | Loopback (process boundary)                          | Same payload                                                                                                   |                     \~100 B | Immediate                                                  | N/A                                             |
| Ingress -> Bundler         | In-memory                                            | NormalizedReading (verified, deduped, CRT reconstructed)                                                       |                     \~150 B | Immediate                                                  | N/A                                             |
| Bundler -> Scheduler       | In-memory                                            | IntervalBundle or EventBundle metadata                                                                         |                      \~1 KB | 30-120 min (interval) ; 60-120 s coalesce (event)          | N/A                                             |
| Scheduler -> Mesh          | gRPC over TLS (WireGuard tunnel), IP over BATMAN-adv | Serialized bundle `{bundle_id, window_id, readings[], created_ts, count, residues_hash or MerkleRoot}`         |           50-100 KB typical | Cadence or immediate                                       | Store-and-forward on Pi; exponential backoff    |
| Mesh -> Orderer            | L2 (BATMAN-adv), then TCP to Fabric ports            | Fabric envelope (proposal, endorsements)                                                                       |            \~100 KB typical | Cadence or immediate                                       | Mesh reroute; TCP retry                         |
| Orderer -> Peers           | Raft + gRPC                                          | Ordered block `{prev_hash, merkle_root, ts}`                                                                   | <= 1 MB (PreferredMaxBytes) | Immediate after submit                                     | Fabric-level retry                              |
| Peers -> Chaincode         | gRPC                                                 | Tx proposal and state updates                                                                                  |                      \~1 KB | Immediate                                                  | Fabric                                          |
| Peers -> Metrics           | Local exporter                                       | Counters and gauges                                                                                            |                        text | On commit                                                  | N/A                                             |
| Metrics -> Prometheus      | HTTP pull                                            | `/metrics` exposition format                                                                                   |                        text | 15s scrape (configurable)                                  | HTTP retry                                      |
| Prometheus -> Dashboard    | HTTP or WebSocket                                    | Rendered charts/tables                                                                                         |                   text/JSON | On demand                                                  | HTTP retry                                      |
| Prometheus -> Alertmanager | HTTP                                                 | Alert JSON                                                                                                     |                       small | On rule trigger                                            | HTTP retry                                      |
| Alertmanager -> Operator   | Email/Webhook                                        | Notification                                                                                                   |                        text | On alert                                                   | Transport retry                                 |

Notes:

* Interval cadence (30-120 min) set in gateway config. Event coalesce window 60-120 s to merge bursts.
* Size targets are typical with summaries; use CRT when payload risks exceeding budget.

---

## Merkle tree for bundles (interval and event)

```mermaid
flowchart TB
  %% Styles
  classDef leaf fill:#E6FFF2,stroke:#00A86B,color:#064e3b,stroke-width:1px;
  classDef inner fill:#F1F8FF,stroke:#1E66F5,color:#0f3a8a,stroke-width:1px;
  classDef root fill:#FDF0FF,stroke:#9D4EDD,color:#3e1a6d,stroke-width:2px;
  classDef note fill:#FFFBE6,stroke:#C9A227,color:#5a4a00,stroke-dasharray:4 3;

  T["Merkle Tree for Interval/Event Bundles"]:::note

  I0["Item0 (reading or raw chunk)"]:::leaf --> H0["h0 = H(serialize(Item0))"]:::leaf
  I1["Item1"]:::leaf --> H1["h1 = H(serialize(Item1))"]:::leaf
  I2["Item2"]:::leaf --> H2["h2 = H(serialize(Item2))"]:::leaf
  I3["Item3"]:::leaf --> H3["h3 = H(serialize(Item3))"]:::leaf
  I4["Item4"]:::leaf --> H4["h4 = H(serialize(Item4))"]:::leaf
  I5["Item5"]:::leaf --> H5["h5 = H(serialize(Item5))"]:::leaf
  I6["Item6"]:::leaf --> H6["h6 = H(serialize(Item6))"]:::leaf
  I7["Item7"]:::leaf --> H7["h7 = H(serialize(Item7))"]:::leaf

  H0 --> H01["h01 = H(h0 || h1)"]:::inner
  H1 --> H01
  H2 --> H23["h23 = H(h2 || h3)"]:::inner
  H3 --> H23
  H4 --> H45["h45 = H(h4 || h5)"]:::inner
  H5 --> H45
  H6 --> H67["h67 = H(h6 || h7)"]:::inner
  H7 --> H67

  H01 --> H0123["h0123 = H(h01 || h23)"]:::inner
  H23 --> H0123
  H45 --> H4567["h4567 = H(h45 || h67)"]:::inner
  H67 --> H4567

  H0123 --> ROOT["MerkleRoot = H(h0123 || h4567)"]:::root
  H4567 --> ROOT

  N1["Hash: H = SHA-256 (or project-selected). Internal nodes H(left || right). Leaves H(serialize(item))."]:::note
  N2["Odd leaves: if count is odd, duplicate last leaf: H(hN || hN)."]:::note
  N3["On-chain: store MerkleRoot in block header or bundle metadata (residues_hash or MerkleRoot)."]:::note
  N4["Context: each Interval bundle (30-120 min) and each Event bundle yields a root."]:::note
  N5["CRT: residues at leaf level are recombined on Pi before hashing so Merkle covers canonical values."]:::note

  T -.-> N1
  ROOT -.-> N3
  H7 -.-> N2
  H0123 -.-> N4
  I0 -.-> N5
```

### Merkle proof table (path verification details)

| Field            | Description                                      | Example / Notes                                                                                   |   |                       |   |       |
| ---------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------- | - | --------------------- | - | ----- |
| hash\_algo       | Hash function used                               | SHA-256 (default), SHA3-256 if specified                                                          |   |                       |   |       |
| leaf\_encoding   | How a leaf is serialized before hashing          | Canonical JSON of item, sorted keys, UTF-8, no whitespace; or protobuf if defined                 |   |                       |   |       |
| leaf\_hash       | H(serialize(item))                               | h0, h1, ...                                                                                       |   |                       |   |       |
| path             | Ordered list of sibling hashes from leaf to root | `[sibling_0, sibling_1, ...]`                                                                     |   |                       |   |       |
| path\_dir        | Direction of each concat at each level           | `["LEFT","RIGHT",...]` meaning H(this                                                             |   | sibling) or H(sibling |   | this) |
| root             | Expected MerkleRoot from bundle or block header  | `0xabc...`                                                                                        |   |                       |   |       |
| verify\_steps    | Deterministic recomputation procedure            | Start with leaf\_hash, fold siblings using path\_dir, compare final to root                       |   |                       |   |       |
| odd\_leaf\_rule  | Handling odd number of leaves                    | Duplicate last hash to make a pair at that level                                                  |   |                       |   |       |
| bundle\_meta     | Where root is recorded                           | Bundle metadata field `MerkleRoot` or `residues_hash`; also embedded in block header merkle\_root |   |                       |   |       |
| canonicalization | When CRT is used                                 | Recombine residues on Pi (Garner) to get canonical numeric x before hashing                       |   |                       |   |       |
| security         | Integrity scope                                  | Proof establishes membership of item in bundle committed on-chain                                 |   |                       |   |       |

---

## Size and timing references

* Interval bundle size: 50-100 KB typical (summaries only).
* Block max payload (PreferredMaxBytes): about 1 MB.
* Submit to commit latency after submit: 1-2 s (2 Pis), 3-5 s (20 Pis), 10-15 s (100 Pis).
* Mesh latency: 2-5 ms per hop.

---
Here’s the **continuation and enhancement** you can drop directly into your GitHub `.md` file. It expands your earlier diagram + table with **Merkle Tree details**, **energy/communication evaluation diagrams**, and a **metrics interpretation section**.

---

# Figure — Merkle Tree for Sensor Data Integrity

```mermaid
graph TD
    subgraph Leaf Level
        A1[ESP32+Sensor Reading 1<br/>{device_id, seq, stats, ts, sig}]
        A2[ESP32+Sensor Reading 2<br/>{device_id, seq, stats, ts, sig}]
        A3[ESP32+Sensor Reading 3<br/>{device_id, seq, stats, ts, sig}]
        A4[ESP32+Sensor Reading 4<br/>{device_id, seq, stats, ts, sig}]
    end

    subgraph Hashing
        H1[H(Reading1)]
        H2[H(Reading2)]
        H3[H(Reading3)]
        H4[H(Reading4)]
    end

    subgraph Internal Nodes
        P1[Parent 1<br/>= H(H1+H2)]
        P2[Parent 2<br/>= H(H3+H4)]
    end

    subgraph Root
        MR[Merkle Root<br/>= H(P1+P2)]
    end

    A1-->H1
    A2-->H2
    A3-->H3
    A4-->H4
    H1-->P1
    H2-->P1
    H3-->P2
    H4-->P2
    P1-->MR
    P2-->MR
```

**Explanation**

* **Leaf nodes** = individual ESP32 sensor readings (temperature, humidity, soil moisture, etc.).
* Each leaf is **hashed** with SHA-256.
* **Internal nodes** combine child hashes.
* The **Merkle Root** is committed to the blockchain block header, ensuring any tampering of readings is detectable.

---

# Figure — Evaluation Diagram for Energy & Communication Metrics

```mermaid
flowchart LR
    S1[ESP32 Node] -->|Tx: Wi-Fi (100B / 60s)| P1[Pi Gateway]
    P1 -->|Bundle 100 readings (~10KB)| M1[Mesh Network]
    M1 -->|Hop to orderer<br/>(~100KB / 30min)| F1[Fabric Orderer]
    F1 -->|Raft Block<br/>Merkle Root| PEERS[Fabric Peers]
    PEERS --> CC[Chaincode]
    CC --> METRICS[Prometheus Exporter]

    subgraph Energy Profile
        ESP32E[ESP32 Avg Tx: 80mA] 
        PiE[Pi Avg Idle: 500mA]
        WiFiE[Wi-Fi burst: 120mA]
        LoRaE[LoRa burst: 40mA]
    end

    subgraph Comm Profile
        Lat[Latency: Wi-Fi ~50ms,<br/>LoRa ~2-3s]
        Thru[Throughput: Wi-Fi 100kbps–1Mbps,<br/>LoRa ~0.3kbps]
        Rel[Reliability: Wi-Fi retries,<br/>LoRa ACK-based]
    end
```

---

# Metrics Table — Energy vs Communication

| Metric            | ESP32 (Wi-Fi)          | ESP32 (LoRa)          | Pi Gateway        | Mesh BATMAN-adv    | Fabric Orderer/Peer |
| ----------------- | ---------------------- | --------------------- | ----------------- | ------------------ | ------------------- |
| **Avg Tx Energy** | \~80mA for 200ms burst | \~40mA for 1–2s burst | \~500mA constant  | \~100mA per hop    | \~1–2A server-grade |
| **Latency**       | 50–100ms               | 2–3s                  | <10ms local       | 10–100ms/hop       | \~1–2s block cut    |
| **Throughput**    | 0.1–1 Mbps             | 0.3 kbps              | 100 Mbps LAN      | Shared across hops | \~10–100 tx/s       |
| **Reliability**   | WPA2 retries           | LoRa ACK              | Stable LAN        | Routing resilient  | Raft consensus      |
| **Bundle Size**   | 100B/reading           | 50B/reading           | 10KB/100 readings | 50–100KB bundle    | 0.5–1MB block       |

---

# Interpretation

* **Wi-Fi (ESP32 → Pi)**: Higher throughput but higher energy consumption. Suitable for **dense plantation areas (500m² per Pi)**.
* **LoRa**: Ultra-low energy, but limited throughput. Better for **wide plantations with sparse data points**.
* **Pi Gateways**: Act as local bundlers, ensuring redundancy is removed before transmission.
* **Mesh (BATMAN-adv)**: Provides resilience against Pi failure; packets can reroute.
* **Fabric Layer**: Ensures immutability and consensus, with Merkle root anchoring sensor trust.


::contentReference[oaicite:0]{index=0}
```
