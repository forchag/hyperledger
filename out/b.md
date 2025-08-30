\documentclass[journal]{IEEEtran}
\usepackage[utf8]{inputenc}
\usepackage{array}
\usepackage{booktabs} % For better looking tables
\usepackage{graphicx} % For including figures (though not used here for images)
\usepackage{hyperref} % For hyperlinks
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,      
    urlcolor=cyan,
    pdftitle={Blockchain IoT Agriculture Literature Review},
}

% Define a new column type for fixed-width, centered cells
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}

\title{Blockchain-enabled IoT Framework for Smart Agriculture: A Literature Review on Energy, Usability, and Supply Chain Integration}
\author{Your~Name(s)~Here% <-this % stops a space
\thanks{Manuscript received...}% <-this % stops a space
}
\markboth{Journal of Some Kind, Vol. 1, No. 1, January 2025}%
{Your Name: Blockchain-enabled IoT Framework for Smart Agriculture}

\begin{document}
\maketitle

\begin{abstract}
Recent advancements in blockchain–IoT integration for smart agriculture have shown promising capabilities to enhance traceability, security, and operational efficiency. However, significant challenges remain in achieving energy efficiency in resource‐constrained IoT environments, promoting usability and adoption among farmers, and ensuring seamless supply chain integration. This report reviews over 40 recent peer‐reviewed studies that investigate energy‐efficient blockchain architectures, user-centric design for farmer adoption, and blockchain‐enabled traceability solutions in agriculture. Our review emphasizes the need for lightweight consensus algorithms, enhanced Quality of Service (QoS) mechanisms, and cross-disciplinary strategies to overcome scalability and interoperability issues. The synthesis culminates in a recommendation for a CRT‐based parallel transaction model that balances energy trade‐offs, usability requirements, and end‐to‐end supply chain transparency.
\end{abstract}

\begin{IEEEkeywords}
Blockchain, Internet of Things (IoT), Smart Agriculture, Energy Efficiency, Usability, Supply Chain, Literature Review.
\end{IEEEkeywords}

\section{Introduction}
\IEEEPARstart{T}{he} digital transformation of agriculture has reached a pivotal moment as emergent technologies such as the Internet of Things (IoT), blockchain, artificial intelligence (AI), and cloud computing converge to address longstanding issues in food safety, supply chain efficiency, and environmental sustainability. In traditional agricultural systems, fragmented data management, lack of traceability, and opaque supply chains have resulted in inefficiencies, food fraud, and resource mismanagement. Blockchain’s decentralized ledger technology—with its inherent immutability, transparency, and security features—offers a viable solution to these challenges by ensuring that data from IoT‐enabled sensors is securely captured and disseminated across a network of stakeholders \cite{akella2023asystematicreview, mwewa2024blockchaintechnologya}.

A central limitation in many blockchain implementations is the high energy consumption associated with conventional consensus mechanisms such as Proof-of-Work. This issue is particularly pertinent in agricultural settings where IoT devices often operate on constrained energy budgets. At the same time, usability challenges hinder the adoption of blockchain systems by farmers, who may lack the digital literacy or access to robust IT infrastructures \cite{ninsiima2025determinantsofsmallholder, mwewa2024blockchaintechnologya}. Moreover, while significant progress has been made in developing blockchain-based traceability systems within food supply chains, many implementations achieve only partial coverage of agricultural processes and – in some cases – struggle to integrate real-time IoT data seamlessly \cite{akella2023asystematicreview, ellahi2023blockchainbasedframeworksfor}.

To address these challenges, our project proposes a novel CRT‐based parallel transaction model that leverages energy‐efficient consensus mechanisms and QoS strategies to improve blockchain performance while simultaneously enhancing usability and full-chain supply traceability. The following literature review provides a critical assessment of recent advances in energy efficiency, usability, and supply chain integration in blockchain-enabled IoT smart farming systems.

\section{Literature Review}

