# 1. Introduction & Scope

Blockchain is increasingly explored to enhance transparency and trust across agricultural supply chains, yet practical deployments remain sparse. Recent surveys catalogue pilot systems for traceability, resource management, and data sharing, underscoring the breadth of current experimentation (see [Zheng2025], Table 1, p. 3). These studies argue that coupling IoT sensing with distributed ledgers can mitigate data tampering and improve provenance tracking [Panwar2023]. Nevertheless, most initiatives are regional and lack interoperability, leaving farmers without a unified framework [Pakseresht2024]. Thus, consolidating blockchain-enabled IoT architectures for smart agriculture remains an open research frontier.

Emerging discussions emphasize that resource-constrained devices require parallelized transaction handling and adaptive consensus to scale securely. CRT-based residue computations promise lightweight cryptography suited to small embedded nodes [Sharma2025]. Concurrently, hierarchical consensus schemes aim to exploit gateway nodes for aggregation while maintaining ledger integrity [Kim2025]. QoS-aware designs are further needed to control latency and packet loss under bursty sensor traffic [Manoj2025]. These themes motivate the thesis on a CRT-based parallel transaction model with consensus and QoS mechanisms for smart agriculture.

# 2. Background & Definitions

The Chinese Remainder Theorem (CRT) decomposes arithmetic over a large modulus into independent operations on smaller coprime moduli, enabling parallel computation [Daniel2021]. In cryptographic protocols, CRT accelerates signing and decryption by allowing each residue class to be processed independently, reducing memory overhead [Sharma2025]. Such decomposition aligns with the limited word sizes of embedded microcontrollers. Consequently, CRT-based techniques offer a path to lightweight transaction processing in IoT contexts.

Consensus families vary in their assumptions and resource demands. Proof-of-Work guarantees strong immutability but consumes substantial energy and introduces confirmation delays [Panwar2023]. Proof-of-Stake reduces energy costs by replacing hashes with economic weight, yet it still requires continuous connectivity among validators [Rahoutiunknown]. Byzantine fault tolerant protocols like PBFT offer low latency for small groups but scale poorly in wide-area deployments [Kim2025]. Selecting an appropriate family for smart agriculture therefore depends on balancing security against node capability and network topology.

QoS and queuing concepts describe how arrival rates of sensor data interact with service rates of block creation. When transaction queues exceed service capacity, buffers overflow and data loss occurs, degrading reliability [Zheng2025]. IoT deployments often follow hierarchical layouts where leaf sensors forward data to gateways and then to cloud layers [Blockchainx02010Empowered2025]. Each level introduces distinct bandwidth and latency characteristics that influence consensus design [Kim2025]. Thus, end-to-end QoS requires coordinated control of queuing dynamics across the hierarchy.

# 3. Blockchain in Smart Agriculture: State of the Art

Surveys report a growing number of blockchain pilots for crop provenance, livestock monitoring, and input supply verification [Sendros2022]. Comparative analyses classify these efforts by application domain and technological stack, highlighting both diversity and fragmentation (see [Zheng2025], Table 1, p. 3). Despite broad interest, many studies remain conceptual and lack performance validation, limiting their transferability to production farms [Panwar2023].

Publication trends show a sharp rise in agricultural blockchain research after 2019, reflecting increased funding and awareness (see [Zheng2025], Figure 4, p. 9). Yet most works concentrate on traceability, with few exploring real-time control or autonomous actuation [Pakseresht2024]. The dominance of ledger-centric solutions underscores the need for frameworks that also address device constraints and network quality—areas targeted by the proposed CRT-based model.

# 4. IoT Architectures & Constraints

Smart agriculture networks typically adopt multi-tier structures comprising field sensors, edge gateways, and cloud backends. Edge-centric frameworks illustrate how federated learning and blockchain can coexist within this hierarchy (see [Manoj2025], Fig. 3, p. 11). Hybrid cyber-physical architectures further detail interactions among perception, control, and management layers (cf. [Blockchainx02010Empowered2025], Fig. 2, p. 3). These designs demonstrate the necessity of assigning distinct roles to each tier to accommodate heterogeneous hardware.

