# Figure — Evaluation: Energy & Communications Metrics (ESP32 + Pi + Mesh + Fabric)

Related: [Five-Tier System Architecture](figure1_three_tier_system_architecture.md)

This file refines the metrics topology, latency pipeline, and energy budgets with realistic ranges and clear assumptions. Diagrams are ASCII-only so GitHub Mermaid renders cleanly.

---

## Part A — Metrics Topology

```mermaid
flowchart LR
    %% Classes first (GitHub Mermaid prefers this order)
    classDef device fill:#e0f7fa,stroke:#006064,color:#006064;
    classDef pi fill:#fff8e1,stroke:#ff6f00,color:#ff6f00;
    classDef network fill:#e8f5e9,stroke:#2e7d32,color:#2e7d32;
    classDef fabric fill:#f3e5f5,stroke:#6a1b9a,color:#6a1b9a;
    classDef observability fill:#fbe9e7,stroke:#d84315,color:#d84315;
    classDef data fill:#ffffff,stroke:#9e9e9e,color:#424242,stroke-dasharray:4 3;

    ESP32((ESP32)):::device
    INGRESS["Pi Ingress\nmetrics: ingress_packets_total, duplicates_total, drops_total, ingress_latency_seconds"]:::pi
    BUNDLER["Bundler and Scheduler\nmetrics: bundles_submitted_total&#123;type&#125;, bundle_latency_seconds,\nstore_backlog_files, events_rate_limited_total"]:::pi
    MESH["Mesh (BATMAN-adv)\nmetrics: mesh_neighbors, mesh_retries_total,\nmesh_etx_avg, mesh_rssi_avg"]:::network
    FABRIC["Fabric submit_to_commit path\nmetrics: submit_commit_seconds, tx_retry_total,\nendorsement_failures_total, block_bytes_total"]:::fabric
    OBS["Observability metrics endpoint\nmetrics: exporter_up, alert_events_total, scrape_duration_seconds"]:::observability

    ESP32 --> INGRESS --> BUNDLER --> MESH --> FABRIC --> OBS

    NOTEA["Notes:\nESP32 sends summaries 10-15 min or event frames.\nBundler aligns to 30-120 min windows and coalesces events 60-120 s.\nMesh stats reflect path quality and stability.\nFabric metrics focus on submit_to_commit latency and block size.\nObservability surfaces health, alerts, and scrape timings."]:::data

    ESP32 -.-> NOTEA

````

---

## Part B — Latency Pipeline

`Latency_total = L_read + L_wifi + L_ingress + L_bundle_wait + L_sched + L_mesh + L_submit_to_commit`

```mermaid
flowchart LR
    classDef box fill:#eef7ff,stroke:#1E66F5,color:#0f3a8a;
    classDef note fill:#fffde7,stroke:#f9a825,color:#6d4c41,stroke-dasharray:4 3;

    L_read[L_read\nsensor sampling and encode]:::box
    L_wifi[L_wifi\nWi-Fi uplink 10-50 ms typical]:::box
    L_ingress[L_ingress\nparse, verify sig, dedupe, CRT reconstruct]:::box
    L_bundle[L_bundle_wait\nperiodic: 30-120 min\nevents: ~0 (coalesce 60-120 s)]:::box
    L_sched[L_sched\nscheduler queue and backoff]:::box
    L_mesh[L_mesh\n2-5 ms per hop (WokFi BATMAN-adv)]:::box
    L_sc[L_submit_to_commit\n2 Pis: 1-2 s\n20 Pis: 3-5 s\n100 Pis: 10-15 s]:::box
    L_total[Latency_total]:::box

    L_read --> L_wifi --> L_ingress --> L_bundle --> L_sched --> L_mesh --> L_sc --> L_total

    N["Guidance:\n- Periodic mode dominated by L_bundle_wait.\n- Event mode dominated by L_submit_to_commit.\n- Keep coalesce small for faster event visibility.\n- Mesh hop count increases variance in L_mesh."]:::note
    L_mesh -.-> N
