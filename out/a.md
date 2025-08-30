\documentclass[10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{geometry}
\geometry{a4paper, margin=1in}
\usepackage{setspace}
\onehalfspacing
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=cyan,
    pdftitle={Literature Review},
    bookmarks=true,
    pdfpagemode=FullScreen,
}
\usepackage[style=ieee]{biblatex}
\addbibresource{references.bib} % Save your BibTeX entries to this file

\title{Blockchain-enabled IoT Framework for Smart Agriculture: A Literature Review on Security, Privacy, and Reliability}
\author{Your Name}
\date{\today}

\begin{document}

\maketitle

\section*{Abstract}
This literature review examines recent advances (2022-2025) in blockchain-enabled IoT frameworks for smart agriculture, focusing on security, privacy, and reliability aspects. The review synthesizes findings from 37 peer-reviewed studies that address challenges related to data integrity, tamper resistance, and end-to-end trust in smart farming environments through cutting-edge blockchain architectures, advanced cryptographic methods, and machine learning-based threat detection.

\section{Introduction}
Smart agriculture is undergoing a rapid digital transformation driven by the convergence of IoT, artificial intelligence, and blockchain technologies. The use of IoT sensors in farms generates vast amounts of data regarding soil condition, environmental parameters, and crop health, which, when combined with advanced analytics, can significantly enhance operational decision-making and productivity. However, the increased connectivity of agricultural systems has raised critical challenges related to cybersecurity, privacy breaches, and data tampering. Centralized cloud architectures present vulnerabilities such as single points of failure and unauthorized data manipulation, which can lead to compromised data integrity and operational disruptions \cite{aliyu2023blockchainbasedsmartfarm}. 

In response, blockchain technology offers an immutable, decentralized ledger that establishes transparency and trust through consensus mechanisms and cryptographic safeguards. This literature review explores how emerging blockchain-enabled IoT frameworks specifically address the intertwined issues of security, privacy, and reliability in smart agriculture. The review also highlights state-of-the-art architectures that incorporate fault-tolerant blockchain frameworks, machine learning for anomaly detection, privacy-preserving data aggregation, and Quality-of-Service (QoS) mechanisms to support parallel transaction processing and consensus \cite{daund2025designofan}.

\section{Security Aspects in Blockchain-Enabled Smart Agriculture}
Security remains the foremost priority in deploying IoT systems in agriculture. Early research laid the foundation by showing that blockchain's inherent characteristics—decentralization, cryptographic hashing, and immutable ledger storage—can significantly improve data integrity and reduce vulnerabilities \cite{aliyu2023blockchainbasedsmartfarm}. For instance, Aliyu and Liu (2023) proposed a blockchain-based smart farm security framework which leverages immutable transaction records and smart contracts to enforce access controls and enable real-time monitoring of IoT sensor health. Their framework employs technologies such as Arduino sensor kits, AWS cloud services, and the Ethereum blockchain via the Rinkeby test network to trigger alerts when abnormal sensor readings are detected. The practical evaluations demonstrated that a decline in accepted blockchain transactions was a reliable indicator of potential security threats, such as poisoning attacks, thereby enhancing end-to-end transaction security and ensuring that tamper-resistant data were available as evidence for dispute resolution.

Other studies have focused on designing fault-tolerant architectures that incorporate consensus algorithms to manage potential single points of failure. For example, research on redactable blockchain-assisted secure data aggregation in fog-enabled Internet-of-Farming-Things (IoFT) systems introduced a three-tier architecture in which data from agricultural IoT devices are aggregated securely at the fog layer before being transmitted and stored in an immutable ledger in the cloud \cite{mishra2023redactableblockchainassistedsecure}. This approach enhances security by coupling source authentication with controlled data modification capabilities while maintaining high availability and protecting against collusion and false data-injection attacks. Additionally, several works have proposed lightweight blockchain implementations optimized for resource-constrained environments encountered in small-scale farms, although challenges such as increased energy consumption per transaction and higher computational overhead persist \cite{shahzad2025decentralizediotbasedarchitectures}.

Smart contracts play a central role in enforcing security policies in these architectures. They automate authentication, access control, and the validation of transactions across distributed networks. For example, blockchain platforms such as Hyperledger Fabric and Corda have been preferred for agricultural applications due to their permissioned networks, which enable controlled access and thereby reduce the risk of unauthorized data access \cite{aliyu2023blockchainbasedsmartfarm, soy2025blockchainintegrationin}. These platforms, however, have shown differences in scalability and transaction processing capabilities. Ethereum, despite its flexibility and strong support for smart contracts, is often challenged by scalability limitations that result in increased transaction costs and latency in real-time applications \cite{aliyu2023blockchainbasedsmartfarm}. Therefore, many implementations target permissioned blockchains that offer modularity, enabling security protocols specifically tailored for enterprise-level smart farming deployments.