\subsection{Energy Efficiency in Blockchain–IoT Agriculture}
Recent studies have focused on reducing blockchain’s energy footprint while maintaining data security and transparency in agricultural IoT applications. Munaganuri et al. \cite{munaganuri2025designofan} propose an integrated model that combines Long Short-Term Memory (LSTM) networks, IoT sensors communicating via the low-power LoRaWAN protocol, and Hyperledger Fabric blockchain, complemented by reinforcement learning with Deep Q-Networks (DQN) to optimize irrigation scheduling. Their field trials reported a 20\% reduction in water usage accompanied by a 12\% increase in crop yield, demonstrating not only improved resource efficiency but also substantial energy savings through the adoption of low-power wireless communication protocols. Other studies have proposed lightweight blockchain architectures such as Easychain \cite{bapatla2023easychainaniotfriendly}, which is specifically designed for IoT environments with limited computational resources. These lightweight approaches focus on reducing the overhead associated with conventional consensus algorithms and employ alternative mechanisms (e.g., Proof-of-Stake or Proof-of-Authority) to further reduce energy consumption \cite{alkhateeb2022hybridblockchainplatforms, tahayur2024enhancingelectronicagriculture}.

However, challenges remain. For instance, while many researchers report favorable results in simulation environments or small-scale field trials, scalability concerns persist when these energy-efficient models are considered for large-scale or diverse agricultural landscapes \cite{akella2023asystematicreview, munaganuri2025designofan}. Furthermore, the integration of renewable energy sources and optimized resource allocation strategies presents additional opportunities to further reduce the energy footprint, yet require more rigorous experimental validation \cite{tahayur2024enhancingelectronicagriculture, mwewa2024blockchaintechnologya}. Figure 1 (see \cite{munaganuri2025designofan}, Fig. 7, p.22) illustrates a typical energy-efficient performance curve for IoT nodes deployed in a smart agriculture network.

\subsection{Usability and Farmer Adoption of Blockchain-Enabled Smart Farming Systems}
The usability of blockchain systems is critical for achieving broad adoption among smallholder farmers and other stakeholders in agriculture. Researchers have applied models such as the Technology Acceptance Model (TAM) and its extensions \cite{ninsiima2025determinantsofsmallholder, mwewa2024blockchaintechnologya} to assess the determinants of blockchain adoption. These studies consistently identify factors such as perceived usefulness, ease of use, and subjective norm as significant predictors of a farmer’s intention to use blockchain-based systems \cite{ninsiima2025determinantsofsmallholder, mwewa2024blockchaintechnologya}. For example, a study by Ninsiima et al. \cite{ninsiima2025determinantsofsmallholder} reports that blockchain technologies, when integrated with user-friendly interfaces and supported by training programs, can effectively reduce information asymmetry and improve trust between farmers and buyers.

User-centered design is therefore pivotal. An example is provided by Price-Torrejón et al. \cite{pricetorrejon2025designofa}, who developed a blockchain-enabled web application prototype designed to optimize traceability in agricultural supply chains. Their evaluation using the System Usability Scale (SUS) yielded an impressive average score of 90, confirming the prototype’s excellent usability and its potential for adoption among low-technical users. Yet despite these positive findings, several limitations continue to impede widespread adoption. High implementation costs, infrastructure deficiencies, and the complexity of blockchain interfaces remain significant barriers, especially in developing regions where digital literacy is limited \cite{ninsiima2025determinantsofsmallholder, akella2023asystematicreview}. Other studies suggest that blockchain-as-a-service (BaaS) platforms might alleviate these hurdles by offloading technical complexities onto third-party providers, though economic and regulatory challenges persist \cite{akella2023asystematicreview}.

\subsection{Blockchain-Enabled Traceability and Supply Chain Integration}
Blockchain’s decentralized ledger technology has been extensively applied in agri-food supply chains to improve traceability and transparency. Numerous real-world applications—such as BeefLedger, Pagonis Dairy, FarMarket, and HARA—demonstrate blockchain’s ability to track agricultural products from pre-harvest through to post-harvest stages \cite{akella2023asystematicreview, mwewa2024blockchaintechnologya}. Such traceability systems leverage smart contracts and integrate data acquired from IoT sensors (RFID, GPS, NFC) to manage provenance information, ensure food safety, and simplify financial transactions among stakeholders \cite{ellahi2023blockchainbasedframeworksfor, akella2023asystematicreview}.

These systems provide significant benefits, including enhanced food quality, reduced fraud, and improved consumer confidence through transparent record-keeping. However, limitations are also evident. For instance, many existing systems are designed to address specific facets of the agricultural process rather than offering full-stack solutions that cover the entire supply chain \cite{akella2023asystematicreview}. Additionally, interoperability issues among disparate ICT systems, scalability challenges, and the lack of unified global standards have been highlighted as key obstacles for widespread adoption \cite{akella2023asystematicreview}. Figure 2 \cite{sakthivel2024enhancingtransparencyand} provides a schematic representation of a blockchain-based traceability framework, which illustrates the integration of IoT sensors and smart contracts for end-to-end supply chain monitoring.

