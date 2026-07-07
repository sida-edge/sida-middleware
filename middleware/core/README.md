# ⚙️ Core: O Motor de Processamento Edge

Este diretório contém os microsserviços que formam o "coração" do SIDA. Eles rodam na Borda (Edge) e são responsáveis por extrair o dado bruto da máquina e transformá-lo em dados ricos.
<!-- A arquitetura do Core é **poliglota e brokerless** na comunicação interna (Leste-Oeste). Os microsserviços conversam entre si com latência de microssegundos utilizando o barramento **ZeroMQ**, garantindo que nenhum gargalo de rede local paralise a linha de produção. -->

## 🧩 O Pipeline de 3 Camadas

O processamento ocorre em uma cascata estrita:

### 1. Ingestão (`/sida-ingestion`)
*   **Papel:** A força bruta. Conecta-se aos hardwares (CLPs, Sensores) através de protocolos industriais (Modbus, OPC UA).
*   **Comportamento:** Lê o dado bruto e publica imediatamente no barramento interno.
<!-- *   **Linguagem sugerida:** C++ / Rust (Foco em performance Bare-Metal). -->

### 2. Contextualização (`/sida-engine`)
*   **Papel:** O cérebro semântico. Consome o dado bruto da Camada 1, aplica regras de negócio e estrutura o pacote segundo normas industriais.
*   **Comportamento:** Enriquece o dado e o empurra via barramento interno para a próxima etapa.
<!-- *   **Linguagem sugerida:** Python (Foco em manipulação de dicionários e preparo para IA). -->

### 3. UNS Delivery (`/sida-delivery`)
*   **Papel:** O carteiro. É a única camada que se comunica com o mundo exterior (Tráfego Norte-Sul).
*   **Comportamento:** Consome o dado rico da Camada 2, aplica os certificados de estado rigorosos (`NBIRTH`, `NDEATH`), serializa o payload em **Protobuf (Sparkplug B)** e publica no broker MQTT central na nuvem.
<!-- *   **Linguagem sugerida:** Go / Python / Node.js (Foco em alta concorrência de rede). -->