```

---

## Part C — Energy Budgets (realistic ranges)

Assumptions below are representative. Adjust currents and duty cycles to your exact hardware and firmware. Use formulas to recompute totals.

### C1. ESP32 leaf node (Wi-Fi uplink)

**Electrical assumptions (typical):**

* Supply: 3.3 V
* Deep sleep current: 0.01 mA (10 uA)
* Light sleep current: 2-10 mA (if used; avoid keeping enabled between samples)
* Active CPU (read/encode): 40-80 mA for 50-150 ms per sensor set
* Wi-Fi TX burst: 160-240 mA for 80-200 ms per uplink (depends on AP RSSI and data size)
* Per-sensor current during sampling:

  * DHT22: \~1-1.5 mA for 2 ms conversion plus MCU active time
  * Light (resistive divider to ADC): 0.1-1 mA while read
  * Capacitive soil moisture board: 5-30 mA while powered; gate it via MOSFET to read only
  * pH front-end board: 5-10 mA during read
  * Water level (float): \~0; ultrasonic: 2-10 mA during ping

**Config knobs:**

* `sample_period_sec` (e.g., 60-300 s)
* `uplink_period_sec` (e.g., 600-1800 s, i.e., 10-30 min)
* Event coalesce window: 60-120 s
* Use CRT to shrink bytes sent during uplink

**Daily energy formula (per node):**
`E_day_Wh = (Σ_i (I_i_mA * t_i_s) * V / 1000) / 3600`
where `i` covers sleep, sampling, and TX states.

**Example scenario (reasonable defaults):**

* Sample every 120 s (720 samples/day), total active per sample 120 ms at 60 mA effective (includes sensor currents via gating):

  * Sampling energy per day: `I=60 mA, t = 720 * 0.12 s = 86.4 s`
* Uplink every 900 s (15 min) with 120 B payload; Wi-Fi TX 200 ms at 200 mA + CPU 50 ms at 80 mA:

  * 96 uplinks/day
  * TX energy per day: `I=200 mA, t = 96 * 0.2 s = 19.2 s`
  * CPU energy per day: `I=80 mA,  t = 96 * 0.05 s = 4.8 s`
* Deep sleep otherwise (assume no light sleep), \~86399 s minus above activities

  * Sleep energy per day: `I=0.01 mA, t ≈ 86400 - (86.4 + 19.2 + 4.8) s ≈ 863 - 111. - not exact rounding`

Now compute approximate daily energy (insert your exact numbers):

* Sampling Wh: `(60 mA * 86.4 s * 3.3 V) / (1000 * 3600) ≈ 0.0042 Wh`
* Wi-Fi TX Wh: `(200 mA * 19.2 s * 3.3 V) / (1000 * 3600) ≈ 0.0035 Wh`
* CPU uplink Wh: `(80 mA * 4.8 s * 3.3 V) / (1000 * 3600) ≈ 0.00035 Wh`
* Deep sleep Wh: `(0.01 mA * ~86289.6 s * 3.3 V) / (1000 * 3600) ≈ 0.00079 Wh`

**Total ESP32 energy per day (example):** about **0.009 - 0.015 Wh**
This is extremely low and consistent with duty-cycled Wi-Fi bursts. If uplink period is shortened or if light sleep remains on, budget rises accordingly.

> Tip: Gating high-draw analog sensors (soil, pH) with a MOSFET and powering only during measurement yields significant savings.

---

### C2. ESP32 leaf node (LoRa uplink alternative)

If using LoRa for leaf to Pi:

* LoRa TX: 30-120 mA depending on SF and power, for 100-500 ms per frame
* Typical packet: 20-100 B summaries, no Wi-Fi stack overhead
* Energy impact per day often lower than Wi-Fi for same reporting rate, at the cost of higher latency and lower throughput

---

### C3. Raspberry Pi gateway

**Typical power (3B+ or 4B, headless):**

* Idle OS baseline: 2.5-3.5 W
* BATMAN-adv plus WireGuard active mesh: +0.8-1.5 W (depends on USB Wi-Fi 6 dongle and link rate)
* Apps.py ingest/bundle/submit steady work: +0.3-0.6 W
* Fabric peer container light load: +0.8-1.5 W
* Short CPU spikes during commit: +0.5-1.0 W

**Representative daily average:**

* Conservative typical: **4.5-6.0 W** average draw
* Daily energy: **108-144 Wh/day per Pi**

**Knobs to lower Pi energy:**

* Reduce logging verbosity
* Increase periodic window (fewer submits)
* Prefer Ethernet where possible (lower radio overhead)
* Tune USB Wi-Fi power saving and TX power

---

### C4. Mesh and Fabric communication budgets

* Mesh latency: 2-5 ms per hop (good LOS with WokFi); 2-4 hops typical per site
* Bundle size: 50-100 KB typical (summaries)
* Block size: PreferredMaxBytes about 1 MB; our blocks are dominated by cadence, not timeout
* Submit to commit after submit: 1-2 s (2 Pis), 3-5 s (20 Pis), 10-15 s (100 Pis)

---

## Part D — Updated communication and energy tables

### D1. Communication by hop

| Hop                  | Protocol or Layer                             | Message / Fields                                                                                              | Size target | Timing                                                     | Reliability (retry / SOF)              |
| -------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------: | ---------------------------------------------------------- | -------------------------------------- |
| ESP32 -> Pi          | Wi-Fi WPA2/3, HTTP or MQTT                    | `{device_id, seq, window_id, stats{min,avg,max,std,count}, last_ts, sensor_set, urgent, [crt{m[],r[]}], sig}` |    <= 100 B | Every 10-15 min and/or at window close; immediate on event | ESP32 retries, rotate pi\_targets\[]   |
| Pi -> Ingress        | Local IPC                                     | Same payload                                                                                                  |     \~100 B | Immediate                                                  | N/A                                    |
| Ingress -> Bundler   | In-memory                                     | NormalizedReading (verified, deduped, CRT reconstructed)                                                      |     \~150 B | Immediate                                                  | N/A                                    |
| Bundler -> Scheduler | In-memory                                     | IntervalBundle or EventBundle metadata                                                                        |      \~1 KB | 30-120 min (interval); 60-120 s coalesce (event)           | N/A                                    |
| Scheduler -> Mesh    | gRPC over TLS (WireGuard), IP over BATMAN-adv | Bundle `{bundle_id, window_id, readings[], created_ts, count, residues_hash or MerkleRoot}`                   |   50-100 KB | Cadence or immediate                                       | Store-and-forward, exponential backoff |
| Mesh -> Orderer      | L2 mesh to TCP Fabric ports                   | Fabric envelope                                                                                               |    \~100 KB | Cadence or immediate                                       | Mesh reroute, TCP retry                |
| Orderer -> Peers     | Raft + gRPC                                   | Ordered block `{prev_hash, merkle_root, ts}`                                                                  |     <= 1 MB | Immediate after submit                                     | Fabric retry                           |
| Peers -> Chaincode   | gRPC                                          | Tx proposal and state updates                                                                                 |      \~1 KB | Immediate                                                  | Fabric                                 |

### D2. ESP32 energy budget (worked example)

| State                               | Current (mA) | Time per day (s) |     Energy Wh at 3.3 V |
| ----------------------------------- | -----------: | ---------------: | ---------------------: |
| Sampling active (all sensors gated) |           60 |             86.4 |               \~0.0042 |
| Wi-Fi TX burst                      |          200 |             19.2 |               \~0.0035 |
| CPU during uplink (no radio)        |           80 |              4.8 |              \~0.00035 |
| Deep sleep                          |         0.01 |          \~86300 |               \~0.0008 |
| **Total**                           |              |                  | **\~0.009 - 0.015 Wh** |

Adjust currents and durations per your exact hardware and configuration.

---

## Part E — Notes on realism and tuning

* Payload compaction with CRT reduces airtime and improves Wi-Fi success probability at the edges of coverage.
* Soil moisture and pH boards can dominate leaf power if left powered. Gate them and read quickly.
* If you move leaf uplink to LoRa, you can often halve the daily energy at the cost of higher latency; keep event coalesce small to compensate.
* The Pi is the dominant energy consumer. Consider solar sizing for 6 W average with weather margin or use mains where available.

---

## Part F — Links

* Metrics naming and labels: see `docs/metrics.md`
* CRT and modular arithmetic: see `docs/crt.md`
* Architecture reference: `figure1_three_tier_system_architecture.md`



## Part G — Periodic vs Event timing (block formation behavior)

```mermaid
sequenceDiagram
    autonumber
    participant ESP32 as ESP32 leaf
    participant PI as Pi gateway
    participant BUNDLER as Bundler/Scheduler
    participant ORDER as Fabric orderer
    participant PEER as Fabric peers

    Note over ESP32: Periodic window mode
    ESP32->>PI: periodic summary payload (window close)
    PI->>BUNDLER: add to IntervalBundle
    BUNDLER->>BUNDLER: wait until cadence (30-120 min)
    BUNDLER->>ORDER: submit IntervalBundle
    ORDER-->>PEER: cut and broadcast block
    PEER-->>BUNDLER: commit event; read-back verify
    Note over BUNDLER: submit_to_commit 1-15 s (cluster size dependent)

    par Event path (independent of cadence)
        Note over ESP32: Event detection (threshold / delta rate)
        ESP32->>PI: urgent=true payload (coalesce 60-120 s)
        PI->>BUNDLER: add to EventBundle
        BUNDLER->>ORDER: submit EventBundle immediately
        ORDER-->>PEER: block cut now (BatchTimeout small)
        PEER-->>BUNDLER: commit; notify dashboard
    and Periodic continues
        BUNDLER->>BUNDLER: interval bundling unaffected
    end