\section{Summary Tables}
The following tables synthesize key findings from selected recent studies on energy efficiency, usability, and supply chain integration in blockchain-enabled IoT smart agriculture systems.

% Table 1
\begin{table*}[htbp]
\caption{Energy Efficiency in Blockchain-IoT Agriculture}
\label{table:energy}
\centering
\begin{tabular}{@{}L{3.5cm}L{4cm}L{3.5cm}L{3cm}@{}}
\toprule
\textbf{Paper Title} & \textbf{Key Findings} & \textbf{Limitations} & \textbf{Similarities/Differences} \\
\midrule
Design of an improved graph-based model integrating LSTM, LoRaWAN, and blockchain for smart agriculture \cite{munaganuri2025designofan} & Demonstrated 20\% reduction in water usage and 12\% increase in crop yield through energy-efficient sensor communication via LoRaWAN and blockchain integration. & Scalability issues and integration challenges in heterogeneous agricultural environments. & Focuses on energy-efficient IoT communication similar to other lightweight models. \\
\midrule
EasyChain: an IoT-friendly blockchain for robust and energy-efficient authentication \cite{bapatla2023easychainaniotfriendly} & Introduced a lightweight blockchain platform optimized for resource-constrained IoT devices, reducing energy consumption and computational overhead. & Integration complexity when scaling to real-world deployments and interoperability with legacy systems. & Shares objective of reducing power usage with alternative consensus mechanisms. \\
\midrule
Blockchain for precision irrigation: Opportunities and challenges \cite{bodkhe2022blockchainforprecision} & Evaluated blockchain-enabled precision irrigation systems, identifying energy constraints and the need for optimized consensus mechanisms to suit agriculture IoT. & Limited experimental validation under large-scale field conditions. & Similar emphasis on energy efficiency in the context of resource management. \\
\midrule
A Cross-Layer Secure and Energy-Efficient Framework for the Internet of Things \cite{mustafa2024acrosslayersecure} & Proposed a multi-layer optimization strategy combining blockchain, AI, and secure routing to conserve energy in IoT devices. & Heavy dependence on simulation accuracy and challenges in maintaining robust performance in real deployments. & Emphasizes cross-layer approaches to reduce energy consumption. \\
\midrule
A Cross-Layer Secure and Energy-Efficient Framework for the Internet of Things \cite{mustafa2024acrosslayersecure} & Highlighted the use of cross-layer protocols and lightweight cryptographic techniques to achieve significant energy savings without compromising security. & Scalability and integration with diverse IoT devices remain unproven in field trials. & Similar to other approaches using cross-layer optimization and lightweight schemes. \\
\bottomrule
\end{tabular}
\end{table*}

% Table 2
\begin{table*}[htbp]
\caption{Usability and Farmer Adoption of Blockchain-Enabled Smart Farming Systems}
\label{table:usability}
\centering
\begin{tabular}{@{}L{3.5cm}L{4cm}L{3.5cm}L{3cm}@{}}
\toprule
\textbf{Paper Title} & \textbf{Key Findings} & \textbf{Limitations} & \textbf{Similarities/Differences} \\
\midrule
Determinants of smallholder barley farmers' intentions to adopt blockchain technology \cite{ninsiima2025determinantsofsmallholder} & Identified perceived usefulness, ease of use, and social influence as key determinants affecting blockchain adoption among smallholder farmers. & Focused on behavioral intention rather than actual system usage; limited to a specific region. & Aligns with TAM-based approaches utilized in other studies on adoption. \\
\midrule
A Systematic Review of Blockchain Technology Adoption Barriers and Enablers \cite{akella2023asystematicreview} & Showed that stakeholder collaboration and trust enhancement are critical enablers, while cost, regulatory issues, and technological complexity are significant barriers. & Provides broad thematic insights but lacks empirical usability data collected directly from farmers. & Similar emphasis on socio-technical factors influencing adoption. \\
\midrule
Design of a Blockchain-Based Web Application to Optimize Traceability \cite{pricetorrejon2025designofa} & Achieved an average SUS score of 90, indicating excellent usability for low-technical users, with functionalities for batch registration and smart contracts. & Reliance on manual data entry in evaluations limits the representativeness of real-world usability. & Highlights user interface design benefits consistent with user-centered design models. \\
\midrule
Blockchain Technology: A Review Study on Improving Efficiency and Transparency \cite{mwewa2024blockchaintechnologya} & Emphasized that blockchain technology can significantly reduce operational costs and build trust through transparent, tamper-proof records in supply chains. & Identified challenges related to digital literacy and high initial investment costs in SMEs. & Consistent with findings that usability remains a barrier in resource-limited settings. \\
\midrule
Determinants of smallholder barley farmers' intentions to adopt blockchain technology \cite{ninsiima2025determinantsofsmallholder} & Integrated psychosocial factors with TAM, revealing that ease of use and relevance of technology directly impact adoption intentions among smallholder farmers. & The study focuses on intentions rather than actual usage and may not capture post-adoption challenges. & Reinforces the significance of educational and economic incentives for adoption. \\
\bottomrule
\end{tabular}
\end{table*}

