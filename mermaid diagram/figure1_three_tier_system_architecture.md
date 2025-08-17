# Figure 1: Three-Tier System Architecture

```mermaid
graph TD
  %% ===== POWER LAYER =====
  subgraph PWR[Power Layer]
    direction TB
    SOLAR["Solar Panel (10W)"] --> CHARGE[Charge Controller]
    CHARGE --> BATT["Battery (10,000mAh)"]
    BATT --> DIST[Power Distribution]
    style PWR fill:#f7fcf0,stroke:#fdae6b
  end

  %% ===== SENSING LAYER =====
  subgraph SNS[Sensing Layer]
    direction TB

    subgraph Z1["Zone 1 (1 km²)"]
      SM1[Soil Moisture] --> ESP1[ESP32 Node]
      T1[Temperature] --> ESP1
      NPK1[NPK Sensor] --> ESP1
      ESP1 --> |LoRa| GW
      style Z1 fill:#e6f7ff,stroke:#91d5ff
    end

    subgraph Z2["Zone 2 (1 km²)"]
      SM2[Soil Moisture] --> ESP2[ESP32 Node]
      T2[Temperature] --> ESP2
      NPK2[NPK Sensor] --> ESP2
      ESP2 --> |LoRa| GW
      style Z2 fill:#e6f7ff,stroke:#91d5ff
    end

    ZN[Zone N] --> |LoRa| GW
    style SNS fill:#f0f9e8,stroke:#43a2ca
  end

  %% ===== EDGE PROCESSING LAYER =====
  subgraph EDGE[Edge Processing Layer]
    direction TB
    GW[Gateway RPi] --> BUF[Buffer]
    BUF --> FE[Feature Extractor]
    FE --> CRT[CRT Compressor]
    CRT --> SIG[RSA-CRT Signer]
    SIG --> LORA[LoRa Transmitter]

    subgraph FE[Feature Extractor]
      MIN[min]:::feat
      MAX[max]:::feat
      MEAN[mean]:::feat
      STD[std]:::feat
      PERC[p90]:::feat
      ANOM[anomaly_flag]:::feat
      style FE fill:#e6f7ff,stroke:#91d5ff
    end

    subgraph CRT[CRT Compressor]
      R1["res₁ = mean % 65521"]:::code
      R2["res₂ = std % 65519"]:::code
      R3["res₃ = (max×10⁴ + min) % 65497"]:::code
      style CRT fill:#f6ffed,stroke:#b7eb8f
    end

    style EDGE fill:#e0f3db,stroke:#43a2ca
  end

  %% ===== BLOCKCHAIN LAYER =====
  subgraph BLC[Blockchain Layer]
    direction LR
    LORA --> VAL[Validator Node]
    VAL --> ANC[DailyAnchor Contract]
    VAL --> ARCH[Archival Node]
    ARCH --> EXT[External HDD]
    ANC --> HIST[Historical Roots]

    subgraph VAL[Validator Node]
      PBFT[PBFT Consensus] --> BLOCK[Block Creator]
      BLOCK --> LEDGER[Distributed Ledger]
      style VAL fill:#e0ecff,stroke:#6b8cff
    end

    style BLC fill:#ccebc5,stroke:#43a2ca
  end

  %% ===== DATA FLOW =====
  SNS -->|Raw Sensor Data| EDGE
  EDGE -->|Signed Transactions| BLC
  PWR -->|Power| SNS
  PWR -->|Power| EDGE
  PWR -->|Power| BLC

  %% ===== ANNOTATIONS =====
  ANNOT1[["LoRa Specs:
  - Frequency: 868 MHz
  - Range: 6.2 km
  - Data Rate: 5.5 kbps
  - AES-128 Encryption"]] --> LORA

  ANNOT2[["Hyperledger Fabric:
  - PBFT Consensus
  - 30–120 min Blocks
  - Event-triggered writing
  - Reduced Storage"]] --> VAL

  ANNOT3[["Power Metrics:
  - 10W per Node
  - 6h Battery Backup
  - Solar Recharge"]] --> PWR

  %% ===== STYLES =====
  classDef feat fill:#f0f9ff,stroke:#69c0ff
  classDef code fill:#f8f9fa,stroke:#adc6ff
  classDef annot fill:#fffbe6,stroke:#ffe58f
```