````

**Key points**

* Periodic blocks are governed by the gateway cadence; orderer cuts quickly on arrival.
* Event bundles bypass the periodic window; a small coalesce window (60–120 s) merges bursts then submits immediately.
* Keep orderer BatchTimeout small (2–5 s) so event blocks close quickly even under light load.

---

## Part H — KPIs, targets, and alert thresholds

| KPI                                                   | Target (typical) | Warning threshold | Critical threshold | Notes                                       |
| ----------------------------------------------------- | ---------------: | ----------------: | -----------------: | ------------------------------------------- |
| submit\_to\_commit\_seconds (interval)                |            3–6 s |            > 10 s |             > 20 s | Increases with cluster size and mesh hops   |
| submit\_to\_commit\_seconds (event)                   |            2–4 s |             > 8 s |             > 15 s | Keep coalesce small for fast alerts         |
| store\_backlog\_files                                 |                0 |              > 10 |              > 100 | Backlog indicates Fabric or mesh outage     |
| ingress\_packets\_total minus duplicates\_total ratio |           > 0.99 |            < 0.98 |             < 0.95 | Duplicate or replay from flapping links     |
| mesh\_neighbors (per Pi)                              |             >= 1 |     == 0 for 60 s |     == 0 for 5 min | No neighbors implies isolation              |
| mesh\_etx\_avg                                        |            < 1.5 |             > 2.0 |              > 3.0 | ETX rise indicates link quality issues      |
| events\_rate\_limited\_total                          |                0 |               > 0 |      sustained > 0 | Tune thresholds/hysteresis                  |
| block\_bytes\_total (moving avg)                      |         < 200 kB |          > 500 kB |           > 800 kB | Consider pruning raw tails or raise cadence |
| power\_avg\_watts (Pi)                                |        4.5–6.0 W |           > 7.5 W |            > 9.0 W | Check radios, logging, throttling           |