Resource limitations at the sensor tier impede direct participation in consensus. Studies of fog-enabled IoT show that lightweight devices struggle with cryptographic workloads, motivating delegation to gateways [Kim2025]. Gateways and edge processors possess moderate computation and storage, allowing them to batch transactions before forwarding them upstream [Manoj2025]. Cloud nodes maintain full ledgers and execute heavy analytics, closing the hierarchy [Blockchainx02010Empowered2025].

| Node type | Resource profile | Consensus role | Sources |
|-----------|-----------------|----------------|---------|
| Sensor node | Limited CPU and memory | Relies on gateways for transaction assembly | [Kim2025] |
| Gateway/edge | Moderate compute and storage | Aggregates and pre-validates sensor data | [Manoj2025] |
| Cloud/cluster | High-performance infrastructure | Hosts full ledger and analytics | [Blockchainx02010Empowered2025] |

*Data synthesized from [Kim2025], [Manoj2025], [Blockchainx02010Empowered2025].*

The disparity in capabilities across tiers motivates hierarchical consensus and residue-based parallelism to prevent bottlenecks at constrained nodes.

# 5. Consensus Mechanisms for IoT

Energy-intensive Proof-of-Work remains unsuitable for battery-powered deployments, as its hash puzzles impose delays incompatible with real-time sensing [Panwar2023]. Proof-of-Stake variants mitigate energy costs by selecting validators according to stake, but they still require robust connectivity and may centralize control in large stakeholders [Rahoutiunknown]. PBFT-style protocols execute quickly in trusted clusters, yet their message complexity escalates with network size [Kim2025].

Hybrid approaches propose layering consensus across hierarchical networks, allowing gateways to run fast local protocols before anchoring summaries on a global chain [Sendros2022]. Such schemes seek to balance responsiveness with security guarantees in dynamic agricultural environments [Manoj2025].

| Consensus | Energy use | Latency | Fault tolerance | Sources |
|-----------|-----------|---------|----------------|---------|
| Proof-of-Work | High | High | High | [Panwar2023] |
| Proof-of-Stake | Medium | Medium | Moderate | [Rahoutiunknown] |
| PBFT/federated | Low | Low | Limited to small groups | [Kim2025] |

*Data synthesized from [Panwar2023], [Rahoutiunknown], [Kim2025].*

Understanding these trade-offs is vital for designing hierarchical consensus that respects device constraints while ensuring ledger integrity.

# 6. CRT-based Parallel Transaction Approaches

Research on applying CRT to blockchain remains sparse. The theorem's ability to partition computations into independent residues enables parallel signature verification and reduced modular arithmetic complexity [Sharma2025]. Classical expositions further illustrate how CRT accelerates modular exponentiation in cryptography [Daniel2021]. These properties suggest that CRT could streamline transaction validation on constrained IoT hardware.

Nevertheless, existing agricultural blockchain studies emphasize traceability and security rather than transaction parallelization [Zheng2025]. Surveys seldom discuss residue number systems or CRT-driven batching, leaving a methodological gap for high-throughput agricultural ledgers [Panwar2023]. Addressing this gap informs the thesis’ proposal for a CRT-based parallel transaction model tailored to smart farming.

# 7. QoS and Queuing in Blockchain-IoT

End-to-end reliability in sensor-driven ledgers hinges on controlling delay, jitter, and loss across network layers. Authentication protocols for fog environments note that unbounded queues can throttle throughput and compromise responsiveness [Kim2025]. Reviews of agricultural blockchain systems likewise warn that untreated congestion leads to stale data and missed actuation windows [Zheng2025].