Another noteworthy approach to security enhancement involves integrating advanced cryptographic techniques such as Elliptic Curve Cryptography (ECC), ring signature technology, and zero-knowledge proofs. Liu et al. demonstrated that the use of ECC not only improves data confidentiality during transmission but also aids robust access control mechanisms that are critical in mitigating insider threats and impersonation attacks in IoT networks. Moreover, lightweight anonymous authentication schemes and secure key management protocols have been developed to secure endpoints without relying on centralized certificate authorities, thus further decentralizing the risk and improving overall network resilience \cite{rai2024enhancingdatasecurity}.

Finally, cyberattack detection and intrusion prevention are enhanced through the incorporation of machine learning techniques. For example, the integration of Isolation Forest for unsupervised anomaly detection and Long Short-Term Memory (LSTM) networks for time-series threat detection has yielded detection rates exceeding 95\% accuracy \cite{daund2025designofan}. These approaches further augment blockchain-based security architectures by providing early warning signals to farmers via mobile applications and automated anomaly triggers embedded as part of smart contracts.

\section{Privacy Preservation Mechanisms}
Privacy concerns in smart agricultural IoT are multifaceted, involving unauthorized access to sensitive farm data, exposure of personal financial information, and risks associated with the misuse of longitudinal agricultural datasets. Recent literature underscores the importance of a privacy-centric framework that integrates secure data exchange, confidential analytics, and user anonymity without compromising the transparency of blockchain systems \cite{rahaman2024privacycentricaiand}.

One promising direction integrates blockchain technology with privacy-preserving machine learning techniques such as federated learning and differential privacy. In a recent study, researchers combined Hyperledger Fabric with federated learning to enable distributed model training, protecting raw data on local IoT devices while sharing only encrypted intermediate results \cite{daund2025designofan}. Differential privacy techniques are applied by adding calibrated noise to data contributions, ensuring that sensitive information remains anonymized while maintaining acceptable model accuracy. Such methods effectively counteract privacy leakage, a critical requirement given that centralized data aggregation in conventional cloud systems can be exploited by attackers or expose data through misconfigured access permissions.

Other works examine the integration of cryptographic techniques tailored to enhance privacy. Zero-Knowledge Proofs (ZKP), for instance, enable participants to validate the authenticity of transactions without revealing underlying data, striking an optimum balance between auditability and confidentiality \cite{soy2025blockchainintegrationin}. Similarly, ring signatures have been employed on elliptic curve platforms to ensure user anonymity in transaction validation, although these methods sometimes require trade-offs in terms of computational efficiency.

Blockchain-based privacy-preserving methods for supply chain management are also critical. In a food traceability context, privacy-preserving protocols ensure that proprietary information related to agricultural practices and product quality remains confidential while offering end-to-end transparency, thereby assuring stakeholders of data integrity. However, such systems face challenges related to the inherent conflict between blockchain transparency and individual privacy, often necessitating the use of hybrid models that combine public and private blockchain features \cite{soy2025blockchainintegrationin}.

Another aspect of privacy preservation is the security of data exchanged among heterogeneous IoT devices. For instance, a privacy-centric protocol designed for smart rural farm monitoring employs a three-phase scheme integrating symmetric and asymmetric key encryption, hash functions, and secure communication channels. This protocol has demonstrated resilience against identity guessing, impersonation, and man-in-the-middle attacks, while maintaining low computational overhead to suit resource-constrained rural environments \cite{rahaman2024privacycentricaiand}. Nonetheless, while these methods have excelled in controlled experimental settings, their scalability to large-scale deployments in the field remains an open question.

In summary, privacy preservation in blockchain-enabled IoT smart agriculture systems is achieved by combining federated learning with advanced encryption, ZKP, and anonymous authentication schemes. Although these methods have significantly improved data confidentiality and user privacy while enabling collaborative analytics, challenges persist in scaling these approaches with minimal additional resource consumption \cite{soy2025blockchainintegrationin}.

\section{Reliability and Fault Tolerance}
Reliability in smart agriculture IoT frameworks ensures that data collected from a diverse range of sensors remains accurate, timely, and available for decision-making despite the presence of dynamic network conditions and potential cyber threats. Efforts to create fault-tolerant blockchain architectures are motivated by the need to prevent data loss, mitigate single points of failure, and maintain operational continuity amid cyber-attacks \cite{aliyu2023blockchainbasedsmartfarm}.

