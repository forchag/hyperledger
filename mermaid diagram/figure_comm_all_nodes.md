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
    participant METRICS as Health/Metrics
    participant DASH as Dashboard/Explorer

    ESP32-->>PI: {device_id, seq, window_id, stats, urgent, [crt?], sig}\nWi-Fi WPA2/3\n1–5 min samples or events
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
    METRICS-->>DASH: HTTP /metrics\n15 s poll
```

**What is transmitted**

| Hop | Protocol/Layer | Message/Fields | Size target | Timing | Reliability (retry/SOF) |
| --- | -------------- | -------------- | ----------- | ------ | ----------------------- |
| ESP32 → Pi | Wi-Fi (WPA2/3) | `{device_id, seq, window_id, stats, urgent, [crt?], sig}` | <100 B | 1–5 min or event | ESP32 retry, HMAC |
| Pi → Ingress | loopback | same payload | <100 B | immediate | n/a |
| Ingress → Bundler | in-memory | normalized reading | ~150 B | immediate | n/a |
| Bundler → Scheduler | in-memory | interval/event bundle metadata | ~1 KB | 30–120 min periodic;<br/>60–120 s event | n/a |
| Scheduler → Mesh | gRPC over WireGuard | bundle `{bundle_id,…}` | 50–100 KB | cadence or immediate | SOF retry |
| Mesh → Orderer | BATMAN-adv L2 | Fabric envelope | ~100 KB | cadence or immediate | SOF retry |
| Orderer → Peers | Raft/gRPC | block `{prev_hash, merkle_root, ts}` | <1 MB | immediate | Fabric retry |
| Peers → Chaincode | gRPC | tx proposal | ~1 KB | immediate | Fabric retry |
| Chaincode → Metrics | internal | counters/gauges | n/a | on commit | n/a |
| Metrics → Dashboard | HTTP | `/metrics` scrape | text | 15 s poll | HTTP retry |