Empirical measurements from federated learning pilots reveal how smart-contract execution time scales with transaction volume (cf. [Manoj2025], Fig. 11, p. 21). Throughput and average latency curves illustrate the onset of queuing delays once arrival rates exceed service capacity (cf. [Manoj2025], Fig. 11, p. 22). These findings underscore the necessity of integrating queuing control into blockchain-IoT frameworks.

Consequently, QoS-aware transaction scheduling becomes essential for ensuring that residue-based parallelism and hierarchical consensus deliver timely updates to agricultural actuators.

# 8. Synthesis: Gaps & Opportunity

- **Lack of CRT-based transaction models.** Current reviews mention lightweight cryptography but do not present residue-oriented ledgers, leaving CRT’s parallelism untapped [Zheng2025], [Sharma2025].
- **Consensus misaligned with hierarchical constraints.** Existing PoS and BFT schemes rarely adapt to the multi-tier structure of agricultural IoT networks, hindering scalability [Kim2025], [Rahoutiunknown].
- **Insufficient QoS evaluation.** Studies focus on functional prototypes without rigorous analysis of queue dynamics or latency bounds [Manoj2025], [Sendros2022].

These gaps motivate a framework combining CRT-based parallel transactions, hierarchical consensus, and QoS-aware queuing tailored to smart agriculture.

## Limitations of this review

The review relies on secondary sources that often omit quantitative metrics, and many references provide only conceptual descriptions of architectures and protocols. Consequently, reported trade-offs may not capture full system variability, and emerging works published after 2025 are not represented.

# 9. Conclusion of Review

Blockchain and IoT integration for agriculture has advanced from conceptual pilots to increasingly complex architectures, yet scalability and reliability challenges persist. Addressing these challenges requires lightweight transaction processing, tiered consensus, and explicit QoS management. The surveyed literature highlights partial solutions but lacks a unified approach. A CRT-based parallel transaction model with consensus and QoS mechanisms can bridge this gap, paving the way for resilient smart agriculture networks.

# 10. References