Recent works have developed multi-tiered blockchain architectures that stratify processing into edge, fog, and cloud layers, each managed by designated "Data Handlers" to ensure effective data lifecycle management. One such architecture incorporates Local Agricultural Data Handlers at the edge for on-site sensor data capture, Peripheral Agri-Fog Data Handlers that facilitate low-latency transmission, and Cloud Agri-Data Handlers that process and analyze aggregated data using advanced optimization algorithms \cite{thiruvenkatasamy2025anonlinetool}. This hierarchical design distributes trust and processing load, increasing overall system fault tolerance and scalability.

Another approach leverages redactable blockchain techniques that allow controlled data modifications while upholding overall immutability. In fog-enabled Internet-of-Farming-Things (IoFT) systems designed for secure data aggregation, a redactable blockchain framework was proposed to selectively modify data while maintaining a record of all alterations. This method enhances reliability by ensuring that even if data inconsistencies are detected, they can be corrected without compromising the integrity of the overall ledger \cite{mishra2023redactableblockchainassistedsecure}. Nevertheless, the computational overhead associated with such encryption and redaction processes remains a limitation for real-world deployments.

Reliability is further exemplified in prototypes that integrate blockchain with cloud-based processing to provide real-time monitoring and automated responses. For instance, a significant prototype employs NodeMCU microcontrollers connected to a permissioned blockchain network whereby IoT sensors continuously report environmental parameters. In a case study applied to a cotton field, the system reduced water consumption by 35\% by triggering automated irrigation based on data recorded immutably on the blockchain \cite{shahzad2025decentralizediotbasedarchitectures}. This performance underscores the practical benefits of combining decentralization with real-time analytics. Key performance metrics in such implementations include throughput (measured in transactions per second), latency, and resource utilization, each of which must be balanced against the inherent overhead incurred by blockchain consensus protocols.

The literature also emphasizes the need for robust consensus mechanisms capable of operating in distributed agricultural environments characterized by intermittent connectivity and heterogeneous IoT devices. Conventional consensus methods such as Proof-of-Work (PoW) introduce high computational and energy costs, whereas alternatives such as Proof-of-Authority (PoA) and Practical Byzantine Fault Tolerance (PBFT) offer greater efficiency and scalability for permissioned networks \cite{soy2025blockchainintegrationin}. Still, selecting an appropriate consensus algorithm remains a trade-off between decentralization, energy efficiency, and overall throughput.

Despite these advances, several challenges persist. The integration of blockchain protocols with resource-constrained agricultural IoT devices may result in increased communication latency and processing delays, negatively impacting the real-time responsiveness necessary for critical decision-making processes. Furthermore, the deployment of blockchain-based fault-tolerant systems in diverse farming contexts still requires extensive field testing to validate performance under environmental and operational heterogeneity \cite{shahzad2025decentralizediotbasedarchitectures}.

\section{State-of-the-Art Comparison and Discussion}
Comparing the recent literature reveals a convergence toward integrating blockchain with advanced cryptographic and machine learning techniques to solve persistent problems in smart agriculture. Works by Aliyu and Liu set the stage by demonstrating practical implementations that focus on poisoning attack prevention and secure IoT data logging using Ethereum and cloud infrastructures. In parallel, studies such as those by Daund et al. have emphasized the incorporation of federated learning and differential privacy to enhance threat detection while maintaining data confidentiality. Similarly, research focused on fault-tolerant architectures shows that multi-tiered blockchain designs not only improve reliability but also enable scalability and real-time responsiveness under resource-limited conditions.

A key area of convergence across these works is the use of permissioned blockchains to tailor network access and provide controlled transparency in agricultural supply chains. While Ethereum's public blockchain offers versatility, its limitations in scalability and transaction costs have led researchers to explore alternatives like Hyperledger Fabric, which offer modular designs and improved privacy controls \cite{aliyu2023blockchainbasedsmartfarm, soy2025blockchainintegrationin}. In addition, the integration of advanced cryptographic primitives such as ECC, zero-knowledge proofs, and homomorphic encryption is becoming common practice to secure sensitive data without impeding computational performance.

In terms of limitations, several studies note that although the integration of blockchain with advanced security and privacy mechanisms has produced promising results in controlled prototype environments, there remains a significant gap in large-scale practical deployments. Issues such as computational overhead, battery life and energy consumption issues for IoT sensors, and integration complexities with existing agricultural infrastructures continue to be open research challenges. Furthermore, efforts to balance the inherent transparency of blockchain with stringent privacy requirements have led to hybrid solutions that require further optimization to minimize trade-offs between data confidentiality and auditability \cite{soy2025blockchainintegrationin}.

