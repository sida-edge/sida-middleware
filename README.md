# 🏭 SIDA - Semantic Industrial DataOps Agent

O **SIDA** é um middleware de Edge Computing e DataOps projetado para a Indústria 4.0. Ele atua como a ponte inteligente entre o chão de fábrica (OT) e os sistemas de análise de dados (IT), implementando o conceitos de Unified Namespace (UNS).

Em vez de atuar como um simples "passador de mensagens", o SIDA extrai, contextualiza semanticamente e entrega dados industriais em tempo real, prontos para consumo por algoritmos de Inteligência Artificial e dashboards analíticos.

## 🏗️ Estrutura

Para garantir escalabilidade e resiliência, o SIDA utiliza uma arquitetura de microsserviços poliglota, dividida nos seguintes domínios:

*   📂 **`/core`**: O motor do SIDA. Contém os microsserviços responsáveis pela ingestão física, tratamento semântico e entrega dos dados.
*   📂 **`/analytics-consumption`**: O destino dos dados. Contém os fluxos do Node-RED e configurações de dashboards para consumo e análise.
*   📂 **`/infra`**: A orquestração. Contém o `docker-compose.yml` para rodar todo o ambiente de forma isolada e local.
*   📂 **`/schemas`**: Os contratos de dados. Contém os arquivos `.proto` (Protobuf) e modelos de dados compartilhados entre todas as camadas.