Alert rules should include a duration (e.g., “for 5 min”) to avoid flapping.

---

## Part I — Measurement and validation plan

1. **Leaf bench test**

   * Fix `sample_period_sec=60`, `uplink_period_sec=900`, event thresholds safe.
   * Record: payload bytes, RSSI, TX duration (firmware log), ESP32 current (inline meter).
   * Output: daily Wh estimate using the table formula.

2. **Gateway ingest test**

   * Replay 1k synthetic payloads at 1–5 Hz.
   * Verify: dedupe rate \~0, ingress\_latency\_seconds p50 < 10 ms, p99 < 50 ms.

3. **Event path test**

   * Trigger 3 distinct events within 90 s.
   * Expect: exactly 1 EventBundle after coalesce; submit\_to\_commit < 6 s.

4. **Periodic path soak**

   * Run for 6 hours @ 30 min cadence.
   * Expect: 12 IntervalBundles, 12 blocks, no backlog, stable block\_bytes\_total.

5. **Mesh impairment**

   * Drop one WokFi link (attenuator or antenna rotate) for 5 min.
   * Expect: reroute within 10–30 s, ETX spike, submit\_to\_commit increases but remains < threshold.

6. **Power profiling**

   * Measure Pi wall power with and without mesh + Fabric.
   * Record averages and spikes during block commit.