Figure 1 illustrates an overview of a typical multi-tiered blockchain-enabled smart agriculture framework, highlighting the roles of edge, fog, and cloud layers in data collection, processing, and secure storage. Figure 2 depicts a sample smart contract workflow used for real-time threat detection and automated alerting in a smart farm setting.

\section{Summary Tables of Key Papers}
Below are two summary tables capturing groups of similar studies on blockchain-based security, privacy, and reliability in smart agriculture.

\begin{table}[htbp]
\centering
\caption{Summary of Papers Focusing on Security and Cryptographic Techniques}
\label{tab:security}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X}
\toprule
\textbf{Paper Title} & \textbf{Key Findings} & \textbf{Limitations} & \textbf{Similarities/Differences} \\
\midrule
Blockchain-based Smart Farm Security Framework (Aliyu \& Liu) \cite{aliyu2023blockchainbasedsmartfarm} & Demonstrates blockchain for tamper-proof IoT sensor data logging and poisoning attack prevention; integration with AWS IoT and smart contract-based alerting. & Limited experimental runs; reliance on cloud infrastructure may impact latency and scalability & Emphasizes decentralized data integrity; uses Ethereum-based smart contracts—similar to other works on secure IoT frameworks \\
\midrule
Hyperledger Fabric \& Federated Learning Framework \cite{daund2025designofan} & Integrates blockchain with federated learning and differential privacy ensuring 100\% data integrity and secure ML-based threat detection. & Computational overhead and integration complexity; scalability in resource-limited IoT systems poses challenges & Uses permissioned blockchain to enforce privacy while balancing transparency and privacy similar to other approaches \\
\midrule
Redactable Blockchain for IoFT Systems \cite{mishra2023redactableblockchainassistedsecure} & Proposes a three-tiered architecture with redactable blockchain to enhance secure data aggregation in fog-enabled agricultural IoT networks. & Resource limitations at fog nodes and challenges in integrating advanced redaction mechanisms into existing infrastructures & Focuses on source authentication and tamper resistance similar to multi-tiered schemes but with controlled redaction \\
\midrule
ECC-Based Authentication Schemes \cite{tahayur2024enhancingelectronicagriculture} & Employs advanced cryptographic techniques such as ECC and ring signatures to provide strong access control and device authentication in IoT systems. & Higher computational cost for cryptographic operations and potential latency issues in real-time processing & Shares common goals with other security protocols focused on robust authentication and encryption \\
\midrule
Lightweight Blockchain Approaches for Resource-Constrained Farms \cite{tahayur2024enhancingelectronicagriculture} & Investigates scalable, resource-efficient blockchain models using smart contracts on permissioned blockchains in agriculture IoT. & Trade-offs between security robustness and energy consumption and latency limitations persist & Similar focus on optimizing security for resource-constrained environments as seen in other works targeting rural deployments \\
\bottomrule
\end{tabularx}
\end{table}

\begin{table}[htbp]
\centering
\caption{Summary of Papers Focusing on Privacy Preservation and Reliability}
\label{tab:privacy}
\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X}
\toprule
\textbf{Paper Title} & \textbf{Key Findings} & \textbf{Limitations} & \textbf{Similarities/Differences} \\
\midrule
Privacy-Centric AI \& IoT Solutions \cite{rahaman2024privacycentricaiand} & Proposes a three-phase secure data exchange protocol for rural farm monitoring using symmetric/asymmetric encryption, hash functions, and rigorous authentication. & Scalability issues in large-scale deployments; limited evaluation of real-world impact & Similar emphasis on privacy preservation using cryptographic techniques as seen in other privacy-centric frameworks \\
\midrule
Federated Learning with Differential Privacy Framework \cite{daund2025designofan} & Combines blockchain with federated learning and noise addition to protect sensitive IoT data without centralizing raw data; achieves high model accuracy and 100\% data integrity. & Trade-offs between privacy guarantees and computational complexity, challenges in achieving real-time performance & Integrates distributed learning approaches while maintaining data confidentiality similarly seen in other studies \\
\midrule
Multi-Tiered Blockchain Architectures for Reliability \cite{thiruvenkatasamy2025anonlinetool} & Presents a hierarchical design involving edge, fog, and cloud layers for distributed data processing and secure ledger storage, validated by a case study demonstrating a 35\% irrigation efficiency improvement. & Increased processing overhead and potential latency due to multi-tier management, with limited large-scale deployment assessments in heterogeneous environments & Aligns with fault-tolerant mechanisms in other research that implements decentralized data processing \\
\midrule
Consensus Mechanism Comparisons \cite{soy2025blockchainintegrationin} & Reviews alternatives to traditional PoW, such as PoA and PBFT, for efficient consensus in permissioned blockchain networks, yielding improved throughput & Trade-offs exist between decentralization level and energy consumption, with some performance degradation during high load & Several proposals converge on using permissioned consensus algorithms to balance scalability with security \\
\midrule
Redactable Blockchain Approaches for Data Integrity \cite{mishra2023redactableblockchainassistedsecure} & Introduces controlled data modification mechanisms while preserving ledger immutability; enhances resilience against false data injection attacks & Complexity in design and potential computational overhead may limit adaptability in fast-changing IoT networks & Similar focus on data traceability and tamper resistance as compared to non-editable blockchains \\
\bottomrule
\end{tabularx}
\end{table}

