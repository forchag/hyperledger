# Figure 1 — Five-Tier System Architecture (ESP32 → Pi → Mesh → Fabric → Observability)

This diagram shows the **complete, self-contained farm ledger** with **periodic blocks (30–120 min)** and **event-triggered blocks (immediate)**.  
Tiers are color-separated; arrows label **what** is transmitted, **how**, and **when**.

```mermaid
flowchart LR
  %% ========= CLASSES / COLORS =========
  classDef tier1 fill:#E6FFF2,stroke:#00A86B,stroke-width:1px,color:#062;
  classDef tier2 fill:#F1F8FF,stroke:#1E66F5,stroke-width:1px,color:#123A7D;
  classDef tier3 fill:#FFF5E6,stroke:#FF8C00,stroke-width:1px,color:#7A3F00;
  classDef tier4 fill:#FDF0FF,stroke:#9D4EDD,stroke-width:1px,color:#3E1A6D;
  classDef tier5 fill:#FFF0F0,stroke:#D7263D,stroke-width:1px,color:#6B111B;
  classDef data fill:#FFFFFF,stroke:#999,stroke-dasharray: 3 3,color:#333;

  %% ========= TIER 1: ESP32 + SENSORS =========
  subgraph T1["Tier 1 — ESP32 + Sensors<br/>(Leaf Intelligence)"]
    direction TB
    SENSORS[[DHT22 • Light • pH • Soil Moisture • Water Level]]
    ESP32[ESP32 Node<br/>• Sampling 1–5 min<br/>• Rolling stats per window<br/>• Threshold & Δ-rate events<br/>• Monotonic seq<br/>• Optional CRT residues]
    SENSORS --> ESP32
  end
  class T1 tier1
  class SENSORS,ESP32 tier1

  %% ========= TIER 2: PI GATEWAY =========
  subgraph T2["Tier 2 — Raspberry Pi Gateway<br/>(Ingest • Verify • Bundle • Schedule)"]
    direction TB
    INGRESS[IngressService<br/>• Verify HMAC/Ed25519<br/>• Dedupe (device_id, seq)<br/>• CRT recombination (Garner)]
    BUNDLER[Bundler<br/>• IntervalBundle (30–120 min)<br/>• Event coalesce (60–120 s)<br/>• Rate-limit events]
    SOF[StoreAndForward<br/>• Durable queue in STORE_DIR<br/>• Retry with backoff]
    SCHED[Scheduler<br/>• Submit IntervalBundle on cadence<br/>• Submit EventBundle immediately]
    INGRESS --> BUNDLER --> SCHED
    BUNDLER --> SOF
  end
  class T2 tier2
  class INGRESS,BUNDLER,SOF,SCHED tier2

  %% ========= TIER 3: MESH (WokFi + BATMAN) =========
  subgraph T3["Tier 3 — Pi⇄Pi Mesh Network<br/>(WokFi Directional + BATMAN-adv L2 Mesh)"]
    direction TB
    MESH[Mesh (bat0)<br/>• Self-healing L2<br/>• 2–5 ms/hop • Tens of Mbps<br/>• WPA2/3 + WireGuard overlay]
    MON[MeshMonitor (batctl)<br/>• Neighbors • ETX • Path changes]
  end
  class T3 tier3
  class MESH,MON tier3

  %% ========= TIER 4: BLOCKCHAIN (FABRIC) =========
  subgraph T4["Tier 4 — Blockchain (Hyperledger Fabric)"]
    direction TB
    ORDERER[Orderer(s) — Raft<br/>• 1–3 nodes<br/>• Receives bundled tx]
    PEERS[Peers on Pis<br/>• Validate & Commit<br/>• CouchDB indexes (device, window, ts)]
    CC[Chaincode<br/>Keys:<br/>• reading:device_id:window_id → {min,avg,max,std,count,last_ts,residues_hash?,writer_msp}<br/>• event:device_id:ts → {type,before[],after[],thresholds,writer_msp}<br/>Guards:<br/>• last_seq:device_id • Idempotency]
    BLOCK[Block Structure<br/>• ~100 kB typical (summaries)<br/>• PreferredMaxBytes ≈ 1 MB<br/>• Merkle tree over tx set<br/>• Header {prev_hash, merkle_root, ts}]
  end
  class T4 tier4
  class ORDERER,PEERS,CC,BLOCK tier4

  %% ========= TIER 5: OBSERVABILITY / OPS =========
  subgraph T5["Tier 5 — Observability & Ops"]
    direction TB
    HEALTH[Health & Readiness<br/>• /healthz (mesh+pipeline)<br/>• /readyz (recent commit)]
    METRICS[Metrics (Prometheus)<br/>• ingress_packets_total<br/>• bundles_submitted_total{type}<br/>• submit_commit_seconds<br/>• mesh_neighbors, store_backlog_files]
    DASH[Dashboards / Explorer<br/>• Periodic state view<br/>• Event timeline]
  end
  class T5 tier5
  class HEALTH,METRICS,DASH tier5

  %% ========= DATA CHANNELS / LABELLED EDGES =========
  ESP32 -- "Wi-Fi client → Pi SSID\nPayload ≤ ~100 B\nPeriodic Summary (10–15 min) • Event Alert (immediate)\n{device_id, seq, window_id, stats, last_ts, urgent, crt?, sig}" --> INGRESS
  INGRESS -- "NormalizedRecord\n(sig OK • CRT→value • dedup OK)" --> BUNDLER
  SCHED -- "Submit IntervalBundle (every 30–120 min)\nSubmit EventBundle (immediate)" --> MESH
  MESH -- "gRPC over mesh (WireGuard recommended)\nLatency 2–5 ms/hop" --> ORDERER
  ORDERER -- "Ordered block" --> PEERS
  PEERS -- "Commit → Chaincode events" --> DASH
  PEERS -- "Commit events & read-back verify\nsubmit→commit latency" --> HEALTH
  PEERS -- "Metrics exporter" --> METRICS

  %% ========= NOTES =========
  note right of ESP32:::data
    CRT / Modular Arithmetic (optional):
    • Leaf packs large numbers as residues r_i = x mod m_i
    • Pi recombines via Garner to recover x
    • Saves airtime & memory on ESP32
  end

  note right of BLOCK:::data
    Block parameters:
    • Block size: ~100 kB typical (summaries); PreferredMaxBytes ≈ 1 MB
    • Consensus: Raft (1–3 orderers)
    • Merkle tree: tx hashes → merkle_root in header
    • Periodic blocks: every 30–120 min (from Scheduler)
    • Event-triggered blocks: immediate on anomaly
  end
```

