# Figure 6: CRT Compression Mechanics

```mermaid
graph LR
  %% ===== INPUT: ORIGINAL VALUES =====
  OV["Original Sensor Values"] --> SCALE[Scaling]
  
  subgraph OV["Original Values"]
    direction TB
    V1(("Mean Moisture: 45.23%")):::value
    V2(("Std Dev: 3.18%")):::value
    V3(("Max Temp: 29.8°C")):::value
    V4(("Min Temp: 22.1°C")):::value
    V5(("NPK: [120,45,210] ppm")):::value
    style OV fill:#e6f7ff,stroke:#91d5ff
  end

  %% ===== SCALING PROCESS =====
  SCALE --> INT[Integer Conversion]
  
  subgraph SCALE["Scaling"]
    direction LR
    S1["mean_scaled = 45.23 × 100 = 4523"]:::code
    S2["std_scaled = 3.18 × 100 = 318"]:::code
    S3["max_scaled = 29.8 × 100 = 2980"]:::code
    S4["min_scaled = 22.1 × 100 = 2210"]:::code
    S5["npk_scaled = 120×10⁶ + 45×10³ + 210 = 120,045,210"]:::code
    style SCALE fill:#f6ffed,stroke:#b7eb8f
  end

  %% ===== MODULO OPERATIONS =====
  INT --> MOD[Modulo Compression]
  
  subgraph MOD["Modulo Operations"]
    direction TB
    M1["res₁ = 4523 % 65521 = 4523"]:::code
    M2["res₂ = 318 % 65519 = 318"]:::code
    M3["res₃ = (2980×10000 + 2210) % 65497 = 29,802,210 % 65497 = 3002"]:::code
    M4["res₄ = 120,045,210 % 65519 = 28977"]:::code
    style MOD fill:#ffefe6,stroke:#ffd8bf
  end

  %% ===== RESIDUE STORAGE =====
  MOD --> STORE[Storage]
  
  subgraph STORE["Compressed Storage"]
    direction LR
    R1["res₁: 4523 → 2 bytes"]:::storage
    R2["res₂: 318 → 2 bytes"]:::storage
    R3["res₃: 3002 → 2 bytes"]:::storage
    R4["res₄: 28977 → 2 bytes"]:::storage
    style STORE fill:#f9f0ff,stroke:#d3adf7
  end

  %% ===== ANNOTATIONS =====
  ANNOT1[["Moduli Properties:\n- 65521 (prime)\n- 65519 (prime)\n- 65497 (prime)\n- Coprime: GCD=1"]] --> MOD
  ANNOT2[["Size Reduction:\n- Original: 20 bytes\n- Compressed: 8 bytes\n- Reduction: 60%"]] --> STORE
  ANNOT3[["Error Analysis:\n- Max Quantization Error: ±0.005%\n- Reconstruction Accuracy: 99.995%"]] --> STORE

  %% ===== PERFORMANCE =====
  PERF[["Performance (RPi 4B):\n- Scaling: 0.02 ms\n- Modulo: 0.08 ms\n- Total: 0.10 ms"]] --> STORE

  %% ===== STYLES =====
  classDef value fill:#e6f7ff,stroke:#91d5ff,stroke-width:2px
  classDef code fill:#f8f9fa,stroke:#d9d9d9,stroke-width:1px
  classDef storage fill:#e0f0ff,stroke:#adc6ff,stroke-width:2px
  classDef annot fill:#fffbe6,stroke:#ffe58f,stroke-width:1px
```