---

## Part J — Capacity planning (formulas)

Let:

* `N_pi` = number of gateways (peers), `N_leaf_per_pi` = leaves per gateway
* `R` = readings per leaf per day (window summaries; typically 96 @ 15 min)
* `S_payload` = bytes per leaf summary (\~100 B)
* `S_bundle` ≈ `N_leaf_per_pi * S_payload + overhead` (typ 50–100 kB)
* `B_cadence` = bundles per day per gateway (24h / window\_minutes)

**Daily traffic per gateway over mesh:**
`T_mesh_day ≈ B_cadence * S_bundle`

**Ledger growth per day (summaries only):**
`G_ledger_day ≈ N_pi * B_cadence * (avg block bytes)`
(keep avg block bytes << PreferredMaxBytes; target \~100–200 kB)

**Peer CPU headroom:** ensure endorser rate `tx/s` << saturation; with summaries, typical is very low.

---

## Part K — Data retention and block sizing guidance

* Keep only **summaries on-chain**; store raw samples off-chain (STORE\_DIR) with **MerkleRoot** anchor.
* Target **avg block size 100–200 kB** to keep commit times predictable on Pis.
* Retain off-chain raw for 30–90 days; prune oldest when disk watermark exceeded (e.g., 70%).
* If block\_bytes\_total trends upward:

  * Reduce raw tails in events, enable CRT compaction, raise window minutes, or shard channels per field station.

---

## Part L — Troubleshooting workflow

```mermaid
flowchart TD
    classDef ok fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
    classDef warn fill:#fff8e1,stroke:#ff6f00,color:#e65100;
    classDef crit fill:#ffebee,stroke:#c62828,color:#b71c1c;

    A[Symptom: delayed commits or missing data] --> B{Which metric is red?}
    B -->|store_backlog_files > 0| C[Fabric unreachable or slow]:::crit
    B -->|mesh_neighbors == 0| D[Mesh isolation]:::crit
    B -->|submit_commit_seconds high| E[Consensus or endorsement slow]:::warn
    B -->|duplicates_total rising| F[Ingress replay or flapping leaf]:::warn
    B -->|block_bytes_total high| G[Block too big]:::warn

    C --> C1[Check orderer reachability, Raft health, disk I/O]
    D --> D1[Check WokFi alignment, RSSI, ETX; verify WireGuard up]
    E --> E1[Reduce load; check CouchDB indexes; peer logs]
    F --> F1[Check seq monotonicity on leaf; dedupe window]
    G --> G1[Reduce tails; enable CRT; increase interval minutes]

    C1 --> H[Recover and drain backlog]
    D1 --> H
    E1 --> H
    F1 --> H
    G1 --> H
```

---

## Part M — Glossary

* **CRT**: Chinese Remainder Theorem, used to compact large integers into residues; recombined via Garner on the Pi.
* **Coalesce window**: short time (e.g., 60–120 s) during which multiple event payloads are merged into one bundle.
* **ETX**: Expected Transmission Count; mesh quality indicator (lower is better).
* **STORE\_DIR**: on-disk queue for store-and-forward when Fabric or mesh is down.
* **submit\_to\_commit**: time between bundle submission and commit event observed by a peer.

---

## Appendix — Quick sanity checklist

* [ ] ESP32 payloads < 100 B typical; signature verified; seq monotonic.
* [ ] Interval cadence set to 30–120 min; event coalesce 60–120 s.
* [ ] Mesh neighbors >= 1; ETX < 2.0; WireGuard established.
* [ ] submit\_to\_commit p95 within targets (see Part H).
* [ ] Block bytes near 100–200 kB; PreferredMaxBytes \~ 1 MB.
* [ ] Prometheus scraping /metrics; alert rules loaded; dashboards show event vs periodic paths.

---