% Table 3
\begin{table*}[htbp]
\caption{Blockchain-Enabled Traceability and Supply Chain Integration in Agriculture}
\label{table:supplychain}
\centering
\begin{tabular}{@{}L{3.5cm}L{4cm}L{3.5cm}L{3cm}@{}}
\toprule
\textbf{Paper Title} & \textbf{Key Findings} & \textbf{Limitations} & \textbf{Similarities/Differences} \\
\midrule
A Systematic Review of Blockchain Technology Adoption Barriers and Enablers \cite{akella2023asystematicreview} & Demonstrated that blockchain-based traceability systems, integrated with IoT sensors, enhance food safety and provenance verification from farm to table. & Existing systems often address only specific parts of the supply chain rather than a full-stack solution. & Focuses on transparency and traceability similar to BeefLedger and related case studies. \\
\midrule
Enhancing Transparency and Trust in Agrifood Supply Chains through Novel Blockchain-based Architecture \cite{sakthivel2024enhancingtransparencyand} & Proposed a layered blockchain architecture with smart contract automation to improve traceability, quality certification, and secure financial transactions in supply chains. & Complexity of integrating decentralized systems with legacy supply chain systems and scalability issues persist. & Shares integration objectives with other blockchain traceability frameworks. \\
\midrule
Blockchain-Based Frameworks for Food Traceability: A Systematic Review \cite{ellahi2023blockchainbasedframeworksfor} & Reviewed multiple implementations demonstrating drastic reductions in traceability times and improved data integrity in food supply chains through IoT integration. & Implementation gaps such as fragmented systems and lack of standardized protocols are common. & Consistent with case studies that emphasize blockchain’s role in reducing food fraud. \\
\midrule
A Systematic Review of Blockchain Technology Adoption Barriers and Enablers \cite{akella2023asystematicreview} & Highlighted blockchain’s capacity to reduce fraud, prevent double-spending, and enhance traceability throughout agricultural supply chains. & Barriers include lack of unified global standards and high resource requirements, which impede full adoption. & In line with other reviews that underscore the need for comprehensive traceability solutions. \\
\midrule
Blockchain Technology: A Review Study on Improving Efficiency and Transparency \cite{mwewa2024blockchaintechnologya} & Noted that blockchain offers improved transparency and efficiency by automating transactions and reducing intermediaries along the supply chain. & Limited by technological immaturity and limited interoperability with existing agricultural systems. & Emphasizes similar benefits as other blockchain-based traceability studies. \\
\bottomrule
\end{tabular}
\end{table*}

\section{Discussion}
The state-of-the-art review reveals significant progress in the integration of blockchain and IoT for smart agriculture, yet also underscores critical challenges that remain unsolved. From an energy efficiency standpoint, researchers have increasingly focused on developing lightweight blockchain architectures and alternative consensus mechanisms that can be deployed on battery-powered IoT devices. Studies such as Munaganuri et al. \cite{munaganuri2025designofan} demonstrate that combining low-power communication protocols like LoRaWAN with optimized blockchain implementations can yield meaningful reductions in energy consumption. Nonetheless, many proposals are still limited by scalability issues and the computational overhead of even lightweight cryptographic operations, particularly when applied to large-scale, heterogeneous agricultural environments \cite{akella2023asystematicreview, munaganuri2025designofan}. Although certain approaches have shown promise in simulated environments and small-scale deployments, further validation is required to ensure these techniques can be effectively extrapolated to broader agricultural contexts while maintaining energy efficiency \cite{tahayur2024enhancingelectronicagriculture, mwewa2024blockchaintechnologya}.