### Key Components Explained

#### 1. Power Layer
- **Solar Panel**: 10W polycrystalline
- **Charge Controller**: PWM-based regulation
- **Battery**: LiFePO₄ 10,000mAh @ 3.2V
- **Distribution**: 5V DC to all nodes
- *Runtime*: 6 hours continuous operation

#### 2. Sensing Layer (Per 1 km² Zone)
- **Soil Moisture Sensor**: Capacitive V1.2 (±3% accuracy)
- **Temperature Sensor**: DS18B20 (±0.5°C accuracy)
- **NPK Sensor**: JXCT-IoT (N/P/K detection)
- **ESP32**: dual-core 240 MHz, 520 KB RAM
- **LoRa Module**: SX1278 (20 dBm output)
- *Reporting Modes*: periodic 30–120 min updates or instant alerts on threshold breaches

#### 3. Edge Processing Layer
- **Feature Extractor**:
  ```python
  features = {
    'min': np.min(window),
    'max': np.max(window),
    'mean': np.mean(window),
    'std': np.std(window),
    'p90': np.percentile(window, 90),
    'anomaly': 1 if std > 15 else 0
  }
  ```
- **CRT Compressor**:
  ```c
  residues[0] = (uint16_t)(mean * 100) % 65521;
  residues[1] = (uint16_t)(std * 100) % 65519;
  residues[2] = (uint16_t)((max * 10000) + min) % 65497;
  ```
- **RSA-CRT Signer**: 2048-bit keys, 78 ms signing time
- *Output*: 46-byte signed AgriBlock

#### 4. Blockchain Layer
- **Validator Node**:
  - PBFT consensus with 3-phase commit
  - Block creation every 5 seconds
- **DailyAnchor Contract**:
  ```solidity
  struct DailyRoot {
    bytes32 merkleRoot;
    uint256 timestamp;
    bytes32 prevRoot;
  }
  ```
- **Archival Node**:
  - RocksDB storage with Zstd compression
  - Daily rsync to external HDD
- *Storage Efficiency*: 225 KB/day per 100 zones

### Data Flow Sequence
1. **Sensing**: 10-second sensor reads → 30-min windows (180 samples)
2. **Edge Processing**:
   - Feature extraction → CRT compression → RSA signing
   - LoRa transmission to gateway
3. **Blockchain**:
   - Transaction validation → PBFT consensus → Ledger storage
   - Daily Merkle root calculation and anchoring

### Performance Metrics
| **Parameter** | **Sensing** | **Edge** | **Blockchain** |
|---------------|-------------|----------|----------------|
| Power Draw | 2.1W | 3.5W | 4.2W |
| Data Output | 1440B/window | 46B/window | 32B/day (root) |
| Processing Time | N/A | 85 ms | 420 ms |
| Network Load | 0.5% duty cycle | 12 KB/hr | 8 KB/hr |

### Innovative Features
1. **Hybrid Compression**:
   - Temporal downsampling (180:1)
   - CRT numerical encoding (12:1)
2. **Fault Tolerance**:
   - Battery-backed operation during cloud cover
   - PBFT consensus tolerates 1/3 node failures
3. **Resource Optimization**:
   - Anomaly-driven irrigation commands
   - Solar-powered off-grid deployment

This revised architecture diagram provides complete technical visibility into the AgriCrypt-Chain system, highlighting the power management, sensor-to-blockchain data flow, and cryptographic processing stages essential for large-scale agricultural monitoring. The color-coded layers and annotated specifications enable clear understanding of the system's operation in resource-constrained environments.
