# Figure — Full Communication Scheme (ESP32 ↔ Pi ↔ Mesh ↔ Fabric ↔ Observability)

Related: [Five-Tier System Architecture](figure1_three_tier_system_architecture.md)

```mermaid
sequenceDiagram
    participant ESP32 as ESP32 Node
    participant PI as Pi (Wi-Fi AP)
    participant INGRESS as IngressService
    participant BUNDLER as Bundler
    participant SCHED as Scheduler
    participant MESH as Mesh (BATMAN-adv/WireGuard)
    participant ORDERER as Fabric Orderer (Raft)
    participant PEERS as Fabric Peers
    participant CC as Chaincode
    participant METRICS as Metrics Exporter
    participant PROM as Prometheus
    participant DASH as Dashboard/Explorer
    participant ALERTS as Alertmanager
    participant OP as Operator

    ESP32-->>PI: {device_id, seq, window_id, stats, urgent, [crt?], sig}\nWi-Fi WPA2/3\n1–5 min samples or events
    PI-->>ESP32: ACK\nkeepalive/command
    Note over ESP32,PI: HMAC/Ed25519\nCRT residues at leaf
    PI-->>INGRESS: forward payload
    INGRESS-->>BUNDLER: verify & dedupe\nGarner CRT
    alt Periodic window
        BUNDLER-->>SCHED: interval bundle\ncoalesce 30–120 min
        SCHED-->>MESH: gRPC\nover WireGuard\non cadence
    else Event flow
        BUNDLER-->>SCHED: event bundle\ncoalesce 60–120 s
        SCHED-->>MESH: gRPC\nover WireGuard\nimmediate
    end
    MESH-->>ORDERER: L2 mesh hop\nBATMAN-adv
    ORDERER-->>PEERS: Raft block cut
    PEERS-->>CC: tx invoke
    CC-->>METRICS: emit metrics
    METRICS-->>PROM: expose /metrics\nHTTP scrape
    PROM-->>DASH: render graphs\n15 s pull
    PROM-->>ALERTS: push alerts
    ALERTS-->>OP: notify
    DASH-->>OP: visualize metrics
```
## End-to-end sequence (periodic and event flows)

```mermaid
sequenceDiagram
    autonumber
    participant ESP32 as ESP32 Node
    participant PI as Pi Wi-Fi AP
    participant INGRESS as IngressService
    participant BUNDLER as Bundler
    participant SCHED as Scheduler
    participant MESH as Mesh BATMAN-adv and WireGuard
    participant ORDERER as Fabric Orderer Raft
    participant PEERS as Fabric Peers
    participant CC as Chaincode
    participant METRICS as Metrics Exporter
    participant PROM as Prometheus
    participant DASH as Dashboard
    participant ALERTS as Alertmanager
    participant OP as Operator

    Note over ESP32: Sample sensors every 1-5 min. Detect thresholds and delta-rate events. Maintain monotonic sequence.
    ESP32->>PI: Leaf payload (device_id, seq, window_id, stats, last_ts, sensor_set, urgent, crt optional, sig)\nWi-Fi WPA2/3
    PI-->>ESP32: ACK or keepalive (optional commands)
    Note over ESP32,PI: HMAC or Ed25519 signature. Optional CRT residues at leaf.

    PI->>INGRESS: Forward payload (local)
    INGRESS->>INGRESS: Verify signature
    INGRESS->>INGRESS: Dedupe by device and sequence
    INGRESS->>INGRESS: Reconstruct CRT via Garner if present
    INGRESS->>BUNDLER: NormalizedReading

    alt Periodic window
        BUNDLER->>SCHED: Interval bundle (window 30-120 min)
        SCHED->>MESH: Submit bundle on cadence (gRPC over TLS tunneled via WireGuard)
    else Event flow
        BUNDLER->>SCHED: Event bundle (coalesce 60-120 s, rate limit)
        SCHED->>MESH: Submit bundle immediately (gRPC over TLS)
    end

    Note over MESH: L2 routing via BATMAN-adv on bat0. 2-5 ms per hop. Tens of Mbps with WokFi links.
    MESH->>ORDERER: Fabric envelope to orderer cluster (Raft)
    ORDERER->>PEERS: Ordered block broadcast
    PEERS->>CC: Endorse validate commit (chaincode invoked)
    CC-->>PEERS: Chaincode events emitted

    PEERS->>METRICS: Increment counters and gauges on commit
    METRICS->>PROM: Expose metrics endpoint for scraping (HTTP pull)
    PROM->>DASH: Render graphs and tables (15 s scrape)
    PROM->>ALERTS: Fire alerts on rules (latency, backlog, health)
    ALERTS->>OP: Notify via email or webhook
    DASH->>OP: Visualization and drilldowns

    Note over SCHED,PEERS:
      After submit, wait for commit event
      Do read-back verification of one key
      Log submit to commit latency
    end note



```
## End-to-end sequence (periodic and event flows)

**What is transmitted**

| Hop | Protocol/Layer | Message/Fields | Size target | Timing | Reliability (retry/SOF) |
| --- | -------------- | -------------- | ----------- | ------ | ----------------------- |
| ESP32 → Pi | Wi-Fi (WPA2/3) | `{device_id, seq, window_id, stats, urgent, [crt?], sig}` | <100 B | 1–5 min or event | ESP32 retry, HMAC |
| Pi → ESP32 | Wi-Fi | ACK/command | <50 B | immediate | WPA retry |
| Pi → Ingress | loopback | same payload | <100 B | immediate | n/a |
| Ingress → Bundler | in-memory | normalized reading | ~150 B | immediate | n/a |
| Bundler → Scheduler | in-memory | interval/event bundle metadata | ~1 KB | 30–120 min periodic;<br/>60–120 s event | n/a |
| Scheduler → Mesh | gRPC over WireGuard | bundle `{bundle_id,…}` | 50–100 KB | cadence or immediate | SOF retry |
| Mesh → Orderer | BATMAN-adv L2 | Fabric envelope | ~100 KB | cadence or immediate | SOF retry |
| Orderer → Peers | Raft/gRPC | block `{prev_hash, merkle_root, ts}` | <1 MB | immediate | Fabric retry |
| Peers → Chaincode | gRPC | tx proposal | ~1 KB | immediate | Fabric retry |
| Chaincode → Metrics | internal | counters/gauges | n/a | on commit | n/a |
| Metrics → Prometheus | HTTP | `/metrics` scrape | text | 15 s poll | HTTP retry |
| Prometheus → Dashboard | HTTP/WebSocket | rendered metrics | text/JSON | on demand | HTTP retry |
| Prometheus → Alertmanager | HTTP | alert payloads | small | on rule trigger | HTTP retry |
| Alertmanager → Operator | Email/Webhook | notification | text | on alert | transport retry |
| Dashboard → Operator | HTTP/WebSocket | visualization updates | text/JSON | on demand | HTTP retry |