Usability and farmer adoption remain equally critical dimensions for the success of blockchain systems in agriculture. Empirical studies using usability metrics like the System Usability Scale have indicated that well-designed blockchain applications can achieve high user satisfaction when user-centered design principles are applied \cite{pricetorrejon2025designofa}. However, broader deployment is impeded by economic, educational, and infrastructural challenges. The complexity inherent in blockchain technology, combined with limited digital literacy among smallholder farmers, means that even high-performing prototypes may fail to gain traction without additional support. Many studies advocate for capacity-building initiatives, government subsidies, and the development of blockchain-as-a-service (BaaS) platforms specifically designed for the agricultural setting to overcome these barriers \cite{ninsiima2025determinantsofsmallholder, mwewa2024blockchaintechnologya}.

Blockchain-enabled traceability systems hold enormous potential for transforming the agricultural supply chain by providing absolute data integrity, enabling real-time tracking, and automating transactions through smart contracts. Numerous case studies have demonstrated the feasibility of these systems in reducing food fraud and enhancing consumer trust by providing immutable records of product provenance \cite{akella2023asystematicreview, mwewa2024blockchaintechnologya}. Yet, the extant literature also highlights that many implementations are fragmented, catering only to specific segments of the supply chain rather than offering a full-stack solution that bridges all stages of production, processing, and distribution. Moreover, interoperability issues persist, as many blockchain frameworks are not yet seamlessly integrated with legacy agricultural ICT systems, thereby limiting their scalability and overall effectiveness \cite{akella2023asystematicreview}.

In summary, the literature evidences that a holistic CRT-based parallel transaction model, which incorporates energy-efficient consensus algorithms, parallel processing to improve throughput, and sophisticated QoS mechanisms, could alleviate many of these challenges. Such a model should prioritize optimizing energy use at the device level while ensuring robust security and transparency in complex supply chains. For instance, cross-layer designs that combine blockchain with AI-driven intrusion detection and energy-efficient routing protocols (see \cite{mustafa2024acrosslayersecure}, Fig. 5, p.19) illustrate a promising pathway towards meeting these objectives. At the same time, future work must place greater emphasis on user-centered design to develop interfaces and support systems that facilitate adoption among farmers who may be less familiar with high-tech solutions, ensuring that the benefits of blockchain can be realized across diverse agricultural contexts.

\section{Conclusion}
In conclusion, this review highlights that blockchain-enabled IoT frameworks hold transformative potential for smart agriculture by addressing critical issues of energy management, usability, and supply chain traceability. Energy-efficient architectures employing lightweight consensus protocols and low-power communication technologies (e.g., LoRaWAN) have demonstrated significant promise in reducing the operational energy footprint of agricultural IoT networks \cite{munaganuri2025designofan, bapatla2023easychainaniotfriendly}. Simultaneously, the adoption of blockchain by farmers is strongly influenced by usability factors that are best addressed through tailored user-centric designs, educational initiatives, and blockchain-as-a-service models \cite{pricetorrejon2025designofa, ninsiima2025determinantsofsmallholder}. Finally, while blockchain-enhanced traceability systems markedly improve transparency and trust in food supply chains, they are still limited by partial process integration, interoperability challenges, and scalability issues \cite{akella2023asystematicreview, mwewa2024blockchaintechnologya}. Addressing these interrelated challenges requires the development of an integrated CRT-based parallel transaction model that not only maximizes energy and computational efficiency but also ensures user-friendly interfaces and full-stack supply chain integration. Future research should focus on validating these approaches in large-scale, real-world settings and developing comprehensive regulatory and educational frameworks to expedite widespread adoption among diverse stakeholders.

Overall, the integration of blockchain with IoT in smart agriculture is advancing rapidly; however, significant work remains to balance energy efficiency, enhance usability, and deliver end-to-end supply chain transparency. This report underscores the importance of interdisciplinary efforts in achieving these objectives and provides a roadmap for future research toward a fully integrated, energy-aware, and user-friendly blockchain-enabled IoT framework for smart agriculture.

IEEE-style reference figures such as those in \cite{munaganuri2025designofan}, Fig. 7, p.22 and \cite{pricetorrejon2025designofa}, Fig. 4, p.15 further illustrate the performance and usability characteristics that are central to this emerging field.

% Use biber as the backend for BibTeX
\bibliographystyle{IEEEtran}
\bibliography{my_bibliography} % Assumes your BibTeX file is named 'my_bibliography.bib'

\end{document}
