# Figure 3b: Verification Process

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant N as Edge Node
    participant B as Blockchain

    C->>N: Request data (TxID)
    N->>B: Retrieve daily Merkle root
    N-->>C: Tx + Merkle path
    C->>C: Hash transaction
    C->>C: Rebuild Merkle path
    C->>B: Compare with root
    B-->>C: Valid / Invalid

    Note over C,N: Client performs verification locally

    classDef client fill:#e6f7ff,stroke:#91d5ff
    classDef node fill:#f6ffed,stroke:#b7eb8f
    classDef chain fill:#e0f0ff,stroke:#adc6ff

    class C client
    class N node
    class B chain
```
