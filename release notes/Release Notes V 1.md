_Data: 17_ _de abril de 2026_

## Visão Estratégica e Arquitetural

#### SIDA - Smart Industrial DataOps Agent

_A Unified Namespace-Based Approach to Enabling Semantic Interoperability_

O SIDA é um _middleware_ de borda projetado especificamente para atuar como o "porteiro" do chão de fábrica. Diferente de soluções legadas de extração ou plataformas monolíticas pesadas, o SIDA oferece uma arquitetura leve, baseada em agentes, para ingerir dados brutos de máquinas heterogêneas, aplicar contextualização semântica (baseada na norma ISA-95) e publicar informações estruturadas em tempo real em uma abordagem de _Unified Namespace_ (UNS).

Este documento detalha a visão, a arquitetura e os objetivos práticos do SIDA, estabelecendo-o como a infraestrutura fundacional para a Indústria 4.0.

#### **O Desafio da "caixa-preta" industrial (OT)**

Apesar dos avanços em sistemas de TI (ERPs, IA, Nuvem), a camada Operacional (OT) das fábricas permanece um ambiente fragmentado. Os principais obstáculos para a integração de dados incluem:

- **A _"Babel"_** **de Protocolos:** O chão de fábrica é composto por máquinas de diferentes eras e fabricantes (Siemens, Rockwell, equipamentos legados, equipamentos proprietários). Cada ativo fala um protocolo proprietário distinto (Modbus, OPC DA/UA, S7, Ethernet/IP).
- **Miopia Semântica (Falta de Contexto):** Ferramentas tradicionais de conectividade extraem dados em sua forma bruta. Um valor como 60.5 vindo de um endereço de memória (ex: DB1.DBX0.0) não possui significado para sistemas corporativos sem o devido contexto (O que é? De qual linha de produção vem? Qual a unidade de medida?).
- **Arquiteturas _"Teia de Aranha"_:** Parte da integração convencional foca na conexão ponto a ponto (ex: conectar a Máquina A diretamente ao Dashboard B). Isso gera um emaranhado técnico insustentável, rígido e caro de manter.

A solução moderna para essa fragmentação é o **Unified Namespace (UNS)** - um hub central de dados em tempo real, organizado hierarquicamente. Contudo, o UNS requer que os dados cheguem até ele limpos e contextualizados. É exatamente nesta lacuna crítica que o SIDA atua.

#### **A Solução: Arquitetura em 3 Camadas do SIDA**

O SIDA resolve a quebra de comunicação entre OT e TI através de uma arquitetura modular, executada na borda da rede (Edge), dividida em três camadas distintas de processamento:

| Camada                 | Descrição                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| _Ingestão e Tradução:_ | **Função:** Estabelecer comunicação física e lógica com ativos legados e modernos de forma não intrusiva (via Polling ou Subscrição).<br><br>**Operação:** Um agente (ex: Agente Modbus) lê o dado bruto do CLP, converte-o para uma estrutura genérica interna e o isola das flutuações de rede da planta.<br><br>**Diferencial:** Arquitetura _plug-and-play_. Se um protocolo falhar ou um cabo romper, apenas aquele agente específico é afetado, garantindo alta disponibilidade do núcleo do sistema.               |
| _Context Engine_       | **Função:** Enriquecer e padronizar os dados utilizando os conceitos de modelagem hierárquica da norma ISA-95.<br><br>**Operação:** O SIDA cruza a telemetria pontual recebida da Camada 1 com a estrutura lógica da fábrica. O dado "bruto" é envelopado e ganha identidade, sendo mapeado como: \[Empresa\] / \[Planta\] / \[Área\] / \[Linha\] / \[Ativo\] / \[Telemetria\].<br><br>**Diferencial:** Previne que a complexidade e a desorganização do hardware subam para a camada corporativa.                        |
| _UNS Delivery_         | **Função:** Publicar os dados contextualizados de forma escalável e leve.<br><br>**Operação:** Transforma a informação em payloads Sparkplug B otimizados e os publica via MQTT diretamente na estrutura de tópicos do Unified Namespace corporativo do cliente.<br><br>**Diferencial:** Inclui resiliência através de mecanismos de _Store and Forward_, garantindo que, em caso de queda da rede de TI, os dados da borda sejam armazenados localmente (buffer) e sincronizados posteriormente, sem perda de histórico. |

#### **Posicionamento Competitivo e de Mercado**

O mercado atual oferece soluções polarizadas. De um lado, ferramentas tradicionais focadas apenas em extração; do outro, plataformas monolíticas complexas. O SIDA encontra seu nicho combinando as duas pontas da necessidade industrial:

- **_vs. Extratores Puros (ex: Kepware):_** Enquanto estes apenas movem dados brutos (Camada 1), o SIDA agrega o _Context Engine_ (Camada 2), entregando dados prontos para análise, e não apenas uma lista interminável de _tags_.
- **_vs. Plataformas SCADA (ex: Ignition):_** O SIDA não tenta ser uma ferramenta de visualização (HMI/SCADA). Somos mais leves, mais baratos e exigimos menos processamento de borda, atuando estritamente como um roteador inteligente de dados (_DataOps_).
- **_vs. Hubs de DataOps (ex: HighByte):_** Enquanto plataformas de alto nível frequentemente exigem que o cliente pague por softwares de terceiros para realizar a Ingestão (Camada 1), o SIDA oferece a solução ponta a ponta para a borda: traduzimos o metal e aplicamos a semântica na mesma ferramenta.

#### **Escopo e Metas: Release 1.0**

O Release 1.0 do SIDA visa estabelecer a fundação técnica robusta do produto, validando seu funcionamento em ambientes reais de fábrica. Os objetivos prioritários (Briefing do MVP) são:

| Meta                            | Descrição                                                                                                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fundação Multilinguagem**     | Desenvolvimento e estabilização de Agentes de Ingestão para, no mínimo, dois protocolos industriais cruciais (ex: Modbus TCP/RTU e OPC UA Client) rodando simultaneamente.      |
| **Motor Semântico Operacional** | Implementação do motor de processamento (Camada 2) capaz de ingerir o dado bruto dos agentes e aplicar um template estático de hierarquia ISA-95, formatando a saída para JSON. |
| **Habilitação do UNS**          | Entrega (Camada 3) de dados estáveis a um Broker MQTT central, provando o fluxo fim-a-fim: da máquina à nuvem/UNS, de forma assíncrona.                                         |