[Publication12FARJ1184FinalPaperV1240830111128unknown]  Publication12_FARJ1184FinalPaperV1_240830_111128 (1), unknown.
[Zheng2025] Chengliang Zheng, Xiangzhen Peng, Ziyue Wang, Tianyu Ma, Jiajia Lu, Leiyang Chen, Liang Dong, Long Wang, Xiaohui Cui and Zhidong Shen A Review on Blockchain Applications in Operational Technology for Food and Agriculture Critical Infrastructure, 2025.
[S2025] S Dudhagara3172025JSRR139816, 2025.
[-2025] NIkechi - The_Internet_of_Things_IoT_in_Farming_Smart_Soluti, 2025.
[Sendros2022] Andreas Sendros, George Drosatos, Pavlos S. Efraimidis and Nestor C. Tsirliganis Blockchain Applications in Agriculture: A Scoping Review, 2022.
[TheInternetofThingsApplicationsandTechnologiesUsedTheCaseofBlockchainTechnologyInSmartAgriculture2025]  The-Internet-of-Things-Applications-and-Technologies-Used_-The-Case-of-Blockchain-Technology-In-Smart-Agriculture, 2025.
[ShahilKumarNationalSeedCongress13th2024unknown]  ShahilKumar_NationalSeedCongress_13th_2024, unknown.
[10247Proceedingfullpaperpdf1721777210SecuringAgriculturalImagingDatainSmartAgricultureaBlockchainbasedApproachtoMitigateCybersecurityThreatsandFutureInnovations2024]  10247_Proceeding_full_paper_pdf_1721777210_SecuringAgriculturalImagingDatainSmartAgriculture-aBlockchain-basedApproachtoMitigateCybersecurityThreatsandFutureInnovations, 2024.
[Daniel2021] Lars Daniel Chapter # Chapter Title, 2021.
[Manoj2025] T Manoj  A Blockchain-Assisted Trusted Federated Learning for Smart Agriculture, 2025.
[S2025] S Olateju2542025AJAAR133366, 2025.
[Sai2025] Sai Blockchain_technology_in_agriculture_Ensuring_tran, 2025.
[Sharma2025] Ms. Aarti Sharma From Centralized Algorithms to Decentralized Intelligence: A Blockchain Perspective, 2025.
[ROLEOFBLOCKCHAININAGRICULTURE2025]  ROLE_OF_BLOCKCHAIN_IN_AGRICULTURE, 2025.
[Pakseresht2024] Ashkan Pakseresht Blockchain technology characteristics essential for the agri-food sector: A systematic review, 2024.
[Rahoutiunknown] Nasim Paykari; Ali Alfatemi; Damian M. Lyons; Mohamed Rahouti Integrating Robotic Navigation with Blockchain: A Novel PoS-Based Approach for Heterogeneous Robotic Teams, unknown.
[Shofa2024] Shofa 988-2730-1-PB, 2024.
[Blockchainx02010Empowered2025]  Blockchain&#x02010;Empowered H&#x02010;CPS Architecture for Smart Agriculture, 2025.
[Green2025]  Green Secure Land Registration Scheme for Blockchain-enabled Agriculture Industry 5.0, 2025.
[AhmadiKalijietal2023BlockchainImplementationsinPrecisionAgriculturefinalvunknown]  AhmadiKalijietal.2023BlockchainImplementationsinPrecisionAgriculture_finalv, unknown.
[Akinnuoye2025] Akinnuoye FrankArena5, 2025.
[SCHOLAR2025] Mr.RESEARCH SCHOLAR Microsoft Word - Optimising the Agri-Food Value Chain Latest Trends and Proven Methods for Success 17042025.0905, 2025.
[BlockchainEmpowered2025]  Blockchain‐Empowered H‐CPS Architecture for Smart Agriculture, 2025.
[User2019] Microsoft Office User 1908.07391v1, 2019.
[EnhancingSustainabilityClimateResilienceandRe2025]  Enhancing_Sustainability_Climate_Resilience_and_Re, 2025.
[Panwar2023] Arvind Panwar, Manju Khari, Sanjay Misra and Urvashi Sugandh Blockchain in Agriculture to Ensure Trust, Effectiveness, and Traceability from Farm Fields to Groceries, 2023.
[ApplyingBlockchaininAgriculture2021]  ApplyingBlockchaininAgriculture, 2021.
[JISIBlockchainandIoTforSustainableAgricultureInnovationsandImpact2025]  JISI-BlockchainandIoTforSustainableAgriculture-InnovationsandImpact, 2025.
[Kim2025] Taehun Kim, Deokkyu Kwon, Yohan Park, and Youngho Park Blockchain-Based Secure Authentication Protocol for Fog-Enabled IoT Environments, 2025.
[EnablingAIinAgriculture40ABlockchainBasedMobileCrowdSensingArchitecture2024]  EnablingAIinAgriculture4.0ABlockchain-BasedMobileCrowdSensingArchitecture, 2024.
[Adnan2025] Adnan 14-SupplyChainTraceabilityandResilienceasDriversofBlockchain2025, 2025.
[TheUseofBlockchainTechnologyintheFoodTrace2025]  The_Use_of_Blockchain_Technology_in_the_Food_Trace, 2025.
[Publication12FARJ1184FinalPaperV1240830111128unknown]  Publication12_FARJ1184FinalPaperV1_240830_111128, unknown.
[Yang2025] Yang Yang, Min Lin, Yangfei Lin, Chen Zhang and Celimuge Wu A Survey of Blockchain Applications for Management in Agriculture and Livestock Internet of Things, 2025.
[Admin2024] Admin IJAS-030924-20929210_16_1_5_IJAS, 2024.
[L.B.2022] Krithika L.B. Survey on the Applications of Blockchain in Agriculture, 2022.
[account2023] Microsoft account c, 2023.