### Tier Descriptions (Deep Dive)

#### Tier 1 — ESP32 + Sensors (Leaf Intelligence)
- **Responsibilities:** sample sensors, compute rolling stats per window, and emit threshold or delta-rate events.
- **Components:** ESP32 microcontroller with attached sensors.
- **Inputs:** raw sensor readings. **Outputs:** signed payloads with monotonic `seq`, `stats`, `last_ts`, optional CRT residues.
- **Timing:** sensor sampling every 1–5 min; periodic summary uplink every 10–15 min; event alerts immediately.
- **Failure Behavior:** buffers minimal state and retries uplink on next interval; sequence gaps detected by gateway.

#### Tier 2 — Raspberry Pi Gateway (Ingest • Verify • Bundle • Schedule)
- **Responsibilities:** verify signatures, deduplicate, recombine CRT residues, bundle records, persist queue, schedule submissions.
- **Components:** [IngressService](../flask_app/IngressService.md), [Bundler](../flask_app/Bundler.md), [StoreAndForward](../flask_app/StoreAndForward.md), [Scheduler](../flask_app/Scheduler.md).
- **Inputs:** Wi-Fi payloads from Tier 1. **Outputs:** `IntervalBundle` and `EventBundle` to mesh.
- **Timing:** bundle summaries every 30–120 min; events coalesced for 60–120 s and rate limited.
- **Failure Behavior:** [StoreAndForward](../flask_app/StoreAndForward.md) queues to `STORE_DIR` with retry/backoff.

#### Tier 3 — Pi⇄Pi Mesh Network (WokFi + BATMAN)
- **Responsibilities:** provide low-latency, self-healing transport between gateways and orderers; monitor mesh health.
- **Components:** BATMAN-adv mesh interface, [MeshMonitor](../flask_app/MeshMonitor.md).
- **Inputs:** bundles from scheduler. **Outputs:** gRPC traffic toward Fabric orderers.
- **Timing:** link latency 2–5 ms per hop; throughput tens of Mbps.
- **Failure Behavior:** automatic reroute on link failure; monitor surfaces neighbor/ETX changes.