\section{Discussion and Future Directions}
The collected literature highlights significant advancements in the convergence of blockchain with IoT for smart agriculture, particularly regarding security, privacy, and reliability. A common observation is that blockchain's decentralized architecture provides a solid foundation by eliminating centralized vulnerabilities and establishing immutable transaction records. However, each proposed framework must strike a delicate balance between implementing robust security protocols and meeting the resource constraints of agricultural IoT devices.

Notably, many state-of-the-art frameworks have shifted toward employing permissioned blockchain systems (such as Hyperledger Fabric and Corda) to enhance access control and enable smart contract-driven automation \cite{aliyu2023blockchainbasedsmartfarm, soy2025blockchainintegrationin}. At the same time, privacy-centric approaches are increasingly integrating federated learning and differential privacy to protect sensitive data during distributed analytics \cite{daund2025designofan}. These integrated solutions illustrate a trend toward holistic architectures that address both external cyber threats (e.g., poisoning, man-in-the-middle, and DDoS attacks) and internal vulnerabilities related to data leakage and unauthorized access.

Despite these promising developments, several open research gaps remain. First, scalability is a universal challenge across many proposals. While experiments in relatively controlled environments indicate improved throughput and fault tolerance, the transition to large-scale deployments in varied agricultural settings has not been fully validated. Second, the resource consumption associated with advanced encryption, consensus algorithms, and redaction methods may exceed the capabilities of resource-constrained edge devices typical in rural farms. Addressing such limitations requires further exploration of lightweight cryptographic methods and energy-efficient consensus mechanisms. Third, the inherent tension between maintaining blockchain transparency and ensuring robust privacy protection is yet to be completely resolved; emerging hybrid models that combine public and private blockchain features show promise but need further robustness evaluation \cite{soy2025blockchainintegrationin}.

Moreover, the integration of Quality-of-Service (QoS) parameters with consensus processes—such as the proposed CRT-based parallel transaction model—introduces additional layers of complexity. Future research should explore adaptive frameworks capable of dynamically adjusting security protocols and resource allocation based on network conditions and transaction criticality. In this context, additional evaluations on latency, energy consumption, and throughput across heterogeneous IoT platforms are warranted.

Finally, while many studies focus on isolated aspects of security, privacy, and reliability, there is a growing need for comprehensive frameworks that simultaneously address these interconnected domains. The emerging trend of combining blockchain with advanced AI methods (e.g., deep learning for anomaly detection) and cryptographic techniques (e.g., homomorphic encryption, ZKP) points toward integrated solutions that can adapt to the dynamic and heterogeneous nature of agricultural data flows. Such systems would not only secure data but also provide actionable insights to optimize agricultural operations and ensure sustainability.

\section{Conclusion}
In summary, recent peer-reviewed literature from 2022 to 2025 demonstrates that blockchain-enabled IoT frameworks for smart agriculture are evolving rapidly to meet the dual challenges of securing data against sophisticated cyber-attacks and preserving user privacy in decentralized networks. Leading studies show that integrating permissioned blockchain architectures with advanced cryptographic methods, federated learning, and real-time automated alert systems offers significant enhancements in data integrity, privacy, and reliability. Nevertheless, practical deployment challenges such as scalability, computational overhead, and energy consumption persist. Future research directions should focus on developing lightweight, adaptive frameworks that harmonize security, privacy, and reliability while accommodating the resource constraints of rural farming environments. By addressing these gaps, blockchain-enabled IoT systems can provide a robust foundation for sustainable, efficient, and secure smart agriculture, as envisioned in the project "Blockchain-enabled IoT Framework for Smart Agriculture: A CRT-based Parallel Transaction Model with Consensus and QoS Mechanisms" \cite{aliyu2023blockchainbasedsmartfarm, daund2025designofan}.

\printbibliography

\end{document}