#### Tier 4 — Blockchain (Hyperledger Fabric)
- **Responsibilities:** order, validate, and commit bundled transactions into blocks.
- **Components:** Raft [Orderer(s)](https://hyperledger-fabric.readthedocs.io/), Peers, [FabricClient](../flask_app/FabricClient.md), chaincode.
- **Inputs:** bundled transactions. **Outputs:** committed state and chaincode events.
- **Timing:** block size ~100 kB; `PreferredMaxBytes ≈ 1 MB`; periodic blocks every 30–120 min; event blocks immediately.
- **Failure Behavior:** idempotent keys (`last_seq:device_id`); peers retry on transient failures.

#### Tier 5 — Observability & Ops
- **Responsibilities:** expose health/readiness and metrics, present dashboards.
- **Components:** health server, Prometheus exporter, dashboards.
- **Inputs:** commit events, mesh stats, bundle counts. **Outputs:** `/healthz`, `/readyz`, metrics (`ingress_packets_total`, `bundles_submitted_total{type}`, `submit_commit_seconds`, `mesh_neighbors`, `store_backlog_files`).
- **Timing:** health endpoints polled continuously; metrics scraped on Prometheus interval.
- **Failure Behavior:** degraded health if no recent commit or mesh unhealthy.

### Data Schemas

- **Leaf → Pi Payload** (`≤ ~100 B`):
  - `device_id`, `seq`, `window_id`, `stats{min,avg,max,std,count}`, `last_ts`, `urgent`, optional `crt{m[],r[]}`, `sig`.
- **IntervalBundle** fields:
  - `bundle_id`, `window_id`, list of readings, `created_ts`, `count`.
- **EventBundle** fields:
  - `bundle_id`, list of events `{type,before,after,thresholds}`, `created_ts`.
- **On-chain Keys:**
  - `reading:device_id:window_id` → summary stats plus optional `residues_hash`.
  - `event:device_id:ts` → event details.
  - Summaries reduce storage; raw values recoverable via Merkle proofs and `residues_hash`.

### Consensus & Block Policy

- **Consensus:** Raft; use 1 orderer for ≤10 Pis, 3 orderers for ≥20 Pis.
- **Block Formation:** scheduler submits periodic bundles every 30–120 min; event bundles trigger immediate blocks.
- **Typical submit→commit latency:** ~2–3 s (2 Pis), 5–8 s (20 Pis), 15–30 s (100 Pis).

### CRT & Modular Arithmetic (When/Why)

- Leaf optionally encodes large integers as residues `r_i = x mod m_i` with pairwise co‑prime `m[]` whose product spans expected range.
- Pi recombines via Garner's algorithm; versioned `m[]` allow rotation and validation.
- Errors in recombination raise alerts and fall back to raw values.

### Security & Ops

- Leaves sign payloads via HMAC or Ed25519; the [device registry](../docs/device_registry.md) maps `device_id` to verification key.
- Mesh links secured with WPA2/3; WireGuard overlay recommended for end‑to‑end encryption.
- Health endpoints: `/healthz` checks mesh and pipeline, `/readyz` confirms recent commit; Prometheus metrics expose ingest and mesh stats.

### Cross-checks / To-Dos

- Stubs for gateway services: [IngressService](../flask_app/IngressService.md), [Bundler](../flask_app/Bundler.md), [Scheduler](../flask_app/Scheduler.md), [StoreAndForward](../flask_app/StoreAndForward.md), [FabricClient](../flask_app/FabricClient.md), [MeshMonitor](../flask_app/MeshMonitor.md).
- Payload schema documented in [`devices/leaf-node/docs/payload.md`](../devices/leaf-node/docs/payload.md); CRT primer in [`docs/crt.md`](../docs/crt.md).
- Device registry described in [`docs/device_registry.md`](../docs/device_registry.md).
- CouchDB indexes for `device_id`, `window_id`, `ts` located under `chaincode/sensor/META-INF/statedb/couchdb/indexes/`.
- Configuration knobs outlined in [`docs/gateway_config.md`](../docs/gateway_config.md).

### Caption & Legend

*Figure 1: Five-Tier, color-separated architecture; arrows label data, transport, and policy.*

| Tier | Color    | Summary |
|------|----------|---------|
| Tier 1 | `#E6FFF2` | ESP32 + Sensors (Leaf Intelligence) |
| Tier 2 | `#F1F8FF` | Raspberry Pi Gateway |
| Tier 3 | `#FFF5E6` | Pi⇄Pi Mesh Network |
| Tier 4 | `#FDF0FF` | Blockchain (Hyperledger Fabric) |
| Tier 5 | `#FFF0F0` | Observability & Ops |
